param(
  [string]$ResourceGroup = "rg-content-understanding",
  [string]$Location = "eastus",
  [string]$AccountName = "",
  [string]$StorageAccountName = "",
  [string]$StorageContainer = "content-understanding-inputs",
  [string]$GptDeploymentName = "gpt-4-1",
  [string]$GptModelName = "gpt-4.1",
  [string]$GptModelVersion = "2025-04-14",
  [string]$MiniDeploymentName = "gpt-4-1-mini",
  [string]$MiniModelName = "gpt-4.1-mini",
  [string]$MiniModelVersion = "2025-04-14",
  [string]$EmbeddingDeploymentName = "text-embedding-3-large",
  [string]$EmbeddingModelName = "text-embedding-3-large",
  [string]$EmbeddingModelVersion = "1",
  [string]$SkuName = "GlobalStandard",
  [string]$MiniSkuName = "Standard",
  [string]$EmbeddingSkuName = "Standard",
  [int]$SkuCapacity = 1,
  [switch]$SkipModelDefaults
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $root "backend\.env"

function Invoke-AzCli {
  $errFile = [System.IO.Path]::GetTempFileName()
  $previousErrorActionPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = "Continue"
    $output = & az @args 2> $errFile
    $exitCode = $LASTEXITCODE
    $errorText = Get-Content -Raw $errFile -ErrorAction SilentlyContinue

    if ($exitCode -ne 0) {
      throw "Azure CLI fallo ejecutando: az $($args -join ' ')`n$errorText`n$output"
    }

    if ($errorText -and $errorText.Trim().StartsWith("WARNING:")) {
      Write-Host $errorText.Trim() -ForegroundColor DarkYellow
    }

    return $output
  } finally {
    $ErrorActionPreference = $previousErrorActionPreference
    Remove-Item $errFile -ErrorAction SilentlyContinue
  }
}

function Get-ContentUnderstandingEndpoint {
  param([string]$Endpoint)
  return $Endpoint.TrimEnd("/").Replace(".cognitiveservices.azure.com", ".services.ai.azure.com")
}

function Invoke-ContentUnderstandingPatch {
  param([string]$Uri, [hashtable]$Headers, [string]$Body)
  try {
    Invoke-RestMethod -Method Patch -Uri $Uri -Headers $Headers -Body $Body | Out-Null
  } catch {
    $message = $_.Exception.Message
    $response = $_.Exception.Response
    if ($response -and $response.GetResponseStream()) {
      $reader = [System.IO.StreamReader]::new($response.GetResponseStream())
      $bodyText = $reader.ReadToEnd()
      if ($bodyText) {
        $message = "$message`nAzure response body:`n$bodyText"
      }
    }
    throw $message
  }
}

function Wait-DeploymentSucceeded {
  param(
    [string]$DeploymentName,
    [int]$MaxAttempts = 30,
    [int]$DelaySeconds = 10
  )

  for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    $state = Invoke-AzCli cognitiveservices account deployment show `
      --resource-group $ResourceGroup `
      --name $AccountName `
      --deployment-name $DeploymentName `
      --query properties.provisioningState `
      -o tsv

    if ($state -eq "Succeeded") {
      Write-Host "Deployment listo: $DeploymentName" -ForegroundColor Green
      return
    }

    if ($state -eq "Failed") {
      throw "El deployment '$DeploymentName' fallo al aprovisionarse."
    }

    Write-Host "Esperando deployment $DeploymentName. Estado actual: $state ($attempt/$MaxAttempts)" -ForegroundColor Yellow
    Start-Sleep -Seconds $DelaySeconds
  }

  throw "Timeout esperando que el deployment '$DeploymentName' llegue a Succeeded."
}

function Get-DeploymentNameIfExists {
  param([string]$DeploymentName)
  return Invoke-AzCli cognitiveservices account deployment list `
    --resource-group $ResourceGroup `
    --name $AccountName `
    --query "[?name=='$DeploymentName'].name | [0]" `
    -o tsv
}

function Ensure-Deployment {
  param(
    [string]$DeploymentName,
    [string]$ModelName,
    [string]$ModelVersion,
    [string]$SkuName
  )

  $existing = Get-DeploymentNameIfExists -DeploymentName $DeploymentName
  if ($existing) {
    Write-Host "Usando deployment existente: $DeploymentName" -ForegroundColor Yellow
    return
  }

  Write-Host "Creando deployment: $DeploymentName ($ModelName $ModelVersion, SKU $SkuName)" -ForegroundColor Cyan
  try {
    Invoke-AzCli cognitiveservices account deployment create `
      --resource-group $ResourceGroup `
      --name $AccountName `
      --deployment-name $DeploymentName `
      --model-name $ModelName `
      --model-version $ModelVersion `
      --model-format OpenAI `
      --sku-name $SkuName `
      --sku-capacity $SkuCapacity 1>$null
  } catch {
    $message = $_.Exception.Message
    if ($message -notmatch "Gateway Timeout|timeout|temporar|timed out") {
      throw
    }

    Write-Host "Azure devolvio timeout creando $DeploymentName. Verificando si la operacion continuo en segundo plano..." -ForegroundColor Yellow
    for ($attempt = 1; $attempt -le 18; $attempt++) {
      Start-Sleep -Seconds 10
      $existingAfterTimeout = Get-DeploymentNameIfExists -DeploymentName $DeploymentName
      if ($existingAfterTimeout) {
        Write-Host "Deployment detectado despues del timeout: $DeploymentName" -ForegroundColor Green
        return
      }
      Write-Host "Aun no aparece $DeploymentName ($attempt/18)" -ForegroundColor Yellow
    }

    Write-Host "No aparecio $DeploymentName despues del timeout. Reintentando una vez..." -ForegroundColor Yellow
    Invoke-AzCli cognitiveservices account deployment create `
      --resource-group $ResourceGroup `
      --name $AccountName `
      --deployment-name $DeploymentName `
      --model-name $ModelName `
      --model-version $ModelVersion `
      --model-format OpenAI `
      --sku-name $SkuName `
      --sku-capacity $SkuCapacity 1>$null
  }
}

function Assert-DeploymentExists {
  param([string]$DeploymentName)
  $existing = Get-DeploymentNameIfExists -DeploymentName $DeploymentName
  if (-not $existing) {
    Write-Host "Deployments actuales:" -ForegroundColor Yellow
    Invoke-AzCli cognitiveservices account deployment list `
      --resource-group $ResourceGroup `
      --name $AccountName `
      --query "[].{name:name, model:properties.model.name, version:properties.model.version, state:properties.provisioningState, sku:sku.name}" `
      -o table
    throw "Falta el deployment requerido '$DeploymentName'. No se pueden configurar defaults."
  }
}

function New-Suffix {
  return (Get-Random -Minimum 100000 -Maximum 999999).ToString()
}

if (-not $AccountName) {
  $AccountName = "cu-foundry-$(New-Suffix)"
}
if (-not $StorageAccountName) {
  $StorageAccountName = "stcu$(New-Suffix)"
}
$AccountName = $AccountName.ToLower()
$StorageAccountName = $StorageAccountName.ToLower()

Write-Host "Validando sesion de Azure CLI..." -ForegroundColor Cyan
Invoke-AzCli account show 1>$null

Write-Host "Creando resource group: $ResourceGroup ($Location)" -ForegroundColor Cyan
Invoke-AzCli group create --name $ResourceGroup --location $Location 1>$null

$existingAccount = Invoke-AzCli cognitiveservices account list `
  --resource-group $ResourceGroup `
  --query "[?name=='$AccountName'].name | [0]" `
  -o tsv

if ($existingAccount) {
  Write-Host "Usando Microsoft Foundry / Azure AI Services existente: $AccountName" -ForegroundColor Yellow
} else {
  Write-Host "Creando Microsoft Foundry / Azure AI Services resource: $AccountName" -ForegroundColor Cyan
  Invoke-AzCli cognitiveservices account create `
    --name $AccountName `
    --resource-group $ResourceGroup `
    --location $Location `
    --kind AIServices `
    --sku S0 `
    --custom-domain $AccountName `
    --yes 1>$null
}

$endpoint = Invoke-AzCli cognitiveservices account show --name $AccountName --resource-group $ResourceGroup --query properties.endpoint -o tsv
$contentUnderstandingEndpoint = Get-ContentUnderstandingEndpoint $endpoint
$key = Invoke-AzCli cognitiveservices account keys list --name $AccountName --resource-group $ResourceGroup --query key1 -o tsv

$existingStorage = Invoke-AzCli storage account list `
  --resource-group $ResourceGroup `
  --query "[?name=='$StorageAccountName'].name | [0]" `
  -o tsv

if ($existingStorage) {
  Write-Host "Usando Storage Account existente: $StorageAccountName" -ForegroundColor Yellow
} else {
  Write-Host "Creando Storage Account para archivos de entrada: $StorageAccountName" -ForegroundColor Cyan
  Invoke-AzCli storage account create `
    --name $StorageAccountName `
    --resource-group $ResourceGroup `
    --location $Location `
    --sku Standard_LRS `
    --kind StorageV2 `
    --allow-blob-public-access false 1>$null
}

$storageConnectionString = Invoke-AzCli storage account show-connection-string `
  --name $StorageAccountName `
  --resource-group $ResourceGroup `
  --query connectionString `
  -o tsv

Write-Host "Creando container privado: $StorageContainer" -ForegroundColor Cyan
Invoke-AzCli storage container create `
  --name $StorageContainer `
  --connection-string $storageConnectionString 1>$null

if (-not $SkipModelDefaults) {
  Write-Host "Creando deployments base para Content Understanding..." -ForegroundColor Cyan
  Ensure-Deployment -DeploymentName $GptDeploymentName -ModelName $GptModelName -ModelVersion $GptModelVersion -SkuName $SkuName
  Ensure-Deployment -DeploymentName $MiniDeploymentName -ModelName $MiniModelName -ModelVersion $MiniModelVersion -SkuName $MiniSkuName
  Ensure-Deployment -DeploymentName $EmbeddingDeploymentName -ModelName $EmbeddingModelName -ModelVersion $EmbeddingModelVersion -SkuName $EmbeddingSkuName

  Assert-DeploymentExists -DeploymentName $GptDeploymentName
  Assert-DeploymentExists -DeploymentName $MiniDeploymentName
  Assert-DeploymentExists -DeploymentName $EmbeddingDeploymentName

  Write-Host "Configurando defaults de Content Understanding..." -ForegroundColor Cyan
  $body = @{
    modelDeployments = @{
      $GptModelName = $GptDeploymentName
      "gpt-4.1-mini" = $MiniDeploymentName
      "text-embedding-3-large" = $EmbeddingDeploymentName
      "prebuilt-analyzer-completion" = $GptDeploymentName
      "prebuilt-analyzer-completion-mini" = $MiniDeploymentName
      "prebuilt-analyzer-embedding" = $EmbeddingDeploymentName
    }
  } | ConvertTo-Json -Depth 5

  Write-Host "Esperando a que los deployments queden disponibles..." -ForegroundColor Cyan
  Wait-DeploymentSucceeded -DeploymentName $GptDeploymentName
  Wait-DeploymentSucceeded -DeploymentName $MiniDeploymentName
  Wait-DeploymentSucceeded -DeploymentName $EmbeddingDeploymentName

  Invoke-ContentUnderstandingPatch `
    -Uri "$contentUnderstandingEndpoint/contentunderstanding/defaults?api-version=2025-11-01" `
    -Headers @{ "Ocp-Apim-Subscription-Key" = $key; "Content-Type" = "application/json" } `
    -Body $body
}

@"
CONTENT_UNDERSTANDING_ENDPOINT=$contentUnderstandingEndpoint
CONTENT_UNDERSTANDING_KEY=$key
CONTENT_UNDERSTANDING_API_VERSION=2025-11-01
CONTENT_UNDERSTANDING_INPUT_MODE=blob
AZURE_STORAGE_CONNECTION_STRING=$storageConnectionString
AZURE_STORAGE_CONTAINER=$StorageContainer
PORT=3060
ALLOWED_ORIGIN=http://localhost:5180
"@ | Set-Content -Path $envPath -Encoding UTF8

Write-Host ""
Write-Host "Azure Content Understanding listo. backend/.env actualizado." -ForegroundColor Green
Write-Host "Resource group    : $ResourceGroup"
Write-Host "Cuenta Foundry    : $AccountName"
Write-Host "Endpoint          : $contentUnderstandingEndpoint"
Write-Host "Storage account   : $StorageAccountName"
Write-Host "Storage container : $StorageContainer"
Write-Host "API version       : 2025-11-01"
if (-not $SkipModelDefaults) {
  Write-Host "Deployments       : $GptDeploymentName, $MiniDeploymentName, $EmbeddingDeploymentName"
  Write-Host "Mini SKU          : $MiniSkuName"
  Write-Host "Embedding SKU     : $EmbeddingSkuName"
}
