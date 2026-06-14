param(
  [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venv = Join-Path $root ".venv"
$python = Join-Path $venv "Scripts\python.exe"

if (-not (Test-Path $python)) {
  py -m venv $venv
}

if (-not $SkipInstall) {
  & $python -m pip install --upgrade pip
  & $python -m pip install -r (Join-Path $root "requirements.txt")
}

$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"

& $python -m streamlit run (Join-Path $root "streamlit_app.py") --server.address 0.0.0.0 --server.port 8501 --server.headless true
