# Modelos Generativos

Demo ligera para crear nuevas salidas visuales mediante modelos generativos en Azure AI Foundry / Microsoft Foundry.

## Stack

- Backend: Python + FastAPI
- Frontend: React + Vite + TypeScript
- Servicio esperado: Azure AI Foundry con un deployment de imagen, por ejemplo `MAI-Image-2.5`

## Funciones

- Generacion de imagen desde prompt
- Seleccion de tamano y calidad
- Vista previa en galeria
- Modo demo local si no hay credenciales configuradas
- Scripts de Azure CLI para crear y eliminar recursos

## Instalar dependencias

```powershell
cd C:\Users\li-ve\Documents\Codex\2026-06-02\modelos-generativos
npm.cmd install
npm.cmd install --prefix frontend
cd backend
py -m pip install -r requirements.txt
cd ..
```

## Crear Azure con Azure CLI

Inicia sesion y selecciona suscripcion:

```powershell
az login
az account set --subscription "<SUBSCRIPTION_ID>"
```

Ejecuta el script:

```powershell
cd C:\Users\li-ve\Documents\Codex\2026-06-02\modelos-generativos
.\scripts\create-azure.ps1
```

El script crea:

- Resource group: `rg-modelos-generativos`
- Recurso Azure AI Services: `aifoundry-modelos-img-eastus`
- Deployment: `mai-image-2-5`
- Modelo: `MAI-Image-2.5`
- Archivo: `backend/.env`

Puedes cambiar valores:

```powershell
.\scripts\create-azure.ps1 `
  -ResourceGroup rg-modelos-generativos `
  -Location eastus `
  -AccountName aifoundry-modelos-img-eastus `
  -DeploymentName mai-image-2-5 `
  -ModelName "MAI-Image-2.5" `
  -ModelVersion "2026-06-02" `
  -SkuName GlobalStandard `
  -SkuCapacity 1
```

`setup-azure.ps1` se conserva como alias seguro y llama internamente a `create-azure.ps1`.

## Configuracion manual

Si no usas el script, crea:

```powershell
copy backend\.env.example backend\.env
```

Ejemplo `.env`:

```env
AZURE_OPENAI_ENDPOINT=https://<tu-recurso>.cognitiveservices.azure.com
AZURE_OPENAI_API_KEY=<tu-key>
AZURE_OPENAI_DEPLOYMENT_NAME=mai-image-2-5
AZURE_OPENAI_MODEL_NAME=MAI-Image-2.5
IMAGE_PROVIDER=mai
AZURE_OPENAI_API_VERSION=2026-06-02
PORT=3030
ALLOWED_ORIGIN=http://localhost:5176
```

Si dejas endpoint/key vacios, el backend usa modo demo local y devuelve una imagen SVG generada por codigo.

## Eliminar Azure con Azure CLI

Borrar el resource group completo:

```powershell
.\scripts\delete-azure.ps1 -NoWait
```

En macOS/Linux:

```bash
./scripts/delete-azure.sh --no-wait
```

Borrar y luego intentar purgar el recurso soft-deleted:

```powershell
.\scripts\delete-azure.ps1 -NoWait -Purge
```

En macOS/Linux:

```bash
./scripts/delete-azure.sh --no-wait --purge
```

Comandos manuales equivalentes:

```powershell
az group delete `
  --name rg-modelos-generativos `
  --yes `
  --no-wait
```

Si el nombre queda reservado por soft-delete:

```powershell
az cognitiveservices account list-deleted -o table
```

```powershell
az cognitiveservices account purge `
  --location eastus `
  --resource-group rg-modelos-generativos `
  --name aifoundry-modelos-img-eastus
```

## Ejecutar manualmente

Backend:

```powershell
cd C:\Users\li-ve\Documents\Codex\2026-06-02\modelos-generativos
npm.cmd run dev:backend
```

Frontend, en otra terminal:

```powershell
cd C:\Users\li-ve\Documents\Codex\2026-06-02\modelos-generativos
npm.cmd run dev:frontend
```

URLs:

- Frontend: http://localhost:5176
- Backend: http://localhost:3030

## Referencia

Microsoft Learn documenta image generation en Foundry Models usando modelos de imagen como `MAI-Image-2.5` y endpoints `/mai/v1/images/generations`.