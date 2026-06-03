# Foundry Chat Demo

Aplicacion ligera de chat usando Microsoft Foundry SDK, con backend Express y frontend React.

## Requisitos

- Node.js 20 o superior
- Azure CLI
- Un proyecto de Microsoft Foundry
- Un modelo desplegado en Foundry

## Configuracion

1. Inicia sesion en Azure:

```bash
az login
```

2. Instala dependencias:

```bash
npm install
npm install --prefix backend
npm install --prefix frontend
```

3. Copia las variables de entorno:

```bash
copy backend\.env.example backend\.env
```

4. Edita `backend/.env`:

```env
PROJECT_ENDPOINT=https://<resource-name>.ai.azure.com/api/projects/<project-name>
MODEL_DEPLOYMENT_NAME=gpt-5-mini
PORT=3001
```

## Ejecutar

```bash
npm run dev
```

- Frontend: http://localhost:5173
- Backend: http://localhost:3001

## Estructura

```txt
backend/
  src/
    foundryClient.ts
    index.ts
    routes/chat.ts
frontend/
  src/
    App.tsx
    components/Chat.tsx
```

## Notas

- El backend usa `DefaultAzureCredential`, por eso `az login` debe estar activo.
- El frontend no conoce secretos ni endpoints de Foundry.
- La conversacion se mantiene en memoria en el navegador durante la sesion.

## Infraestructura con Terraform

La carpeta `infra/terraform` crea el recurso de Microsoft Foundry, un proyecto y un deployment de modelo.

### Opcion automatica

Este script detecta tu `subscription_id`, actualiza `terraform.tfvars`, ejecuta Terraform, escribe `backend/.env`, levanta el backend, espera a que `/health` responda y luego levanta el frontend:

```bash
bash scripts/deploy-foundry-and-run.sh
```

Si estas en Windows, ejecutalo desde Git Bash, WSL o una terminal compatible con Bash.

### Opcion manual

```bash
cd infra/terraform
copy terraform.tfvars.example terraform.tfvars
```

Edita `terraform.tfvars` con tu `subscription_id` y region. Luego ejecuta:

```bash
az login
terraform init -upgrade
terraform plan -out main.tfplan
terraform apply main.tfplan
terraform output backend_env
```

Copia el output `backend_env` en `backend/.env`.
