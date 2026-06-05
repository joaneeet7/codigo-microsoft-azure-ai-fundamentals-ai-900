# App Speeach

Demo ligera usando Azure Speech en Foundry Tools con backend Python/FastAPI y frontend React.

> Nota: el nombre de la carpeta se mantiene como `app-speeach`, tal como fue solicitado.

## Funciones

- Text to speech: convierte texto a audio MP3 usando Azure Speech.
- Speech to text: transcribe archivos WAV cortos.
- Frontend profesional con panel de voz, reproductor y resultados.

## Requisitos

- Node.js 20+
- Python 3.10+
- Recurso de Azure AI Speech / Azure AI Services Speech

## Configuracion

Instala dependencias:

```bash
npm install
npm install --prefix frontend
cd backend
py -m pip install -r requirements.txt
cd ..
```

Crea `backend/.env` desde el ejemplo:

```bash
copy backend\.env.example backend\.env
```

Configura:

```env
SPEECH_KEY=<tu-key>
SPEECH_REGION=eastus2
SPEECH_VOICE_NAME=es-MX-DaliaNeural
SPEECH_RECOGNITION_LANGUAGE=es-MX
PORT=3022
ALLOWED_ORIGIN=http://localhost:5175
```

## Ejecutar

Backend:

```bash
npm.cmd run dev:backend
```

Frontend:

```bash
npm.cmd run dev:frontend
```

O ambos:

```bash
npm.cmd run dev
```

- Frontend: http://localhost:5175
- Backend: http://localhost:3022

## Script

```bash
bash scripts/start-environment.sh
```

El script instala dependencias si hacen falta, levanta primero backend y despues frontend.

## Azure con Terraform

La carpeta `infra/terraform` crea un recurso Azure Speech Services y genera las variables necesarias para `backend/.env`.

Script interactivo:

```bash
bash scripts/start-environment.sh
```

Opciones:

```txt
1) Despliegue en Terraform + backend + frontend
2) Solo backend + frontend
3) Solo Terraform
```

Terraform manual:

```bash
cd infra/terraform
copy terraform.tfvars.example terraform.tfvars
terraform init -upgrade
terraform plan -out main.tfplan
terraform apply main.tfplan
terraform output -raw backend_env
```
