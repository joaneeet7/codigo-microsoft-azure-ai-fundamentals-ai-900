param(
  [string]$AnalyzerId = "prebuilt-invoice",
  [string]$InputUrl = "https://github.com/Azure-Samples/azure-ai-content-understanding-python/raw/refs/heads/main/data/invoice.pdf",
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

$envValues = Read-EnvFile $envPath
$endpoint = $envValues["CONTENT_UNDERSTANDING_ENDPOINT"]
$key = $envValues["CONTENT_UNDERSTANDING_KEY"]

if (-not $endpoint -or -not $key) {
  throw "Faltan CONTENT_UNDERSTANDING_ENDPOINT o CONTENT_UNDERSTANDING_KEY en backend/.env."
}

$endpoint = Get-CuEndpoint $endpoint
$headers = @{ "Ocp-Apim-Subscription-Key" = $key; "Content-Type" = "application/json" }

Write-Host "Endpoint : $endpoint" -ForegroundColor Cyan
Write-Host "Analyzer : $AnalyzerId" -ForegroundColor Cyan
Write-Host "Input    : $InputUrl" -ForegroundColor Cyan

Write-Host ""
Write-Host "Defaults actuales" -ForegroundColor Cyan
try {
  Invoke-RestMethod `
    -Method Get `
    -Uri "$endpoint/contentunderstanding/defaults?api-version=$ApiVersion" `
    -Headers @{ "Ocp-Apim-Subscription-Key" = $key } | ConvertTo-Json -Depth 10
} catch {
  Write-Host "No se pudieron leer defaults:" -ForegroundColor Yellow
  Write-Host $_.Exception.Message
  $body = Get-ResponseBody $_
  if ($body) { Write-Host $body }
}

Write-Host ""
Write-Host "Enviando analisis oficial..." -ForegroundColor Cyan
$requestBody = @{ inputs = @(@{ url = $InputUrl }) } | ConvertTo-Json -Depth 5

try {
  $response = Invoke-WebRequest `
    -Method Post `
    -Uri "$endpoint/contentunderstanding/analyzers/${AnalyzerId}:analyze?api-version=$ApiVersion" `
    -Headers $headers `
    -Body $requestBody
} catch {
  Write-Host "POST fallo:" -ForegroundColor Red
  Write-Host $_.Exception.Message
  $body = Get-ResponseBody $_
  if ($body) { Write-Host $body }
  exit 1
}

$operationLocation = $response.Headers["Operation-Location"]
if (-not $operationLocation) {
  throw "Azure no devolvio Operation-Location."
}

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