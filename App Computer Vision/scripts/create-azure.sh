#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-app-vision}"
LOCATION="${LOCATION:-eastus}"
ACCOUNT_NAME="${ACCOUNT_NAME:-vision-app-demo}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_PATH="$PROJECT_ROOT/backend/.env"

info() { printf '\033[36m%s\033[0m\n' "$1"; }
success() { printf '\033[32m%s\033[0m\n' "$1"; }

info "Validando sesion de Azure CLI..."
az account show >/dev/null

info "Creando resource group: $RESOURCE_GROUP ($LOCATION)"
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" >/dev/null

info "Creando recurso Azure AI Vision: $ACCOUNT_NAME"
az cognitiveservices account create \
  --name "$ACCOUNT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --kind ComputerVision \
  --sku S1 \
  --yes >/dev/null

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
VISION_ENDPOINT=$endpoint
VISION_KEY=$key
VISION_API_VERSION=2024-02-01
PORT=3050
ALLOWED_ORIGIN=http://localhost:5179
EOF

printf '\n'
success "Azure AI Vision listo. Archivo backend/.env actualizado."
printf 'Resource group : %s\n' "$RESOURCE_GROUP"
printf 'Cuenta Vision  : %s\n' "$ACCOUNT_NAME"
printf 'Endpoint       : %s\n' "$endpoint"
printf '\nPara probar:\n'
printf '  npm run dev:backend\n'
printf '  npm run dev:frontend\n'