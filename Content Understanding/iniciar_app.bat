@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Preparando la app por primera vez...
  py -m venv .venv
  if errorlevel 1 (
    python -m venv .venv
  )
)

echo Instalando o revisando dependencias...
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo La app se abrira en el navegador:
echo http://localhost:8501
echo.

".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501
