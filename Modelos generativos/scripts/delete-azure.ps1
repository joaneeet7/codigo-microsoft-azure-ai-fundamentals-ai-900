param(
  [string]$ResourceGroup = "rg-modelos-generativos",
  [string]$AccountName = "aifoundry-modelos-img-eastus",
  [string]$Location = "eastus",
  [switch]$Purge,
  [switch]$NoWait
)

$ErrorActionPreference = "Stop"

Write-Host "Recursos actuales en ${ResourceGroup}:" -ForegroundColor Cyan
az resource list `
  --resource-group $ResourceGroup `
  --query "[].{name:name,type:type,location:location}" `
  -o table

if ($NoWait) {
  Write-Host "Eliminando resource group en segundo plano: $ResourceGroup" -ForegroundColor Yellow
  az group delete --name $ResourceGroup --yes --no-wait
} else {
  Write-Host "Eliminando resource group: $ResourceGroup" -ForegroundColor Yellow
  az group delete --name $ResourceGroup --yes
  Write-Host "Resource group eliminado: $ResourceGroup" -ForegroundColor Green
}

if ($Purge) {
  Write-Host "Intentando purgar cuenta soft-deleted: $AccountName" -ForegroundColor Yellow
  az cognitiveservices account purge `
    --location $Location `
    --resource-group $ResourceGroup `
    --name $AccountName
}

Write-Host ""
Write-Host "Comandos utiles si necesitas revisar soft-delete:" -ForegroundColor Cyan
Write-Host "az cognitiveservices account list-deleted -o table"
Write-Host "az cognitiveservices account purge --location $Location --resource-group $ResourceGroup --name $AccountName"