#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TERRAFORM_DIR="$ROOT_DIR/infra/terraform"
TFVARS_FILE="$TERRAFORM_DIR/terraform.tfvars"
TFVARS_EXAMPLE="$TERRAFORM_DIR/terraform.tfvars.example"
BACKEND_ENV_FILE="$ROOT_DIR/backend/.env"
BACKEND_PORT="3022"
FRONTEND_PORT="5175"

info() { printf "\n[info] %s\n" "$1"; }
ok() { printf "\n[ok] %s\n" "$1"; }
fail() { printf "\n[error] %s\n" "$1" >&2; exit 1; }

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
  local temp_file

  temp_file="${file}.tmp"

  awk -v key="$key" -v value="$value" '
    BEGIN { written = 0; line = key " = \"" value "\"" }
    $0 ~ "^[[:space:]]*" key "[[:space:]]*=" {
      if (!written) { print line; written = 1 }
      next
    }
    { print }
    END { if (!written) print line }
  ' "$file" >"$temp_file"

  mv "$temp_file" "$file"
}

ensure_python() {
  PYTHON_CMD=""
  if command -v python >/dev/null 2>&1 && python -c "import sys" >/dev/null 2>&1; then
    PYTHON_CMD="python"
  elif command -v py >/dev/null 2>&1 && py -c "import sys" >/dev/null 2>&1; then
    PYTHON_CMD="py"
  else
    fail "No encontre Python funcional. Instala Python 3 o habilita py."
  fi
}

ensure_python_pip() {
  if "$PYTHON_CMD" -m pip --version >/dev/null 2>&1; then
    return
  fi

  info "Python no tiene pip. Intentando activarlo con ensurepip"
  if "$PYTHON_CMD" -m ensurepip --upgrade >/dev/null 2>&1; then
    ok "pip activado"
    return
  fi

  fail "No pude activar pip. Ejecuta: py -m ensurepip --upgrade"
}

ensure_dependencies() {
  local npm_bin="$1"
  cd "$ROOT_DIR"

  info "Validando dependencias npm"
  if [[ ! -d "$ROOT_DIR/node_modules" ]]; then
    "$npm_bin" install
  fi

  if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
    "$npm_bin" install --prefix frontend
  fi

  if ! "$PYTHON_CMD" -c "import fastapi, uvicorn, dotenv, azure.cognitiveservices.speech" >/dev/null 2>&1; then
    ensure_python_pip
    info "Instalando dependencias Python"
    "$PYTHON_CMD" -m pip install -r backend/requirements.txt
  else
    ok "Dependencias Python listas"
  fi
}

run_terraform() {
  require_command az
  require_command terraform

  info "Validando sesion de Azure"
  if ! az account show >/dev/null 2>&1; then
    info "No hay una sesion activa. Abriendo az login..."
    az login >/dev/null
  fi

  local subscription_id
  local subscription_name
  subscription_id="$(az account show --query id -o tsv)"
  subscription_name="$(az account show --query name -o tsv)"

  if [[ -z "$subscription_id" ]]; then
    fail "No pude obtener el subscription_id desde Azure CLI."
  fi

  info "Usando suscripcion: ${subscription_name} (${subscription_id})"

  if [[ ! -f "$TFVARS_FILE" ]]; then
    cp "$TFVARS_EXAMPLE" "$TFVARS_FILE"
  fi

  replace_or_add_tfvar "subscription_id" "$subscription_id" "$TFVARS_FILE"
  replace_or_add_tfvar "backend_port" "$BACKEND_PORT" "$TFVARS_FILE"
  replace_or_add_tfvar "frontend_origin" "http://localhost:${FRONTEND_PORT}" "$TFVARS_FILE"

  info "Ejecutando Terraform"
  cd "$TERRAFORM_DIR"
  terraform init -upgrade
  terraform plan -out main.tfplan
  terraform apply main.tfplan

  ok "Terraform termino. Variables para backend/.env:"
  terraform output -raw backend_env

  printf "\n\nQuieres escribir automaticamente estos valores en backend/.env? (S/N): "
  read -r write_env
  if [[ "$write_env" =~ ^[sS]$ ]]; then
    terraform output -raw backend_env >"$BACKEND_ENV_FILE"
    ok "backend/.env actualizado"
  else
    info "No se modifico backend/.env. Copia el bloque anterior manualmente si quieres usar Azure Speech."
  fi
}

wait_for_backend() {
  node - <<'NODE'
const url = "http://localhost:3022/health";
const deadline = Date.now() + 60000;

async function waitForBackend() {
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        console.log("[ok] Backend listo en http://localhost:3022");
        return;
      }
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
  throw new Error(`El backend no respondio a tiempo en ${url}`);
}

waitForBackend().catch((error) => {
  console.error(`[error] ${error.message}`);
  process.exit(1);
});
NODE
}

start_app() {
  local npm_bin="$1"

  info "Levantando backend"
  cd "$ROOT_DIR/backend"
  "$PYTHON_CMD" -m uvicorn app.main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT" &
  BACKEND_PID=$!
  cd "$ROOT_DIR"

  cleanup() {
    if kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
      kill "$BACKEND_PID" >/dev/null 2>&1 || true
    fi
  }
  trap cleanup EXIT

  wait_for_backend

  info "Levantando frontend"
  "$npm_bin" run dev:frontend
}

cat <<'MENU'

Selecciona una opcion:
1) Despliegue en Terraform + backend + frontend
2) Solo backend + frontend
3) Solo Terraform
MENU

printf "Opcion [1/2/3]: "
read -r option

case "$option" in
  1)
    require_command node
    ensure_python
    NPM="$(npm_command)"
    ensure_dependencies "$NPM"
    run_terraform
    start_app "$NPM"
    ;;
  2)
    require_command node
    ensure_python
    NPM="$(npm_command)"
    ensure_dependencies "$NPM"
    start_app "$NPM"
    ;;
  3)
    run_terraform
    ok "Solo Terraform terminado. No se levantaron backend ni frontend."
    ;;
  *)
    fail "Opcion invalida. Usa 1, 2 o 3."
    ;;
esac
