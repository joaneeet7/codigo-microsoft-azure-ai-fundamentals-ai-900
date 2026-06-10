param(
  [string]$ResourceGroup = "rg-visual-input",
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


# az cognitiveservices account purge `
#   --location eastus `
#   --resource-group rg-visual-input `
#   --name aoai-visual-input-demo
