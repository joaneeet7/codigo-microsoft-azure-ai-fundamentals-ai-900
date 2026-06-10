#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-app-vision}"
ACCOUNT_NAME="${ACCOUNT_NAME:-vision-app-demo}"
LOCATION="${LOCATION:-eastus}"
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

Opciones:
  --resource-group <nombre>  Default: rg-app-vision
  --account-name <nombre>    Default: vision-app-demo
  --location <region>        Default: eastus
  --no-wait                  No esperar a que termine el borrado
  --purge                    Intentar purgar el recurso soft-deleted
HELP
      exit 0
      ;;
    *) echo "Opcion no reconocida: $1" >&2; exit 1 ;;
  esac
done

info() { printf '\033[36m%s\033[0m\n' "$1"; }
warn() { printf '\033[33m%s\033[0m\n' "$1"; }
success() { printf '\033[32m%s\033[0m\n' "$1"; }

info "Recursos actuales en $RESOURCE_GROUP:"
az resource list \
  --resource-group "$RESOURCE_GROUP" \
  --query "[].{name:name,type:type,location:location}" \
  -o table || true

if [[ "$NO_WAIT" == "true" ]]; then
  warn "Eliminando resource group en segundo plano: $RESOURCE_GROUP"
  az group delete --name "$RESOURCE_GROUP" --yes --no-wait
else
  warn "Eliminando resource group: $RESOURCE_GROUP"
  az group delete --name "$RESOURCE_GROUP" --yes
  success "Resource group eliminado: $RESOURCE_GROUP"
fi

if [[ "$PURGE" == "true" ]]; then
  warn "Intentando purgar cuenta soft-deleted: $ACCOUNT_NAME"
  az cognitiveservices account purge \
    --location "$LOCATION" \
    --resource-group "$RESOURCE_GROUP" \
    --name "$ACCOUNT_NAME"
fi

printf '\nComandos utiles si necesitas revisar soft-delete:\n'
printf 'az cognitiveservices account list-deleted -o table\n'
printf 'az cognitiveservices account purge --location %s --resource-group %s --name %s\n' "$LOCATION" "$RESOURCE_GROUP" "$ACCOUNT_NAME"