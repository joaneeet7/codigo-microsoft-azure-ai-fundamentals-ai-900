# App Speeach

Demo ligera usando Azure Speech en Foundry Tools con backend Python/FastAPI y frontend React.


## Funciones

- Text to speech: convierte texto a audio MP3 usando Azure Speech.
- Speech to text: transcribe archivos WAV cortos.
- Frontend profesional con panel de voz, reproductor y resultados.

## Requisitos

- Node.js 20+
- Python 3.10+
- Recurso de Azure AI Speech / Azure AI Services Speech

## Configuracion

Instala dependencias.

En macOS o Linux:

```bash
npm install
npm install --prefix frontend
cd backend
python3 -m pip install -r requirements.txt
cd ..
```

En Windows (usa `py` o `python` segun tu instalacion):

```cmd
npm install
npm install --prefix frontend
cd backend
py -m pip install -r requirements.txt
cd ..
```

Crea `backend/.env` desde el ejemplo:

En macOS o Linux:

```bash
cp backend/.env.example backend/.env
```

En Windows (CMD):

```cmd
copy backend\.env.example backend\.env
```

En Windows (PowerShell):

```powershell
Copy-Item backend\.env.example backend\.env
```

Configura:

```env
SPEECH_KEY=<tu-key>
SPEECH_REGION=<region>
SPEECH_VOICE_NAME=es-MX-DaliaNeural
SPEECH_RECOGNITION_LANGUAGE=es-MX
PORT=3022
ALLOWED_ORIGIN=http://localhost:5175
```

## Ejecutar


```bash
npm run dev
```

- Frontend: http://localhost:5175
- Backend: http://localhost:3022
