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
cd "D:\Repository\Blockstellart\codigo-microsoft-azure-ai-fundamentals-ai-900\App Computer Vision"
.\start.ps1
```

En macOS/Linux:

```bash
cd "/ruta/a/codigo-microsoft-azure-ai-fundamentals-ai-900/App Computer Vision"
chmod +x start.sh
./start.sh
```

El script crea `.venv`, instala `requirements.txt` y levanta Streamlit.

URL local:

- http://localhost:8501

Para omitir la instalacion de dependencias cuando ya existe el entorno:

```powershell
.\start.ps1 -SkipInstall
```

En macOS/Linux:

```bash
./start.sh --skip-install
```

## Configurar credenciales

Copia el archivo de ejemplo y edita los valores:

```powershell
copy backend\.env.example backend\.env
notepad backend\.env
```

Variables:

```env
VISION_ENDPOINT=https://<tu-recurso>.cognitiveservices.azure.com
VISION_KEY=<tu-key>
VISION_API_VERSION=2024-02-01
```

Si `VISION_ENDPOINT` y `VISION_KEY` estan vacios, la aplicacion arranca en modo demo local.

## Crear Azure con Azure CLI

```powershell
az login
az account set --subscription "<SUBSCRIPTION_ID>"
cd "D:\Repository\Blockstellart\codigo-microsoft-azure-ai-fundamentals-ai-900\App Computer Vision"
.\scripts\create-azure.ps1
```

El script crea el resource group, crea el recurso Computer Vision, obtiene endpoint/key y actualiza `backend\.env`.

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

## Crear servicios desde el portal de Azure

Pasos para crear el recurso sin CLI:

1. Entra a [Azure Portal](https://portal.azure.com).
2. Busca `Computer Vision` o `Azure AI services` y selecciona crear un recurso.
3. Completa los campos principales:
   - Subscription: tu suscripcion.
   - Resource group: crea `rg-app-vision` o usa uno existente.
   - Region: por ejemplo `East US`, o una region disponible para tu suscripcion.
   - Name: un nombre unico, por ejemplo `vision-app-demo`.
   - Pricing tier: `S1` para pruebas con Computer Vision, o el tier permitido por tu cuenta.
4. Revisa y crea el recurso.
5. Abre el recurso creado y entra a `Keys and Endpoint`.
6. Copia `Endpoint` en `VISION_ENDPOINT`.
7. Copia `KEY 1` en `VISION_KEY`.
8. Guarda esos valores en `backend\.env`.
9. Ejecuta `.\start.ps1` y abre http://localhost:8501.

Notas:

- Para prototipos locales puedes dejar networking publico. En ambientes empresariales revisa las opciones de red, identidad y cifrado antes de crear el recurso.
- Necesitas permisos de Azure RBAC para crear recursos, por ejemplo `Owner`, `Contributor` o un rol personalizado con `Microsoft.CognitiveServices/accounts/write`.
- Microsoft documenta la creacion de recursos de Azure AI desde portal y CLI en [Create a Foundry resource](https://learn.microsoft.com/en-us/azure/ai-services/multi-service-resource?pivots=azportal&tabs=windows).

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

## Referencia

Azure AI Vision Image Analysis 4.0 usa el endpoint `computervision/imageanalysis:analyze` con features como `caption`, `denseCaptions`, `tags`, `objects`, `read`, `people` y `smartCrops`.
