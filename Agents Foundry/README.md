# Foundry Agents Chat Demo

Aplicacion cliente ligera para un agente de Microsoft Foundry. Lista los agentes desplegados en tu proyecto, te deja elegir uno y chatear con el. Backend Express y frontend React.

## Requisitos

- Node.js 20 o superior
- Azure CLI
- Un proyecto de Microsoft Foundry
- Al menos un agente desplegado en Foundry

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

4. Edita `backend/.env`:

```env
PROJECT_ENDPOINT=https://<resource-name>.services.ai.azure.com/api/projects/<project-name>
PORT=3001
ALLOWED_ORIGIN=http://localhost:5173
```

## Ejecutar

```bash
npm run dev
```

- Frontend: http://localhost:5173
- Backend: http://localhost:3001