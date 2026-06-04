# App Analisis Texto

Aplicacion ligera para analizar texto con Azure AI Language. Incluye un backend Express y un frontend React/Vite.

## Funciones

- Analisis de sentimiento
- Extraccion de frases clave
- Reconocimiento de entidades
- Deteccion de idioma
- Fallback local para demos sin credenciales

## Requisitos

- Node.js 20 o superior
- Recurso de Azure AI Language, opcional para demo local

## Configuracion

```bash
npm install
npm install --prefix backend
npm install --prefix frontend
copy backend\.env.example backend\.env
```

Edita `backend/.env` si usaras Azure:

```env
AZURE_LANGUAGE_ENDPOINT=https://<resource-name>.cognitiveservices.azure.com/
AZURE_LANGUAGE_KEY=<key>
PORT=3010
ALLOWED_ORIGIN=http://localhost:5174
```

Si dejas esas variables vacias, el backend usa un analisis local aproximado.

## Ejecutar

Backend:

```bash
npm run dev:backend
```

Frontend:

```bash
npm run dev:frontend
```

O ambos:

```bash
npm run dev
```

- Frontend: http://localhost:5174
- Backend: http://localhost:3010

## Crear recurso de Azure AI Language por CLI

```bash
az login
az group create --name rg-analisis-texto --location eastus2
az cognitiveservices account create --kind TextAnalytics --resource-group rg-analisis-texto --name <nombre-unico> --sku F0 --location eastus2
az cognitiveservices account show --name <nombre-unico> --resource-group rg-analisis-texto --query properties.endpoint -o tsv
az cognitiveservices account keys list --name <nombre-unico> --resource-group rg-analisis-texto --query key1 -o tsv
```

## Infraestructura y arranque automatizado

El proyecto incluye Terraform para crear Azure AI Language y un script interactivo para levantar el entorno.

Script principal:

```bash
bash scripts/start-environment.sh
```

El script pregunta:

```txt
1) Crear/actualizar Azure con Terraform y levantar backend + frontend
2) Solo levantar backend + frontend
```

Si eliges la opcion 1, el script:

- Valida `az`, `terraform` y `node`
- Ejecuta `az login` si hace falta
- Obtiene automaticamente tu `subscription_id`
- Actualiza `infra/terraform/terraform.tfvars`
- Ejecuta `terraform init`, `terraform plan` y `terraform apply`
- Imprime el bloque para `backend/.env`
- Pregunta si quieres escribirlo automaticamente en `backend/.env`
- Levanta primero el backend y despues el frontend

Terraform manual:

```bash
cd infra/terraform
copy terraform.tfvars.example terraform.tfvars
terraform init -upgrade
terraform plan -out main.tfplan
terraform apply main.tfplan
terraform output -raw backend_env
```

Para detener los servidores, presiona `Ctrl + C` en la terminal donde corre el script.

## Backend Python

El backend ahora usa Python con FastAPI. El frontend no cambia porque se conserva el mismo contrato HTTP:

```txt
POST /api/analyze
GET  /health
```

Instalar dependencias del backend:

```bash
cd backend
python -m pip install -r requirements.txt
```

Ejecutar backend:

```bash
cd ..
npm.cmd run dev:backend
```

El backend corre en:

```txt
http://localhost:3010
```
