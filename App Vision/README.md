# App Vision

Aplicacion ligera con funcionalidades de vision usando Azure AI Vision Image Analysis 4.0.

## Stack

- Backend: Python + FastAPI
- Frontend: React + Vite + TypeScript
- Azure: Azure AI Vision / Computer Vision Image Analysis 4.0

## Funcionalidades

- Caption de imagen
- Dense captions
- Tags
- Deteccion de objetos
- OCR con Read
- Deteccion de personas
- Smart crops
- Modo demo local sin credenciales

## Instalar

```powershell
cd C:\Users\li-ve\Documents\Codex\2026-06-02\app-vision
npm.cmd install
npm.cmd install --prefix frontend
cd backend
py -m pip install -r requirements.txt
cd ..
copy backend\.env.example backend\.env
```

## Crear Azure con Azure CLI

```powershell
az login
az account set --subscription "<SUBSCRIPTION_ID>"
cd C:\Users\li-ve\Documents\Codex\2026-06-02\app-vision
.\scripts\create-azure.ps1
```

En macOS/Linux:

```bash
az login
az account set --subscription "<SUBSCRIPTION_ID>"
cd /ruta/a/app-vision
chmod +x scripts/create-azure.sh scripts/delete-azure.sh
./scripts/create-azure.sh
```

Comandos manuales equivalentes:

```powershell
az group create `
  --name rg-app-vision `
  --location eastus
```

```powershell
az cognitiveservices account create `
  --name vision-app-demo `
  --resource-group rg-app-vision `
  --location eastus `
  --kind ComputerVision `
  --sku S1 `
  --yes
```

```powershell
az cognitiveservices account show `
  --name vision-app-demo `
  --resource-group rg-app-vision `
  --query properties.endpoint `
  -o tsv
```

```powershell
az cognitiveservices account keys list `
  --name vision-app-demo `
  --resource-group rg-app-vision `
  --query key1 `
  -o tsv
```

## Eliminar recursos

Borrar todo el resource group:

```powershell
az group delete `
  --name rg-app-vision `
  --yes `
  --no-wait
```

Si el nombre queda en soft-delete y quieres purgarlo:

```powershell
az cognitiveservices account purge `
  --location eastus `
  --resource-group rg-app-vision `
  --name vision-app-demo
```

Con script:

```powershell
.\scripts\delete-azure.ps1 -NoWait
```

En macOS/Linux:

```bash
./scripts/delete-azure.sh --no-wait
```

Para borrar e intentar purgar soft-delete en macOS/Linux:

```bash
./scripts/delete-azure.sh --no-wait --purge
```

## Ejecutar manualmente

Backend:

```powershell
cd C:\Users\li-ve\Documents\Codex\2026-06-02\app-vision
npm.cmd run dev:backend
```

Frontend, en otra terminal:

```powershell
cd C:\Users\li-ve\Documents\Codex\2026-06-02\app-vision
npm.cmd run dev:frontend
```

URLs:

- Frontend: http://localhost:5179
- Backend: http://localhost:3050

## Referencia

Azure AI Vision Image Analysis 4.0 usa el endpoint `computervision/imageanalysis:analyze` con features como `caption`, `denseCaptions`, `tags`, `objects`, `read`, `people` y `smartCrops`.