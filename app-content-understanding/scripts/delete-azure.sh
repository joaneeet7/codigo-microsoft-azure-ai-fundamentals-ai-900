#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="rg-content-understanding"
ACCOUNT_NAME="cu-foundry-demo"
LOCATION="eastus"
NO_WAIT="false"
PURGE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
    --account-name) ACCOUNT_NAME="$2"; shift 2 ;;
    --location) LOCATION="$2"; shift 2 ;;
    --no-wait) NO_WAIT="true"; shift ;;
    --purge) PURGE="true"; shift ;;
    -h|--help)
      cat <<HELP
Uso: ./scripts/delete-azure.sh [opciones]
  --resource-group NAME
  --account-name NAME
  --location LOCATION
  --no-wait
  --purge
HELP
      exit 0 ;;
    *) echo "Opcion desconocida: $1" >&2; exit 1 ;;
  esac
done

if ! command -v az >/dev/null 2>&1; then
  echo "Falta 'az'. Instala Azure CLI." >&2
  exit 1
fi

echo "Recursos actuales en $RESOURCE_GROUP:"
az resource list --resource-group "$RESOURCE_GROUP" --query "[].{name:name,type:type,location:location}" -o table || true

if [[ "$NO_WAIT" == "true" ]]; then
  echo "Eliminando resource group en segundo plano: $RESOURCE_GROUP"
  az group delete --name "$RESOURCE_GROUP" --yes --no-wait
else
  echo "Eliminando resource group: $RESOURCE_GROUP"
  az group delete --name "$RESOURCE_GROUP" --yes
  echo "Resource group eliminado: $RESOURCE_GROUP"
fi

if [[ "$PURGE" == "true" ]]; then
  echo "Intentando purgar cuenta soft-deleted: $ACCOUNT_NAME"
  az cognitiveservices account purge --location "$LOCATION" --resource-group "$RESOURCE_GROUP" --name "$ACCOUNT_NAME"
fi