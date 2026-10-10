# Installs Studio control-plane and optional LOCAL (free) model inference dependencies.
param([switch]$Image,[switch]$Voice,[switch]$DownloadTools)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not (Test-Path .venv)) { py -3.12 -m venv .venv; if($LASTEXITCODE -ne 0){throw 'Install Python 3.12 first'} }
$python=Join-Path $root '.venv/Scripts/python.exe'
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt
if ($DownloadTools) { & $python -m pip install -r requirements-download.txt }
if ($Image) {
 Write-Host 'Install NVIDIA-compatible PyTorch FIRST as directed at https://pytorch.org/get-started/locally/'
 & $python -m pip install -r requirements-local-image.txt
}
if ($Voice) { & $python -m pip install -r requirements-voice.txt }
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
& $python -m studio.free_cli doctor
Write-Host 'Run: .venv/Scripts/python.exe -m uvicorn studio.app:app --host 127.0.0.1 --port 8000'
