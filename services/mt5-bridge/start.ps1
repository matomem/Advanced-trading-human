$ErrorActionPreference = "Stop"
if (-not (Test-Path ".env")) {
  Write-Error "Copy .env.example to .env and configure MT5/XM demo credentials and BRIDGE_API_TOKEN first."
}
if (-not (Test-Path ".venv")) { py -3.11 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000 --env-file .env
