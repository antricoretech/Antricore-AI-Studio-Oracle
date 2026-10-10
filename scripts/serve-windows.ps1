Set-Location (Split-Path -Parent $PSScriptRoot)
& .\.venv\Scripts\python.exe -m uvicorn studio.app:app --reload --host 127.0.0.1 --port 8000
