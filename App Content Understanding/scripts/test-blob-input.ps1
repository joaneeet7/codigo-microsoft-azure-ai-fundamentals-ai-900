param(
  [string]$AnalyzerId = "prebuilt-documentSearch",
  [string]$FilePath = "",
  [string]$ApiVersion = "2025-11-01",
  [int]$MaxAttempts = 90,
  [int]$DelaySeconds = 2
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $root "backend\.env"

function Read-EnvFile {
  param([string]$Path)
  $values = @{}
  if (Test-Path $Path) {
    Get-Content $Path | ForEach-Object {
      if ($_ -match '^\s*([^#=]+)=(.*)$') {
        $values[$matches[1].Trim()] = $matches[2].Trim()
      }
    }
  }
  return $values
}

function Get-CuEndpoint {
  param([string]$Endpoint)
  return $Endpoint.TrimEnd('/').Replace('.cognitiveservices.azure.com', '.services.ai.azure.com')
}

function Get-ResponseBody {
  param($ErrorRecord)
  $response = $ErrorRecord.Exception.Response
  if ($response -and $response.GetResponseStream()) {
    $reader = [System.IO.StreamReader]::new($response.GetResponseStream())
    return $reader.ReadToEnd()
  }
  return ""
}

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
    return $output
  } finally {
    $ErrorActionPreference = $previousErrorActionPreference
    Remove-Item $errFile -ErrorAction SilentlyContinue
  }
}

$envValues = Read-EnvFile $envPath
$endpoint = $envValues["CONTENT_UNDERSTANDING_ENDPOINT"]
$key = $envValues["CONTENT_UNDERSTANDING_KEY"]
$storageConnectionString = $envValues["AZURE_STORAGE_CONNECTION_STRING"]
$container = $envValues["AZURE_STORAGE_CONTAINER"]

if (-not $endpoint -or -not $key) { throw "Faltan CONTENT_UNDERSTANDING_ENDPOINT o CONTENT_UNDERSTANDING_KEY en backend/.env." }
if (-not $storageConnectionString -or -not $container) { throw "Faltan AZURE_STORAGE_CONNECTION_STRING o AZURE_STORAGE_CONTAINER en backend/.env." }
if (-not $FilePath) { throw "Pasa un archivo local con -FilePath. Ejemplo: .\scripts\test-blob-input.ps1 -FilePath 'C:\ruta\invoice.pdf'" }
if (-not (Test-Path $FilePath)) { throw "No existe el archivo: $FilePath" }

$endpoint = Get-CuEndpoint $endpoint
$file = Get-Item $FilePath
$blobName = "diagnostics/$([guid]::NewGuid())-$($file.Name)"
$expiry = (Get-Date).ToUniversalTime().AddHours(1).ToString("yyyy-MM-ddTHH:mmZ")

Write-Host "Subiendo archivo a Blob Storage..." -ForegroundColor Cyan
Invoke-AzCli storage blob upload `
  --connection-string $storageConnectionString `
  --container-name $container `
  --name $blobName `
  --file $file.FullName `
  --overwrite true 1>$null

$sas = Invoke-AzCli storage blob generate-sas `
  --connection-string $storageConnectionString `
  --container-name $container `
  --name $blobName `
  --permissions r `
  --expiry $expiry `
  -o tsv

$accountName = ""
$storageConnectionString.Split(';') | ForEach-Object {
  if ($_ -like 'AccountName=*') { $script:accountName = $_.Split('=', 2)[1] }
}
if (-not $accountName) { throw "No pude leer AccountName desde AZURE_STORAGE_CONNECTION_STRING." }

$inputUrl = "https://$accountName.blob.core.windows.net/$container/$blobName`?$sas"

Write-Host "Endpoint : $endpoint" -ForegroundColor Cyan
Write-Host "Analyzer : $AnalyzerId" -ForegroundColor Cyan
Write-Host "Archivo  : $($file.Name)" -ForegroundColor Cyan
Write-Host "Blob SAS : generado por 1 hora" -ForegroundColor Cyan

Write-Host ""
Write-Host "Enviando analisis con Blob SAS..." -ForegroundColor Cyan
$requestBody = @{ inputs = @(@{ url = $inputUrl }) } | ConvertTo-Json -Depth 5

try {
  $response = Invoke-WebRequest `
    -UseBasicParsing `
    -Method Post `
    -Uri "$endpoint/contentunderstanding/analyzers/${AnalyzerId}:analyze?api-version=$ApiVersion" `
    -Headers @{ "Ocp-Apim-Subscription-Key" = $key; "Content-Type" = "application/json" } `
    -Body $requestBody
} catch {
  Write-Host "POST fallo:" -ForegroundColor Red
  Write-Host $_.Exception.Message
  $body = Get-ResponseBody $_
  if ($body) { Write-Host $body }
  exit 1
}

$operationLocation = $response.Headers["Operation-Location"]
if (-not $operationLocation) { throw "Azure no devolvio Operation-Location." }
Write-Host "Operation-Location recibido." -ForegroundColor Green

for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
  try {
    $result = Invoke-RestMethod `
      -Method Get `
      -Uri $operationLocation `
      -Headers @{ "Ocp-Apim-Subscription-Key" = $key }
  } catch {
    Write-Host "GET resultado fallo:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    $body = Get-ResponseBody $_
    if ($body) { Write-Host $body }
    exit 1
  }

  $status = $result.status
  Write-Host "Estado: $status ($attempt/$MaxAttempts)"

  if ($status -eq "Succeeded") {
    Write-Host "Analisis correcto." -ForegroundColor Green
    $result | ConvertTo-Json -Depth 10
    exit 0
  }

  if ($status -in @("Failed", "Error", "Canceled", "Cancelled")) {
    Write-Host "Analisis fallo." -ForegroundColor Red
    $result | ConvertTo-Json -Depth 10
    exit 1
  }

  Start-Sleep -Seconds $DelaySeconds
}

Write-Host "Timeout esperando resultado." -ForegroundColor Red
exit 1