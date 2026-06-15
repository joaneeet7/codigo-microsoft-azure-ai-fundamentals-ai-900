#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
SKIP_INSTALL="false"

for arg in "$@"; do
  case "$arg" in
    --skip-install)
      SKIP_INSTALL="true"
      ;;
    *)
      echo "Argumento no soportado: $arg" >&2
      echo "Uso: ./start.sh [--skip-install]" >&2
      exit 1
      ;;
  esac
done

if [ ! -x "$PYTHON_BIN" ]; then
  python3 -m venv "$VENV_DIR"
fi

if [ "$SKIP_INSTALL" != "true" ]; then
  "$PYTHON_BIN" -m pip install --upgrade pip
  "$PYTHON_BIN" -m pip install -r "$ROOT_DIR/requirements.txt"
fi

export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

"$PYTHON_BIN" -m streamlit run "$ROOT_DIR/streamlit_app.py" \
  --server.address 0.0.0.0 \
  --server.port 8503 \
  --server.headless true
