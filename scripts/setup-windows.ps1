$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
Write-Host "READY. In VS Code select .venv interpreter and run 'AI Influencer Studio' launch config."
