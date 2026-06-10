param(
  [string]$ResourceGroup = "rg-modelos-generativos",
  [string]$Location = "eastus",
  [string]$AccountName = "aifoundry-modelos-img-eastus",
  [string]$DeploymentName = "mai-image-2-5",
  [string]$ModelName = "MAI-Image-2.5",
  [string]$ModelVersion = "2026-06-02",
  [string]$SkuName = "GlobalStandard",
  [int]$SkuCapacity = 1
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot "backend\.env"

Write-Host "Validando sesion de Azure CLI..." -ForegroundColor Cyan
az account show 1>$null

Write-Host "Creando resource group: $ResourceGroup ($Location)" -ForegroundColor Cyan
az group create `
  --name $ResourceGroup `
  --location $Location 1>$null

Write-Host "Creando recurso Azure AI Foundry / AI Services: $AccountName" -ForegroundColor Cyan
az cognitiveservices account create `
  --name $AccountName `
  --resource-group $ResourceGroup `
  --location $Location `
  --kind AIServices `
  --sku S0 `
  --custom-domain $AccountName `
  --yes 1>$null

Write-Host "Creando deployment de imagen: $DeploymentName -> $ModelName ($ModelVersion)" -ForegroundColor Cyan
az cognitiveservices account deployment create `
  --resource-group $ResourceGroup `
  --name $AccountName `
  --deployment-name $DeploymentName `
  --model-name $ModelName `
  --model-version $ModelVersion `
  --model-format Microsoft `
  --sku-name $SkuName `
  --sku-capacity $SkuCapacity 1>$null

$endpoint = az cognitiveservices account show `
  --name $AccountName `
  --resource-group $ResourceGroup `
  --query properties.endpoint `
  -o tsv

$key = az cognitiveservices account keys list `
  --name $AccountName `
  --resource-group $ResourceGroup `
  --query key1 `
  -o tsv

$envContent = @"
AZURE_OPENAI_ENDPOINT=$endpoint
AZURE_OPENAI_API_KEY=$key
AZURE_OPENAI_DEPLOYMENT_NAME=$DeploymentName
AZURE_OPENAI_MODEL_NAME=$ModelName
IMAGE_PROVIDER=mai
AZURE_OPENAI_API_VERSION=$ModelVersion
PORT=3030
ALLOWED_ORIGIN=http://localhost:5176
"@

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($envPath, $envContent, $utf8NoBom)

Write-Host ""
Write-Host "Azure listo. Archivo backend/.env actualizado." -ForegroundColor Green
Write-Host "Resource group : $ResourceGroup"
Write-Host "Cuenta         : $AccountName"
Write-Host "Endpoint       : $endpoint"
Write-Host "Deployment     : $DeploymentName"
Write-Host "Modelo         : $ModelName"
Write-Host "Provider       : mai"
Write-Host ""
Write-Host "Para probar:"
Write-Host "  npm.cmd run dev:backend"
Write-Host "  npm.cmd run dev:frontend"