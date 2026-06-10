#Listar modelos
az cognitiveservices model list `
  --location eastus `
  --query "[?contains(model.name, 'dall-e') || contains(model.name, 'image')]" `
  --output table
  
  
  
$endpoint = az cognitiveservices account show `
  --name aifoundry-modelos-img-eastus `
  --resource-group rg-modelos-generativos `
  --query properties.endpoint `
  -o tsv
  
  
$key = az cognitiveservices account keys list `
  --name aifoundry-modelos-img-eastus `
  --resource-group rg-modelos-generativos `
  --query key1 `
  -o tsv
  
# Purgar
az group delete `
  --name rg-modelos-generativos `
  --yes `
  --no-wait