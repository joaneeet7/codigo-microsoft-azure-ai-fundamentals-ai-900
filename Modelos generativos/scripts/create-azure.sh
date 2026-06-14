#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-modelos-generativos}"
LOCATION="${LOCATION:-eastus}"
ACCOUNT_NAME="${ACCOUNT_NAME:-aifoundry-modelos-img-eastus}"
DEPLOYMENT_NAME="${DEPLOYMENT_NAME:-mai-image-2-5}"
MODEL_NAME="${MODEL_NAME:-MAI-Image-2.5}"
MODEL_VERSION="${MODEL_VERSION:-2026-06-02}"
SKU_NAME="${SKU_NAME:-GlobalStandard}"
SKU_CAPACITY="${SKU_CAPACITY:-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_PATH="$PROJECT_ROOT/backend/.env"

info() {
  printf '\033[36m%s\033[0m\n' "$1"
}

success() {
  printf '\033[32m%s\033[0m\n' "$1"
}

info "Validando sesion de Azure CLI..."
az account show >/dev/null

info "Creando resource group: $RESOURCE_GROUP ($LOCATION)"
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" >/dev/null

info "Creando recurso Azure AI Foundry / AI Services: $ACCOUNT_NAME"
az cognitiveservices account create \
  --name "$ACCOUNT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --kind AIServices \
  --sku S0 \
  --custom-domain "$ACCOUNT_NAME" \
  --yes >/dev/null

info "Creando deployment de imagen: $DEPLOYMENT_NAME -> $MODEL_NAME ($MODEL_VERSION)"
az cognitiveservices account deployment create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$ACCOUNT_NAME" \
  --deployment-name "$DEPLOYMENT_NAME" \
  --model-name "$MODEL_NAME" \
  --model-version "$MODEL_VERSION" \
  --model-format Microsoft \
  --sku-name "$SKU_NAME" \
  --sku-capacity "$SKU_CAPACITY" >/dev/null

endpoint="$(az cognitiveservices account show \
  --name "$ACCOUNT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query properties.endpoint \
  -o tsv)"

key="$(az cognitiveservices account keys list \
  --name "$ACCOUNT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query key1 \
  -o tsv)"

cat > "$ENV_PATH" <<EOF
AZURE_OPENAI_ENDPOINT=$endpoint
AZURE_OPENAI_API_KEY=$key
AZURE_OPENAI_DEPLOYMENT_NAME=$DEPLOYMENT_NAME
AZURE_OPENAI_MODEL_NAME=$MODEL_NAME
IMAGE_PROVIDER=mai
AZURE_OPENAI_API_VERSION=$MODEL_VERSION
PORT=3030
ALLOWED_ORIGIN=http://localhost:5176
EOF

printf '\n'
success "Azure listo. Archivo backend/.env actualizado."
printf 'Resource group : %s\n' "$RESOURCE_GROUP"
printf 'Cuenta         : %s\n' "$ACCOUNT_NAME"
printf 'Endpoint       : %s\n' "$endpoint"
printf 'Deployment     : %s\n' "$DEPLOYMENT_NAME"
printf 'Modelo         : %s\n' "$MODEL_NAME"
printf 'Provider       : mai\n'
printf '\nPara probar:\n'
printf '  npm run dev:backend\n'
printf '  npm run dev:frontend\n'