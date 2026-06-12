#!/usr/bin/env bash
set -euo pipefail

ANALYZER_ID="prebuilt-documentSearch"
FILE_PATH=""
API_VERSION="2025-11-01"
MAX_ATTEMPTS="90"
DELAY_SECONDS="2"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --analyzer-id) ANALYZER_ID="$2"; shift 2 ;;
    --file-path) FILE_PATH="$2"; shift 2 ;;
    --api-version) API_VERSION="$2"; shift 2 ;;
    --max-attempts) MAX_ATTEMPTS="$2"; shift 2 ;;
    --delay-seconds) DELAY_SECONDS="$2"; shift 2 ;;
    -h|--help)
      cat <<HELP
Uso: ./scripts/test-blob-input.sh --file-path /ruta/invoice.pdf [--analyzer-id prebuilt-invoice]
HELP
      exit 0 ;;
    *) echo "Opcion desconocida: $1" >&2; exit 1 ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_PATH="$ROOT_DIR/backend/.env"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Falta '$1'. En mac puedes instalarlo con: brew install $1" >&2
    exit 1
  fi
}

read_env_value() {
  local name="$1"
  grep -E "^[[:space:]]*$name=" "$ENV_PATH" | tail -n 1 | cut -d= -f2-
}

cu_endpoint() {
  local endpoint="$1"
  endpoint="${endpoint%/}"
  printf "%s" "${endpoint/.cognitiveservices.azure.com/.services.ai.azure.com}"
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
  rm -f "$err_file"
  printf "%s" "$output"
}

require_cmd az
require_cmd curl
require_cmd jq

if [[ ! -f "$ENV_PATH" ]]; then
  echo "No existe backend/.env." >&2
  exit 1
fi
if [[ -z "$FILE_PATH" ]]; then
  echo "Pasa un archivo local con --file-path. Ejemplo: ./scripts/test-blob-input.sh --file-path ./invoice.pdf" >&2
  exit 1
fi
if [[ ! -f "$FILE_PATH" ]]; then
  echo "No existe el archivo: $FILE_PATH" >&2
  exit 1
fi

ENDPOINT="$(cu_endpoint "$(read_env_value CONTENT_UNDERSTANDING_ENDPOINT)")"
KEY="$(read_env_value CONTENT_UNDERSTANDING_KEY)"
STORAGE_CONNECTION_STRING="$(read_env_value AZURE_STORAGE_CONNECTION_STRING)"
CONTAINER="$(read_env_value AZURE_STORAGE_CONTAINER)"
if [[ -z "$ENDPOINT" || -z "$KEY" ]]; then
  echo "Faltan CONTENT_UNDERSTANDING_ENDPOINT o CONTENT_UNDERSTANDING_KEY en backend/.env." >&2
  exit 1
fi
if [[ -z "$STORAGE_CONNECTION_STRING" || -z "$CONTAINER" ]]; then
  echo "Faltan AZURE_STORAGE_CONNECTION_STRING o AZURE_STORAGE_CONTAINER en backend/.env." >&2
  exit 1
fi

BASENAME="$(basename "$FILE_PATH")"
BLOB_NAME="diagnostics/$(uuidgen)-$BASENAME"
EXPIRY="$(date -u -v+1H '+%Y-%m-%dT%H:%MZ' 2>/dev/null || date -u -d '+1 hour' '+%Y-%m-%dT%H:%MZ')"

echo "Subiendo archivo a Blob Storage..."
az_cli storage blob upload \
  --connection-string "$STORAGE_CONNECTION_STRING" \
  --container-name "$CONTAINER" \
  --name "$BLOB_NAME" \
  --file "$FILE_PATH" \
  --overwrite true > /dev/null

SAS="$(az_cli storage blob generate-sas \
  --connection-string "$STORAGE_CONNECTION_STRING" \
  --container-name "$CONTAINER" \
  --name "$BLOB_NAME" \
  --permissions r \
  --expiry "$EXPIRY" \
  -o tsv)"

ACCOUNT_NAME="$(printf "%s" "$STORAGE_CONNECTION_STRING" | tr ';' '\n' | awk -F= '$1=="AccountName" {print $2}')"
if [[ -z "$ACCOUNT_NAME" ]]; then
  echo "No pude leer AccountName desde AZURE_STORAGE_CONNECTION_STRING." >&2
  exit 1
fi

INPUT_URL="https://$ACCOUNT_NAME.blob.core.windows.net/$CONTAINER/$BLOB_NAME?$SAS"

echo "Endpoint : $ENDPOINT"
echo "Analyzer : $ANALYZER_ID"
echo "Archivo  : $BASENAME"
echo "Blob SAS : generado por 1 hora"
echo ""
echo "Enviando analisis con Blob SAS..."

REQUEST_BODY="$(jq -n --arg url "$INPUT_URL" '{inputs:[{url:$url}]}')"
HEADER_FILE="$(mktemp)"
BODY_FILE="$(mktemp)"
HTTP_CODE="$(curl -sS -D "$HEADER_FILE" -o "$BODY_FILE" -w "%{http_code}" \
  -X POST "$ENDPOINT/contentunderstanding/analyzers/${ANALYZER_ID}:analyze?api-version=$API_VERSION" \
  -H "Ocp-Apim-Subscription-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d "$REQUEST_BODY")"

if [[ "$HTTP_CODE" != "202" ]]; then
  echo "POST fallo con HTTP $HTTP_CODE" >&2
  cat "$BODY_FILE" >&2
  rm -f "$HEADER_FILE" "$BODY_FILE"
  exit 1
fi

OPERATION_LOCATION="$(awk 'BEGIN{IGNORECASE=1} /^Operation-Location:/ {sub(/\r$/, "", $0); print substr($0, index($0, ":")+2)}' "$HEADER_FILE" | tail -n 1)"
rm -f "$HEADER_FILE" "$BODY_FILE"
if [[ -z "$OPERATION_LOCATION" ]]; then
  echo "Azure no devolvio Operation-Location." >&2
  exit 1
fi

echo "Operation-Location recibido."

for ((attempt=1; attempt<=MAX_ATTEMPTS; attempt++)); do
  RESULT="$(curl -sS "$OPERATION_LOCATION" -H "Ocp-Apim-Subscription-Key: $KEY")"
  STATUS="$(printf "%s" "$RESULT" | jq -r '.status // empty')"
  echo "Estado: $STATUS ($attempt/$MAX_ATTEMPTS)"

  if [[ "$STATUS" == "Succeeded" ]]; then
    echo "Analisis correcto."
    printf "%s" "$RESULT" | jq .
    exit 0
  fi

  if [[ "$STATUS" == "Failed" || "$STATUS" == "Error" || "$STATUS" == "Canceled" || "$STATUS" == "Cancelled" ]]; then
    echo "Analisis fallo." >&2
    printf "%s" "$RESULT" | jq .
    exit 1
  fi

  sleep "$DELAY_SECONDS"
done

echo "Timeout esperando resultado." >&2
exit 1