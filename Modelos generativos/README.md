# Modelos Generativos

Aplicacion ligera para generar imagenes con modelos generativos en Azure AI Foundry / Azure AI Services.

La app funciona con Python + Streamlit en un solo proceso. El frontend React/Vite y el backend FastAPI originales quedan como referencia, pero ya no son necesarios para ejecutar la aplicacion.

## Stack

- App: Python + Streamlit
- Azure: Azure AI Foundry / Azure AI Services con deployment de imagen
- Modelo esperado: `MAI-Image-2.5`
- Modo demo local sin credenciales

## Funcionalidades

- Generacion de imagen desde prompt
- Seleccion de tamano
- Seleccion de calidad
- Vista previa de resultado
- Descarga de imagen generada
- Historial visual
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

- http://localhost:8502