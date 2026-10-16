# Arranca o Gestor de Pedidos DSI.
#   .\iniciar.ps1                  so neste PC (http://localhost:8010)
#   .\iniciar.ps1 -Rede            acessivel aos colegas na rede da MHAIS (http://<IP-deste-PC>:8010)
#   .\iniciar.ps1 -Porta 8020      outra porta
param([int]$Porta = 8010, [switch]$Rede)
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

if ($Rede) {
    $ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" -and $_.InterfaceAlias -notmatch "vEthernet|Loopback|VirtualBox|VMware" } |
        Select-Object -ExpandProperty IPAddress
    Write-Host ""
    Write-Host "Gestor de Pedidos DSI acessivel na rede. Envia ao colega (o nome nao muda quando o IP muda):" -ForegroundColor Green
    Write-Host "   http://$($env:COMPUTERNAME.ToLower()):$Porta" -ForegroundColor Cyan
    foreach ($ip in $ips) { Write-Host "   http://${ip}:$Porta   (IP actual)" }
    Write-Host ""
    Write-Host "Se o colega nao conseguir abrir, cria a regra de firewall (PowerShell como administrador):" -ForegroundColor Yellow
    Write-Host "   New-NetFirewallRule -DisplayName 'Gestor de Pedidos DSI (teste)' -Direction Inbound -Protocol TCP -LocalPort $Porta -Action Allow -Profile Domain,Private"
    Write-Host "Modo de teste: quem abrir o endereco escolhe o utilizador sem palavra-passe. Fecha esta janela no fim do teste." -ForegroundColor Yellow
    Write-Host ""
    & $py -m uvicorn portal.main:app --host 0.0.0.0 --port $Porta
} else {
    Write-Host "Gestor de Pedidos DSI em http://localhost:$Porta"
    & $py -m uvicorn portal.main:app --host 127.0.0.1 --port $Porta --reload
}
