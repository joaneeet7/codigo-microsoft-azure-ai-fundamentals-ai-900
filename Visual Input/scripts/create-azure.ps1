param(
  [string]$ResourceGroup = "rg-visual-input",
  [string]$Location = "eastus",
  [string]$AccountName = "aoai-visual-input-demo",
  [string]$DeploymentName = "gpt-4o-mini",
  [string]$ModelName = "gpt-4o-mini",
  [string]$ModelVersion = "2024-07-18",
  [string]$SkuName = "GlobalStandard",
  [int]$SkuCapacity = 1
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
  --kind OpenAI `
  --sku S0 `
  --yes 1>$null

az cognitiveservices account deployment create `
  --resource-group $ResourceGroup `
  --name $AccountName `
  --deployment-name $DeploymentName `
  --model-name $ModelName `
  --model-version $ModelVersion `
  --model-format OpenAI `
  --sku-name $SkuName `
  --sku-capacity $SkuCapacity `
  -o jsonc
if ($LASTEXITCODE -ne 0) {
  throw "Fallo la creacion del deployment '$DeploymentName'. Revisa el error anterior de Azure CLI."
}

$deployment = az cognitiveservices account deployment show `
  --resource-group $ResourceGroup `
  --name $AccountName `
  --deployment-name $DeploymentName `
  -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $deployment) {
  throw "No se pudo confirmar el deployment '$DeploymentName'. Revisa si el modelo '$ModelName' version '$ModelVersion' esta disponible en '$Location'."
}

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
AZURE_OPENAI_ENDPOINT=$endpoint
AZURE_OPENAI_API_KEY=$key
AZURE_OPENAI_DEPLOYMENT_NAME=$DeploymentName
AZURE_OPENAI_API_VERSION=2024-10-21
PORT=3040
ALLOWED_ORIGIN=http://localhost:5178
"@ | Set-Content -Path $envPath -Encoding UTF8

Write-Host "Azure listo. Archivo backend/.env actualizado." -ForegroundColor Green
Write-Host "Resource group: $ResourceGroup"
Write-Host "Cuenta: $AccountName"
Write-Host "Deployment: $DeploymentName"
