param(
  [string]$ResourceGroup = "rg-app-vision",
  [string]$AccountName = "vision-app-demo",
  [string]$Location = "eastus",
  [switch]$Purge,
  [switch]$NoWait
)

$ErrorActionPreference = "Stop"

if ($NoWait) {
  az group delete --name $ResourceGroup --yes --no-wait
  Write-Host "Eliminacion iniciada para $ResourceGroup." -ForegroundColor Yellow
} else {
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