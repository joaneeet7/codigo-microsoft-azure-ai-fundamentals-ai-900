# App Analisis Texto

Aplicacion ligera para analizar texto con Azure AI Language. Incluye un backend Python/FastAPI y un frontend React/Vite.

## Funciones

- Analisis de sentimiento
- Extraccion de frases clave
- Reconocimiento de entidades
- Deteccion de idioma
- Fallback local para demos sin credenciales

## Requisitos

- Node.js 20 o superior
- Python 3.9 o superior
- Recurso de Azure AI Language, opcional para demo local

## Configuracion

Instala dependencias (igual en todos los sistemas):

```bash
npm install
npm install --prefix backend
npm install --prefix frontend
```

Crea `backend/.env` desde el ejemplo.

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

Edita `backend/.env` si usaras Azure:

```env
AZURE_LANGUAGE_ENDPOINT=https://<resource-name>.cognitiveservices.azure.com/
AZURE_LANGUAGE_KEY=<key>
PORT=3010
ALLOWED_ORIGIN=http://localhost:5174
```

Si dejas esas variables vacias, el backend usa un analisis local aproximado.

## Ejecutar

```bash
npm run dev
```

- Frontend: http://localhost:5174
- Backend: http://localhost:3010