param(
    [int]$Port = 8124,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Studio virtual environment not found: $Python"
}

$env:STUDIO_APP_SURFACE = "legacy"
# The legacy process keeps the existing database/references/outputs location.
$env:DATA_DIR = Join-Path $ProjectRoot "data"
$env:STUDIO_GENERATED_DIR = Join-Path $ProjectRoot "generated"
$ReloadArgs = if ($Reload) { @("--reload") } else { @() }

& $Python -m uvicorn studio.legacy_app:app --host 127.0.0.1 --port $Port @ReloadArgs
exit $LASTEXITCODE
