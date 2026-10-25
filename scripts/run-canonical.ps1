param(
    [int]$Port = 8123,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Studio virtual environment not found: $Python"
}

$env:STUDIO_APP_SURFACE = "canonical"
$env:DATA_DIR = Join-Path $ProjectRoot "data\canonical"
$env:STUDIO_GENERATED_DIR = Join-Path $ProjectRoot "data\canonical\generated"
$ReloadArgs = if ($Reload) { @("--reload") } else { @() }

& $Python -m uvicorn studio.canonical_app:app --host 127.0.0.1 --port $Port @ReloadArgs
exit $LASTEXITCODE
