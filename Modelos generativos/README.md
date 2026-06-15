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
cd "D:\Repository\Blockstellart\codigo-microsoft-azure-ai-fundamentals-ai-900\Modelos generativos"
.\start.ps1
```

El script crea `.venv`, instala `requirements.txt` y levanta Streamlit.

URL local:

- http://localhost:8502

Para omitir la instalacion de dependencias cuando ya existe el entorno:

```powershell
.\start.ps1 -SkipInstall
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
AZURE_OPENAI_ENDPOINT=https://<tu-recurso>.cognitiveservices.azure.com
AZURE_OPENAI_API_KEY=<tu-key>
AZURE_OPENAI_DEPLOYMENT_NAME=mai-image-2-5
AZURE_OPENAI_MODEL_NAME=MAI-Image-2.5
IMAGE_PROVIDER=mai
AZURE_OPENAI_API_VERSION=2026-06-02
```

Si `AZURE_OPENAI_ENDPOINT` o `AZURE_OPENAI_API_KEY` estan vacios, la aplicacion arranca en modo demo local.

## Crear Azure con Azure CLI

```powershell
az group create `
  --name rg-modelos-generativos `
  --location eastus
```

```powershell
az cognitiveservices account create `
  --name aifoundry-modelos-img-eastus `
  --resource-group rg-modelos-generativos `
  --location eastus `
  --kind AIServices `
  --sku S0 `
  --custom-domain aifoundry-modelos-img-eastus `
  --yes
```

```powershell
az cognitiveservices account deployment create `
  --resource-group rg-modelos-generativos `
  --name aifoundry-modelos-img-eastus `
  --deployment-name mai-image-2-5 `
  --model-name "MAI-Image-2.5" `
  --model-version "2026-06-02" `
  --model-format Microsoft `
  --sku-name GlobalStandard `
  --sku-capacity 1 `
  -o jsonc
```

```powershell
az cognitiveservices account show `
  --name aifoundry-modelos-img-eastus `
  --resource-group rg-modelos-generativos `
  --query properties.endpoint `
  -o tsv
```

```powershell
az cognitiveservices account keys list `
  --name aifoundry-modelos-img-eastus `
  --resource-group rg-modelos-generativos `
  --query key1 `
  -o tsv
```

## Crear servicios desde el portal de Azure

Pasos para crear el recurso sin CLI:

1. Entra a [Azure Portal](https://portal.azure.com).
2. Busca `Azure AI services` y selecciona crear un recurso.
3. Completa los campos principales:
   - Subscription: tu suscripcion.
   - Resource group: crea `rg-modelos-generativos` o usa uno existente.
   - Region: por ejemplo `East US`, o una region disponible para tu suscripcion.
   - Name: un nombre unico, por ejemplo `aifoundry-modelos-img-eastus`.
   - Pricing tier: `S0` o el tier permitido por tu cuenta.
4. Revisa y crea el recurso.
5. Abre el recurso creado y entra a `Keys and Endpoint`.
6. Copia `Endpoint` en `AZURE_OPENAI_ENDPOINT`.
7. Copia `KEY 1` en `AZURE_OPENAI_API_KEY`.
8. Abre Azure AI Foundry.
9. En el catalogo de modelos, busca y despliega `MAI-Image-2.5`.
10. Usa como nombre de deployment `mai-image-2-5`.
11. Guarda estos valores en `backend\.env`:

```env
AZURE_OPENAI_ENDPOINT=https://<tu-recurso>.cognitiveservices.azure.com
AZURE_OPENAI_API_KEY=<tu-key>
AZURE_OPENAI_DEPLOYMENT_NAME=mai-image-2-5
AZURE_OPENAI_MODEL_NAME=MAI-Image-2.5
IMAGE_PROVIDER=mai
AZURE_OPENAI_API_VERSION=2026-06-02
```

12. Ejecuta `.\start.ps1` y abre http://localhost:8502.

Notas:

- Para deployments MAI, la app normaliza internamente el endpoint de `.cognitiveservices.azure.com` a `.services.ai.azure.com`.
- Necesitas permisos de Azure RBAC para crear recursos y deployments, por ejemplo `Owner`, `Contributor` o permisos equivalentes.
- Si usas otro deployment compatible con Azure OpenAI Images, cambia `IMAGE_PROVIDER=azure-openai`.

## Eliminar recursos

Borrar todo el resource group:

```powershell
az group delete `
  --name rg-modelos-generativos `
  --yes `
  --no-wait
```

Si el nombre queda en soft-delete y quieres purgarlo:

```powershell
az cognitiveservices account purge `
  --location eastus `
  --resource-group rg-modelos-generativos `
  --name aifoundry-modelos-img-eastus
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
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8502 -State Listen).OwningProcess
```

## Referencia

Para deployments MAI, la app usa el endpoint:

```text
/mai/v1/images/generations
```

Para deployments Azure OpenAI Images, la app usa:

```text
/openai/deployments/<deployment>/images/generations
```
