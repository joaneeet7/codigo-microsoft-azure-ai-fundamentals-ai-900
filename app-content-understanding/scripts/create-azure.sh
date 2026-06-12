#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="rg-content-understanding"
LOCATION="eastus"
ACCOUNT_NAME=""
STORAGE_ACCOUNT_NAME=""
STORAGE_CONTAINER="content-understanding-inputs"
GPT_DEPLOYMENT_NAME="gpt-4-1"
GPT_MODEL_NAME="gpt-4.1"
GPT_MODEL_VERSION="2025-04-14"
MINI_DEPLOYMENT_NAME="gpt-4-1-mini"
MINI_MODEL_NAME="gpt-4.1-mini"
MINI_MODEL_VERSION="2025-04-14"
EMBEDDING_DEPLOYMENT_NAME="text-embedding-3-large"
EMBEDDING_MODEL_NAME="text-embedding-3-large"
EMBEDDING_MODEL_VERSION="1"
SKU_NAME="GlobalStandard"
MINI_SKU_NAME="Standard"
EMBEDDING_SKU_NAME="Standard"
SKU_CAPACITY="1"
SKIP_MODEL_DEFAULTS="false"
API_VERSION="2025-11-01"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
    --location) LOCATION="$2"; shift 2 ;;
    --account-name) ACCOUNT_NAME="$2"; shift 2 ;;
    --storage-account-name) STORAGE_ACCOUNT_NAME="$2"; shift 2 ;;
    --storage-container) STORAGE_CONTAINER="$2"; shift 2 ;;
    --gpt-deployment-name) GPT_DEPLOYMENT_NAME="$2"; shift 2 ;;
    --gpt-model-name) GPT_MODEL_NAME="$2"; shift 2 ;;
    --gpt-model-version) GPT_MODEL_VERSION="$2"; shift 2 ;;
    --mini-deployment-name) MINI_DEPLOYMENT_NAME="$2"; shift 2 ;;
    --mini-model-name) MINI_MODEL_NAME="$2"; shift 2 ;;
    --mini-model-version) MINI_MODEL_VERSION="$2"; shift 2 ;;
    --embedding-deployment-name) EMBEDDING_DEPLOYMENT_NAME="$2"; shift 2 ;;
    --embedding-model-name) EMBEDDING_MODEL_NAME="$2"; shift 2 ;;
    --embedding-model-version) EMBEDDING_MODEL_VERSION="$2"; shift 2 ;;
    --sku-name) SKU_NAME="$2"; shift 2 ;;
    --mini-sku-name) MINI_SKU_NAME="$2"; shift 2 ;;
    --embedding-sku-name) EMBEDDING_SKU_NAME="$2"; shift 2 ;;
    --sku-capacity) SKU_CAPACITY="$2"; shift 2 ;;
    --skip-model-defaults) SKIP_MODEL_DEFAULTS="true"; shift ;;
    -h|--help)
      cat <<HELP
Uso: ./scripts/create-azure.sh [opciones]

Opciones principales:
  --resource-group NAME       Default: rg-content-understanding
  --location LOCATION         Default: eastus
  --account-name NAME         Si se omite, se genera uno unico
  --storage-account-name NAME Si se omite, se genera uno unico
  --skip-model-defaults       Crea recursos pero no deployments/defaults
HELP
      exit 0 ;;
    *) echo "Opcion desconocida: $1" >&2; exit 1 ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_PATH="$ROOT_DIR/backend/.env"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Falta '$1'. Instala la dependencia y vuelve a ejecutar." >&2
    exit 1
  fi
}

suffix() {
  printf "%06d" "$(( RANDOM % 900000 + 100000 ))"
}

az_cli() {
  local err_file
  err_file="$(mktemp)"
  local output
  if ! output="$(az "$@" 2>"$err_file")"; then
    echo "Azure CLI fallo ejecutando: az $*" >&2
    cat "$err_file" >&2 || true
    rm -f "$err_file"
    exit 1
  fi
  if [[ -s "$err_file" ]] && grep -q '^WARNING:' "$err_file"; then
    cat "$err_file" >&2
  fi
  rm -f "$err_file"
  printf "%s" "$output"
}

cu_endpoint() {
  local endpoint="$1"
  endpoint="${endpoint%/}"
  printf "%s" "${endpoint/.cognitiveservices.azure.com/.services.ai.azure.com}"
}

get_deployment_name_if_exists() {
  local deployment_name="$1"
  az_cli cognitiveservices account deployment list \
    --resource-group "$RESOURCE_GROUP" \
    --name "$ACCOUNT_NAME" \
    --query "[?name=='$deployment_name'].name | [0]" \
    -o tsv
}

ensure_deployment() {
  local deployment_name="$1"
  local model_name="$2"
  local model_version="$3"
  local sku_name="$4"

  if [[ -n "$(get_deployment_name_if_exists "$deployment_name")" ]]; then
    echo "Usando deployment existente: $deployment_name"
    return 0
  fi

  echo "Creando deployment: $deployment_name ($model_name $model_version, SKU $sku_name)"
  local err_file
  err_file="$(mktemp)"
  if az cognitiveservices account deployment create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$ACCOUNT_NAME" \
    --deployment-name "$deployment_name" \
    --model-name "$model_name" \
    --model-version "$model_version" \
    --model-format OpenAI \
    --sku-name "$sku_name" \
    --sku-capacity "$SKU_CAPACITY" > /dev/null 2>"$err_file"; then
    rm -f "$err_file"
    return 0
  fi

  local error_text
  error_text="$(cat "$err_file")"
  rm -f "$err_file"
  if [[ ! "$error_text" =~ Gateway\ Timeout|timeout|temporar|timed\ out ]]; then
    echo "Azure CLI fallo creando deployment $deployment_name" >&2
    echo "$error_text" >&2
    exit 1
  fi

  echo "Azure devolvio timeout creando $deployment_name. Verificando si la operacion continuo en segundo plano..."
  for attempt in {1..18}; do
    sleep 10
    if [[ -n "$(get_deployment_name_if_exists "$deployment_name")" ]]; then
      echo "Deployment detectado despues del timeout: $deployment_name"
      return 0
    fi
    echo "Aun no aparece $deployment_name ($attempt/18)"
  done

  echo "No aparecio $deployment_name despues del timeout. Reintentando una vez..."
  az_cli cognitiveservices account deployment create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$ACCOUNT_NAME" \
    --deployment-name "$deployment_name" \
    --model-name "$model_name" \
    --model-version "$model_version" \
    --model-format OpenAI \
    --sku-name "$sku_name" \
    --sku-capacity "$SKU_CAPACITY" > /dev/null
}

assert_deployment_exists() {
  local deployment_name="$1"
  if [[ -z "$(get_deployment_name_if_exists "$deployment_name")" ]]; then
    echo "Deployments actuales:" >&2
    az_cli cognitiveservices account deployment list \
      --resource-group "$RESOURCE_GROUP" \
      --name "$ACCOUNT_NAME" \
      --query "[].{name:name, model:properties.model.name, version:properties.model.version, state:properties.provisioningState, sku:sku.name}" \
      -o table >&2
    echo "Falta el deployment requerido '$deployment_name'. No se pueden configurar defaults." >&2
    exit 1
  fi
}

wait_deployment_succeeded() {
  local deployment_name="$1"
  local max_attempts="30"
  local delay_seconds="10"
  for ((attempt=1; attempt<=max_attempts; attempt++)); do
    local state
    state="$(az_cli cognitiveservices account deployment show \
      --resource-group "$RESOURCE_GROUP" \
      --name "$ACCOUNT_NAME" \
      --deployment-name "$deployment_name" \
      --query properties.provisioningState \
      -o tsv)"
    if [[ "$state" == "Succeeded" ]]; then
      echo "Deployment listo: $deployment_name"
      return 0
    fi
    if [[ "$state" == "Failed" ]]; then
      echo "El deployment '$deployment_name' fallo al aprovisionarse." >&2
      exit 1
    fi
    echo "Esperando deployment $deployment_name. Estado actual: $state ($attempt/$max_attempts)"
    sleep "$delay_seconds"
  done
  echo "Timeout esperando que el deployment '$deployment_name' llegue a Succeeded." >&2
  exit 1
}

require_cmd az
require_cmd curl

if [[ -z "$ACCOUNT_NAME" ]]; then
  ACCOUNT_NAME="cu-foundry-$(suffix)"
fi
if [[ -z "$STORAGE_ACCOUNT_NAME" ]]; then
  STORAGE_ACCOUNT_NAME="stcu$(suffix)"
fi
ACCOUNT_NAME="$(printf "%s" "$ACCOUNT_NAME" | tr '[:upper:]' '[:lower:]')"
STORAGE_ACCOUNT_NAME="$(printf "%s" "$STORAGE_ACCOUNT_NAME" | tr '[:upper:]' '[:lower:]')"

echo "Validando sesion de Azure CLI..."
az_cli account show > /dev/null

echo "Creando resource group: $RESOURCE_GROUP ($LOCATION)"
az_cli group create --name "$RESOURCE_GROUP" --location "$LOCATION" > /dev/null

existing_account="$(az_cli cognitiveservices account list --resource-group "$RESOURCE_GROUP" --query "[?name=='$ACCOUNT_NAME'].name | [0]" -o tsv)"
if [[ -n "$existing_account" ]]; then
  echo "Usando Microsoft Foundry / Azure AI Services existente: $ACCOUNT_NAME"
else
  echo "Creando Microsoft Foundry / Azure AI Services resource: $ACCOUNT_NAME"
  az_cli cognitiveservices account create \
    --name "$ACCOUNT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --kind AIServices \
    --sku S0 \
    --custom-domain "$ACCOUNT_NAME" \
    --yes > /dev/null
fi

endpoint="$(az_cli cognitiveservices account show --name "$ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP" --query properties.endpoint -o tsv)"
content_understanding_endpoint="$(cu_endpoint "$endpoint")"
key="$(az_cli cognitiveservices account keys list --name "$ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP" --query key1 -o tsv)"

existing_storage="$(az_cli storage account list --resource-group "$RESOURCE_GROUP" --query "[?name=='$STORAGE_ACCOUNT_NAME'].name | [0]" -o tsv)"
if [[ -n "$existing_storage" ]]; then
  echo "Usando Storage Account existente: $STORAGE_ACCOUNT_NAME"
else
  echo "Creando Storage Account para archivos de entrada: $STORAGE_ACCOUNT_NAME"
  az_cli storage account create \
    --name "$STORAGE_ACCOUNT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --sku Standard_LRS \
    --kind StorageV2 \
    --allow-blob-public-access false > /dev/null
fi

storage_connection_string="$(az_cli storage account show-connection-string --name "$STORAGE_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP" --query connectionString -o tsv)"

echo "Creando container privado: $STORAGE_CONTAINER"
az_cli storage container create --name "$STORAGE_CONTAINER" --connection-string "$storage_connection_string" > /dev/null

if [[ "$SKIP_MODEL_DEFAULTS" != "true" ]]; then
  echo "Creando deployments base para Content Understanding..."
  ensure_deployment "$GPT_DEPLOYMENT_NAME" "$GPT_MODEL_NAME" "$GPT_MODEL_VERSION" "$SKU_NAME"
  ensure_deployment "$MINI_DEPLOYMENT_NAME" "$MINI_MODEL_NAME" "$MINI_MODEL_VERSION" "$MINI_SKU_NAME"
  ensure_deployment "$EMBEDDING_DEPLOYMENT_NAME" "$EMBEDDING_MODEL_NAME" "$EMBEDDING_MODEL_VERSION" "$EMBEDDING_SKU_NAME"

  assert_deployment_exists "$GPT_DEPLOYMENT_NAME"
  assert_deployment_exists "$MINI_DEPLOYMENT_NAME"
  assert_deployment_exists "$EMBEDDING_DEPLOYMENT_NAME"

  echo "Esperando a que los deployments queden disponibles..."
  wait_deployment_succeeded "$GPT_DEPLOYMENT_NAME"
  wait_deployment_succeeded "$MINI_DEPLOYMENT_NAME"
  wait_deployment_succeeded "$EMBEDDING_DEPLOYMENT_NAME"

  echo "Configurando defaults de Content Understanding..."
  body="$(cat <<JSON
{
  "modelDeployments": {
    "$GPT_MODEL_NAME": "$GPT_DEPLOYMENT_NAME",
    "gpt-4.1-mini": "$MINI_DEPLOYMENT_NAME",
    "text-embedding-3-large": "$EMBEDDING_DEPLOYMENT_NAME",
    "prebuilt-analyzer-completion": "$GPT_DEPLOYMENT_NAME",
    "prebuilt-analyzer-completion-mini": "$MINI_DEPLOYMENT_NAME",
    "prebuilt-analyzer-embedding": "$EMBEDDING_DEPLOYMENT_NAME"
  }
}
JSON
)"
  patch_body_file="$(mktemp)"
  patch_code="$(curl -sS -o "$patch_body_file" -w "%{http_code}" \
    -X PATCH "$content_understanding_endpoint/contentunderstanding/defaults?api-version=$API_VERSION" \
    -H "Ocp-Apim-Subscription-Key: $key" \
    -H "Content-Type: application/json" \
    -d "$body")"
  if [[ "$patch_code" -lt 200 || "$patch_code" -ge 300 ]]; then
    echo "PATCH defaults fallo con HTTP $patch_code" >&2
    cat "$patch_body_file" >&2
    rm -f "$patch_body_file"
    exit 1
  fi
  rm -f "$patch_body_file"
fi

cat > "$ENV_PATH" <<ENV
CONTENT_UNDERSTANDING_ENDPOINT=$content_understanding_endpoint
CONTENT_UNDERSTANDING_KEY=$key
CONTENT_UNDERSTANDING_API_VERSION=$API_VERSION
CONTENT_UNDERSTANDING_INPUT_MODE=blob
AZURE_STORAGE_CONNECTION_STRING=$storage_connection_string
AZURE_STORAGE_CONTAINER=$STORAGE_CONTAINER
PORT=3060
ALLOWED_ORIGIN=http://localhost:5180
ENV

echo ""
echo "Azure Content Understanding listo. backend/.env actualizado."
echo "Resource group    : $RESOURCE_GROUP"
echo "Cuenta Foundry    : $ACCOUNT_NAME"
echo "Endpoint          : $content_understanding_endpoint"
echo "Storage account   : $STORAGE_ACCOUNT_NAME"
echo "Storage container : $STORAGE_CONTAINER"
echo "API version       : $API_VERSION"
if [[ "$SKIP_MODEL_DEFAULTS" != "true" ]]; then
  echo "Deployments       : $GPT_DEPLOYMENT_NAME, $MINI_DEPLOYMENT_NAME, $EMBEDDING_DEPLOYMENT_NAME"
  echo "Mini SKU          : $MINI_SKU_NAME"
  echo "Embedding SKU     : $EMBEDDING_SKU_NAME"
fi