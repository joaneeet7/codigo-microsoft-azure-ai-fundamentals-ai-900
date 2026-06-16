# App Vision

Aplicacion ligera de Azure AI Vision Image Analysis 4.0. La app ahora se ejecuta con Python + Streamlit en un solo proceso, manteniendo la experiencia visual del sitio original.

## Stack

- App: Python + Streamlit
- Azure: Azure AI Vision / Computer Vision Image Analysis 4.0
- Modo demo local sin credenciales

El frontend React/Vite y el backend FastAPI originales quedan en el repositorio como referencia, pero ya no son necesarios para ejecutar la aplicacion.

## Funcionalidades

- Caption de imagen
- Dense captions
- Tags
- Deteccion de objetos
- OCR con Read
- Deteccion de personas
- Smart crops
- Modo demo local sin credenciales

## Ejecutar con un solo script

Desde PowerShell:

```powershell
.\start.ps1
```

En macOS/Linux:

```bash
chmod +x start.sh
./start.sh
```

El script crea `.venv`, instala `requirements.txt` y levanta Streamlit.

URL local:

- http://localhost:8501