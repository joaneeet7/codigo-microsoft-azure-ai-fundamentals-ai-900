#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ ! -f ".venv/bin/python" ]; then
  echo "Preparando la app por primera vez..."
  python3 -m venv .venv
fi

echo "Instalando o revisando dependencias..."
".venv/bin/python" -m pip install -r requirements.txt

echo
echo "La app se abrira en el navegador:"
echo "http://localhost:8501"
echo

".venv/bin/python" -m streamlit run app.py --server.port 8501
