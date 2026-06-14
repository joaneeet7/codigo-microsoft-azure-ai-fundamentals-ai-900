param(
  [string]$ResourceGroup = "rg-app-vision",
  [string]$Location = "eastus",
  [string]$AccountName = "vision-app-demo"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $root "backend\.env"

az account show 1>$null

az group create `
  --name $ResourceGroup `
  --location $Location 1>$null

az cognitiveservices account create `
  --name $AccountName `
  --resource-group $ResourceGroup `
  --location $Location `
  --kind ComputerVision `
  --sku S1 `
  --yes 1>$null

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

@"
VISION_ENDPOINT=$endpoint
VISION_KEY=$key
VISION_API_VERSION=2024-02-01
PORT=3050
ALLOWED_ORIGIN=http://localhost:5179
"@ | Set-Content -Path $envPath -Encoding UTF8

Write-Host "Azure AI Vision listo. Archivo backend/.env actualizado." -ForegroundColor Green
Write-Host "Resource group: $ResourceGroup"
Write-Host "Cuenta Vision: $AccountName"