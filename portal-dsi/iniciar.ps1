# Arranca o Gestor de Pedidos DSI. Uso: .\iniciar.ps1            (porta 8010)
#                           .\iniciar.ps1 -Porta 8020
param([int]$Porta = 8010)
Set-Location $PSScriptRoot
$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    py -m venv .venv
}
# Instala ou completa as dependencias sempre que faltar alguma (ex.: depois de um git pull).
& $py -c "import fastapi, uvicorn, sqlalchemy, itsdangerous, msal, dotenv" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $py -m pip install --upgrade pip
    & $py -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Write-Host "Falhou a instalacao das dependencias." -ForegroundColor Red; exit 1 }
}
if (-not (Test-Path .\.env)) { Copy-Item .env.example .env }
Write-Host "Gestor de Pedidos DSI em http://localhost:$Porta"
& $py -m uvicorn portal.main:app --host 127.0.0.1 --port $Porta --reload
