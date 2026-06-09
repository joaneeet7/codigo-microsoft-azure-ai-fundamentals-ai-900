# Visual Input

Demo ligera para interpretar una entrada visual dentro de prompts usando un modelo multimodal desplegado en Azure OpenAI / Microsoft Foundry.

## Stack

- Backend: Python + FastAPI
- Frontend: React + Vite + TypeScript
- Azure: Azure OpenAI con un deployment multimodal, por ejemplo `gpt-4o-mini` o `gpt-4o`

## Configuracion local

```powershell
cd C:\Users\li-ve\Documents\Codex\2026-06-02\visual-input
npm.cmd install
npm.cmd install --prefix frontend
cd backend
py -m pip install -r requirements.txt
cd ..
copy backend\.env.example backend\.env
```

Si `backend/.env` no tiene endpoint/key, el backend responde en modo demo local.

## Crear recursos con Azure CLI

Primero inicia sesion:

```powershell
az login
az account set --subscription "<SUBSCRIPTION_ID>"
```

Opcion automatizada:

```powershell
cd C:\Users\li-ve\Documents\Codex\2026-06-02\visual-input
.\scripts\create-azure.ps1
```

En macOS/Linux:

```bash
cd /ruta/a/visual-input
chmod +x scripts/create-azure.sh scripts/delete-azure.sh
./scripts/create-azure.sh
```

Comandos manuales equivalentes:

```powershell
az group create `
  --name rg-visual-input `
  --location eastus
```

```powershell
az cognitiveservices account create `
  --name aoai-visual-input-demo `
  --resource-group rg-visual-input `
  --location eastus `
  --kind OpenAI `
  --sku S0 `
  --yes
```

```powershell
az cognitiveservices account deployment create `
  --resource-group rg-visual-input `
  --name aoai-visual-input-demo `
  --deployment-name gpt-4o-mini `
  --model-name gpt-4o-mini `
  --model-version "2024-07-18" `
  --model-format OpenAI `
  --sku-name GlobalStandard `
  --sku-capacity 1
```

Si tu region no soporta ese SKU/modelo, lista modelos disponibles:

```powershell
az cognitiveservices model list `
  --location eastus `
  --query "[?contains(model.name, 'gpt-4o') || contains(model.name, 'gpt-4.1')].[model.name, model.version, model.lifecycleStatus, skuName]" `
  -o table
```

## Eliminar recursos con Azure CLI

Borrar todo el resource group:

```powershell
az group delete `
  --name rg-visual-input `
  --yes `
  --no-wait
```

O con el script incluido:

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

Si quieres conservar el grupo y borrar solo el recurso OpenAI:

```powershell
az cognitiveservices account delete `
  --name aoai-visual-input-demo `
  --resource-group rg-visual-input
```

Ver recursos antes de borrar:

```powershell
az resource list `
  --resource-group rg-visual-input `
  --query "[].{name:name,type:type,location:location}" `
  -o table
```

## Ejecutar manualmente

Backend:

```powershell
cd C:\Users\li-ve\Documents\Codex\2026-06-02\visual-input
npm.cmd run dev:backend
```

Frontend, en otra terminal:

```powershell
cd C:\Users\li-ve\Documents\Codex\2026-06-02\visual-input
npm.cmd run dev:frontend
```

URLs:

- Frontend: http://localhost:5178
- Backend: http://localhost:3040

## Referencia

Microsoft documenta que los modelos multimodales con vision aceptan contenido de usuario con texto e imagen en formato URL o data URI base64 mediante Chat Completions.