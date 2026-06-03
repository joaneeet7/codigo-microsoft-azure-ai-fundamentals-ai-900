#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TERRAFORM_DIR="$ROOT_DIR/infra/terraform"
TFVARS_FILE="$TERRAFORM_DIR/terraform.tfvars"
TFVARS_EXAMPLE="$TERRAFORM_DIR/terraform.tfvars.example"
BACKEND_ENV_FILE="$ROOT_DIR/backend/.env"

info() {
  printf "\n[info] %s\n" "$1"
}

fail() {
  printf "\n[error] %s\n" "$1" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "No encontre '$1'. Instalalo y vuelve a ejecutar el script."
}

npm_command() {
  if command -v npm.cmd >/dev/null 2>&1; then
    printf "npm.cmd"
  else
    printf "npm"
  fi
}

replace_or_add_tfvar() {
  local key="$1"
  local value="$2"
  local file="$3"

  if grep -qE "^[[:space:]]*${key}[[:space:]]*=" "$file"; then
    sed -i.bak -E "s|^[[:space:]]*${key}[[:space:]]*=.*|${key} = \"${value}\"|" "$file"
    rm -f "${file}.bak"
  else
    printf '%s = "%s"\n' "$key" "$value" >>"$file"
  fi
}

require_command az
require_command terraform
require_command node

NPM="$(npm_command)"

info "=========Validando sesion de Azure========="
if ! az account show >/dev/null 2>&1; then
  info "=========No hay una sesion activa. Abriendo az login...========="
  az login >/dev/null
fi

SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
SUBSCRIPTION_NAME="$(az account show --query name -o tsv)"

if [[ -z "$SUBSCRIPTION_ID" ]]; then
  fail "=========No pude obtener el subscription_id desde Azure CLI.========="
fi

info "=========Usando suscripcion: ${SUBSCRIPTION_NAME} (${SUBSCRIPTION_ID})========="

info "=========Preparando terraform.tfvars========="
if [[ ! -f "$TFVARS_FILE" ]]; then
  cp "$TFVARS_EXAMPLE" "$TFVARS_FILE"
fi

replace_or_add_tfvar "subscription_id" "$SUBSCRIPTION_ID" "$TFVARS_FILE"

info "=========Instalando dependencias si hacen falta========="
cd "$ROOT_DIR"
if [[ ! -d "$ROOT_DIR/node_modules" ]]; then
  "$NPM" install
fi

if [[ ! -d "$ROOT_DIR/backend/node_modules" ]]; then
  "$NPM" install --prefix backend
fi

if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  "$NPM" install --prefix frontend
fi

info "=========Inicializando Terraform========="
cd "$TERRAFORM_DIR"
terraform init -upgrade

info "=========Generando plan de Terraform========="
terraform plan -out main.tfplan

info "=========Aplicando infraestructura en Azure========="
terraform apply main.tfplan

info "=========Escribiendo variables de Foundry en backend/.env========="
terraform output -raw backend_env >"$BACKEND_ENV_FILE"

printf "\n[ok] backend/.env generado:\n"
cat "$BACKEND_ENV_FILE"

info "=========Levantando backend========="
cd "$ROOT_DIR"

"$NPM" run dev:backend &
BACKEND_PID=$!

cleanup() {
  if kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

info "=========Esperando a que el backend responda en http://localhost:3001/health========="
node - <<'NODE'
const url = "http://localhost:3001/health";
const deadline = Date.now() + 60000;

async function waitForBackend() {
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        console.log("[ok] Backend listo");
        return;
      }
    } catch {
      // Backend is still starting.
    }

    await new Promise((resolve) => setTimeout(resolve, 1500));
  }

  throw new Error(`El backend no respondio a tiempo en ${url}`);
}

waitForBackend().catch((error) => {
  console.error(`[error] ${error.message}`);
  process.exit(1);
});
NODE

info "=========Levantando frontend========="
"$NPM" run dev:frontend
