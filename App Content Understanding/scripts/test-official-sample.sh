#!/usr/bin/env bash
set -euo pipefail

ANALYZER_ID="prebuilt-invoice"
INPUT_URL="https://github.com/Azure-Samples/azure-ai-content-understanding-python/raw/refs/heads/main/data/invoice.pdf"
API_VERSION="2025-11-01"
MAX_ATTEMPTS="90"
DELAY_SECONDS="2"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --analyzer-id) ANALYZER_ID="$2"; shift 2 ;;
    --input-url) INPUT_URL="$2"; shift 2 ;;
    --api-version) API_VERSION="$2"; shift 2 ;;
    --max-attempts) MAX_ATTEMPTS="$2"; shift 2 ;;
    --delay-seconds) DELAY_SECONDS="$2"; shift 2 ;;
    -h|--help)
      cat <<HELP
Uso: ./scripts/test-official-sample.sh [opciones]
  --analyzer-id prebuilt-invoice|prebuilt-documentSearch
  --input-url URL
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

require_cmd curl
require_cmd jq

if [[ ! -f "$ENV_PATH" ]]; then
  echo "No existe backend/.env." >&2
  exit 1
fi

ENDPOINT="$(cu_endpoint "$(read_env_value CONTENT_UNDERSTANDING_ENDPOINT)")"
KEY="$(read_env_value CONTENT_UNDERSTANDING_KEY)"
if [[ -z "$ENDPOINT" || -z "$KEY" ]]; then
  echo "Faltan CONTENT_UNDERSTANDING_ENDPOINT o CONTENT_UNDERSTANDING_KEY en backend/.env." >&2
  exit 1
fi

echo "Endpoint : $ENDPOINT"
echo "Analyzer : $ANALYZER_ID"
echo "Input    : $INPUT_URL"
echo ""
echo "Defaults actuales"
curl -sS "$ENDPOINT/contentunderstanding/defaults?api-version=$API_VERSION" \
  -H "Ocp-Apim-Subscription-Key: $KEY" | jq . || true

echo ""
echo "Enviando analisis oficial..."
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