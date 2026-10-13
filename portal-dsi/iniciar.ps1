# Arranca o Portal DSI. Uso: .\iniciar.ps1            (porta 8010)
#                           .\iniciar.ps1 -Porta 8020
param([int]$Porta = 8010)
Set-Location $PSScriptRoot
if (-not (Test-Path .\.venv)) {
    py -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}
if (-not (Test-Path .\.env)) { Copy-Item .env.example .env }
Write-Host "Portal DSI em http://127.0.0.1:$Porta"
.\.venv\Scripts\python.exe -m uvicorn portal.main:app --host 127.0.0.1 --port $Porta --reload
