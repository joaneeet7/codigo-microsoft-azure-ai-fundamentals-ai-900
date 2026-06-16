# Visual Input

Aplicacion ligera para interpretar imagenes dentro de prompts usando un modelo multimodal en Azure OpenAI / Microsoft Foundry.

La app funciona con Python + Streamlit en un solo proceso. El frontend React/Vite y el backend FastAPI originales quedan como referencia, pero ya no son necesarios para ejecutar la aplicacion.

## Stack

- App: Python + Streamlit
- Azure: Azure OpenAI con deployment multimodal
- Modelo esperado: `gpt-4o-mini` o `gpt-4o`
- Modo demo local sin credenciales

## Funcionalidades

- Carga de imagen PNG, JPG o WEBP
- Prompt textual multimodal
- Interpretacion visual con modelo multimodal
- Render basico de Markdown en la respuesta
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

- http://localhost:8503