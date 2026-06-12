# App Content Understanding

Demo ligera para extraccion de informacion de documentos y formularios mediante Azure Content Understanding en Foundry Tools.

## Stack

- Backend: Python + FastAPI
- Frontend: React + Vite + TypeScript
- Azure: Microsoft Foundry / Azure AI Services con Content Understanding

## Funciones

- Carga de PDF, imagen o TXT
- Analyzers prebuilt: `prebuilt-invoice`, `prebuilt-documentSearch`, `prebuilt-imageSearch`, `prebuilt-tax.us.w2`, `prebuilt-tax.us.w4`, `prebuilt-tax.us.1099NEC`
- Extraccion de campos, markdown, paginas, tablas y key-values
- Modo demo local sin credenciales
- Scripts PowerShell para crear, completar y eliminar recursos

## Instalar

```powershell
cd C:\Users\li-ve\Documents\Codex\2026-06-02\app-content-understanding
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
cd C:\Users\li-ve\Documents\Codex\2026-06-02\app-content-understanding
.\scripts\create-azure.ps1
```

El script crea:

- Resource group: `rg-content-understanding`
- Recurso Microsoft Foundry / Azure AI Services: `cu-foundry-demo`
- Deployments base: `gpt-4-1`, `gpt-4-1-mini`, `text-embedding-3-large`
- Defaults de Content Understanding
- Storage Account privado para archivos de entrada
- Archivo `backend/.env` con endpoint, key y Storage

Si tu region/suscripcion no soporta esos modelos, puedes crear solo el recurso y configurar defaults manualmente:

```powershell
.\scripts\create-azure.ps1 -SkipModelDefaults
```

Si ya tienes el recurso de Content Understanding creado y solo necesitas corregir el flujo de archivos, crea Storage y actualiza `backend/.env` con:

```powershell
.\scripts\setup-storage.ps1
```

Content Understanding funciona siguiendo el flujo REST oficial: para analyzers prebuilt no necesitas crear una task en Foundry portal. El backend sube el archivo a Blob Storage privado, genera una URL SAS de lectura por 1 hora y envia esa URL al analyzer.

## Eliminar Azure

```powershell
.\scripts\delete-azure.ps1 -NoWait
```

Con purga soft-delete:

```powershell
.\scripts\delete-azure.ps1 -NoWait -Purge
```

## Ejecutar manualmente

Backend:

```powershell
cd C:\Users\li-ve\Documents\Codex\2026-06-02\app-content-understanding
npm.cmd run dev:backend
```

Frontend, en otra terminal:

```powershell
cd C:\Users\li-ve\Documents\Codex\2026-06-02\app-content-understanding
npm.cmd run dev:frontend
```

URLs:

- Frontend: http://localhost:5180
- Backend: http://localhost:3060

## Referencia

Azure Content Understanding analiza contenido con endpoints como `/contentunderstanding/analyzers/{analyzerId}:analyze?api-version=2025-11-01`. La respuesta inicial es asincrona y devuelve `Operation-Location`; luego se consulta el resultado hasta que el estado sea `Succeeded`.
## Diagnostico REST oficial

Para separar problemas de Azure de problemas de la app, ejecuta una prueba directa contra el PDF oficial de Microsoft:

```powershell
.\scripts\test-official-sample.ps1
```

Si esta prueba falla, el problema esta en el recurso/defaults/deployments de Azure. Si esta prueba funciona, el recurso esta bien y el problema esta en el backend o en la subida del archivo.
## Scripts en macOS/Linux

Los scripts PowerShell tienen equivalentes Bash en `scripts/`:

- `create-azure.sh`: crea Azure, Storage, deployments, defaults y `backend/.env`.
- `delete-azure.sh`: elimina el resource group y opcionalmente purga soft-delete.
- `test-official-sample.sh`: prueba REST directa con el PDF oficial de Microsoft.
- `test-blob-input.sh`: sube un archivo local a Blob Storage y prueba REST con SAS.

Dependencias en macOS:

```bash
brew install azure-cli jq
az login
chmod +x scripts/*.sh
```

Crear recursos:

```bash
./scripts/create-azure.sh
```

Eliminar recursos:

```bash
./scripts/delete-azure.sh --no-wait
```

Probar ejemplo oficial:

```bash
./scripts/test-official-sample.sh --analyzer-id prebuilt-invoice
```

Probar con un PDF local via Blob SAS:

```bash
./scripts/test-blob-input.sh --file-path "/ruta/al/invoice.pdf" --analyzer-id prebuilt-invoice
```