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
cd "D:\Repository\Blockstellart\codigo-microsoft-azure-ai-fundamentals-ai-900\Visual Input"
.\start.ps1
```

En macOS/Linux:

```bash
cd "/ruta/a/codigo-microsoft-azure-ai-fundamentals-ai-900/Visual Input"
chmod +x start.sh
./start.sh
```

El script crea `.venv`, instala `requirements.txt` y levanta Streamlit.

URL local:

- http://localhost:8503

Para omitir la instalacion de dependencias cuando ya existe el entorno:

```powershell
.\start.ps1 -SkipInstall
```

En macOS/Linux:

```bash
./start.sh --skip-install
```

## Configurar credenciales

La app lee las credenciales desde:

```text
backend\.env
```

Copia el archivo de ejemplo:

```powershell
copy backend\.env.example backend\.env
notepad backend\.env
```

Variables:

```env
MICROSOFT_FOUNDRY_ENDPOINT=https://<tu-recurso>.openai.azure.com
MICROSOFT_FOUNDRY_API_KEY=<tu-key>
MICROSOFT_FOUNDRY_DEPLOYMENT_NAME=gpt-4o-mini
MICROSOFT_FOUNDRY_API_VERSION=2024-10-21
AZURE_IMAGE_DETAIL=low
```

Si `MICROSOFT_FOUNDRY_ENDPOINT` o `MICROSOFT_FOUNDRY_API_KEY` estan vacios, la aplicacion arranca en modo demo local.

## Crear Azure con Azure CLI

```powershell
az login
az account set --subscription "<SUBSCRIPTION_ID>"
cd "D:\Repository\Blockstellart\codigo-microsoft-azure-ai-fundamentals-ai-900\Visual Input"
.\scripts\create-azure.ps1
```

El script crea el resource group, crea el recurso Azure OpenAI, crea el deployment multimodal, obtiene endpoint/key y actualiza `backend\.env`.

Valores por defecto:

- Resource group: `rg-visual-input`
- Cuenta Azure OpenAI: `aoai-visual-input-demo`
- Deployment: `gpt-4o-mini`
- Modelo: `gpt-4o-mini`
- Version: `2024-07-18`

Confirma que el deployment quedo creado:

```powershell
az cognitiveservices account deployment list `
  --name aoai-visual-input-demo `
  --resource-group rg-visual-input `
  -o table
```

Debe aparecer:

```text
gpt-4o-mini
```

##### Comandos manuales equivalentes:

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
  --sku-capacity 1 `
  -o jsonc
```

```powershell
az cognitiveservices account show `
  --name aoai-visual-input-demo `
  --resource-group rg-visual-input `
  --query properties.endpoint `
  -o tsv
```

```powershell
az cognitiveservices account keys list `
  --name aoai-visual-input-demo `
  --resource-group rg-visual-input `
  --query key1 `
  -o tsv
```

Si tu region no soporta ese SKU/modelo, lista modelos disponibles:

```powershell
az cognitiveservices model list `
  --location eastus `
  --query "[?contains(model.name, 'gpt-4o') || contains(model.name, 'gpt-4.1')].[model.name, model.version, model.lifecycleStatus, skuName]" `
  -o table
```

## Crear servicios desde el portal de Azure

Pasos para crear el recurso sin CLI:

1. Entra a [Azure Portal](https://portal.azure.com).
2. Busca `Azure OpenAI` y selecciona crear un recurso.
3. Completa los campos principales:
   - Subscription: tu suscripcion.
   - Resource group: crea `rg-visual-input` o usa uno existente.
   - Region: por ejemplo `East US`, o una region disponible para tu suscripcion.
   - Name: un nombre unico, por ejemplo `aoai-visual-input-demo`.
   - Pricing tier: `S0` o el tier permitido por tu cuenta.
4. Revisa y crea el recurso.
5. Abre el recurso creado y entra a `Keys and Endpoint`.
6. Copia `Endpoint` en `MICROSOFT_FOUNDRY_ENDPOINT`.
7. Copia `KEY 1` en `MICROSOFT_FOUNDRY_API_KEY`.
8. Abre Azure AI Foundry.
9. En deployments, crea un deployment de `gpt-4o-mini` o `gpt-4o`.
10. Usa como nombre de deployment `gpt-4o-mini`.
11. Guarda estos valores en `backend\.env`:

```env
MICROSOFT_FOUNDRY_ENDPOINT=https://<tu-recurso>.openai.azure.com
MICROSOFT_FOUNDRY_API_KEY=<tu-key>
MICROSOFT_FOUNDRY_DEPLOYMENT_NAME=gpt-4o-mini
MICROSOFT_FOUNDRY_API_VERSION=2024-10-21
AZURE_IMAGE_DETAIL=low
```

12. Ejecuta `.\start.ps1` y abre http://localhost:8503.

Notas:

- El deployment debe ser multimodal y aceptar imagenes.
- Necesitas permisos de Azure RBAC para crear recursos y deployments, por ejemplo `Owner`, `Contributor` o permisos equivalentes.
- `AZURE_IMAGE_DETAIL` puede ser `low`, `high` o `auto`.

## Eliminar recursos

Borrar todo el resource group:

```powershell
az group delete `
  --name rg-visual-input `
  --yes `
  --no-wait
```

Con script:

```powershell
.\scripts\delete-azure.ps1 -NoWait
```

Para borrar e intentar purgar soft-delete:

```powershell
.\scripts\delete-azure.ps1 -NoWait -Purge
```

## Detener la app

Si la app corre en la misma terminal:

```text
Ctrl + C
```

Si quieres detenerla desde otra terminal:

```powershell
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8503 -State Listen).OwningProcess
```

## Referencia

La app llama a Chat Completions con contenido multimodal:

```text
/openai/deployments/<deployment>/chat/completions
```

El mensaje de usuario incluye texto y una imagen como `data:image/...;base64,...`.
