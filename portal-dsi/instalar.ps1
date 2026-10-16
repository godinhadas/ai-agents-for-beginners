# Instala o Gestor de Pedidos DSI neste computador (de raiz ou por cima de uma instalacao existente).
# Uso (PowerShell; como administrador, para criar tambem a regra de firewall):
#   iwr https://raw.githubusercontent.com/godinhadas/ai-agents-for-beginners/claude/crm-app-ujozhn/portal-dsi/instalar.ps1 -OutFile $env:TEMP\instalar-gpd.ps1
#   powershell -ExecutionPolicy Bypass -File $env:TEMP\instalar-gpd.ps1
# Faz: instala Python e Git se faltarem (winget), descarrega so a pasta portal-dsi, cria o ambiente,
# instala as dependencias, cria a regra de firewall, os atalhos e o arranque automatico, e arranca.
param(
    [string]$Destino = "C:\Projectos\ai-agents-for-beginners",
    [string]$Ramo = "claude/crm-app-ujozhn",
    [int]$Porta = 8010
)
$ErrorActionPreference = "Stop"
$repo = "https://github.com/godinhadas/ai-agents-for-beginners.git"
function Passo($t) { Write-Host ""; Write-Host "== $t" -ForegroundColor Cyan }
function Actualizar-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}
function Tem($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

Passo "1/6 Python e Git"
if (-not (Tem py) -and -not (Tem python)) {
    if (-not (Tem winget)) { throw "Falta o Python. Instala o Python 3.12 ou superior (python.org, com 'Add to PATH') e volta a correr." }
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    Actualizar-Path
}
if (-not (Tem git)) {
    if (-not (Tem winget)) { throw "Falta o Git. Instala o Git (git-scm.com) e volta a correr." }
    winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements
    Actualizar-Path
}
$pyLanc = if (Tem py) { "py" } else { "python" }
& $pyLanc --version

Passo "2/6 Codigo do portal ($Ramo)"
$pasta = Join-Path $Destino "portal-dsi"
if (Test-Path (Join-Path $Destino ".git")) {
    git -C $Destino fetch origin $Ramo
    git -C $Destino checkout $Ramo
    git -C $Destino pull origin $Ramo
} else {
    New-Item -ItemType Directory -Force -Path (Split-Path $Destino) | Out-Null
    git clone --depth 1 --filter=blob:none --sparse -b $Ramo $repo $Destino
    git -C $Destino sparse-checkout set portal-dsi
}
if (-not (Test-Path (Join-Path $pasta "portal\main.py"))) { throw "Nao encontrei o portal em $pasta." }
Set-Location $pasta

Passo "3/6 Ambiente Python e dependencias"
if (Test-Path ".\parar.ps1") { & .\parar.ps1 -Porta $Porta }
if (-not (Test-Path ".\.venv\Scripts\python.exe")) { & $pyLanc -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) { throw "Falhou a instalacao das dependencias." }
if (-not (Test-Path ".\.env")) { Copy-Item .env.example .env }

Passo "4/6 Firewall (porta $Porta, rede de dominio e privada)"
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$regra = "Gestor de Pedidos DSI"
if (Get-NetFirewallRule -DisplayName $regra -ErrorAction SilentlyContinue) {
    Write-Host "Regra ja existe."
} elseif ($admin) {
    New-NetFirewallRule -DisplayName $regra -Direction Inbound -Protocol TCP -LocalPort $Porta -Action Allow -Profile Domain,Private | Out-Null
    Write-Host "Regra criada."
} else {
    Write-Host "Sem permissoes de administrador: os colegas podem nao conseguir abrir o portal." -ForegroundColor Yellow
    Write-Host "Corre como administrador: New-NetFirewallRule -DisplayName '$regra' -Direction Inbound -Protocol TCP -LocalPort $Porta -Action Allow -Profile Domain,Private"
}

Passo "5/6 Atalhos e arranque automatico"
& .\instalar-atalhos.ps1

Passo "6/6 Arranque"
Start-Process -FilePath (Join-Path $pasta "Arrancar Gestor de Pedidos.cmd") -WorkingDirectory $pasta -WindowStyle Minimized
$ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" -and $_.InterfaceAlias -notmatch "vEthernet|Loopback|VirtualBox|VMware" } |
    Select-Object -ExpandProperty IPAddress
Write-Host ""
Write-Host "Instalado em $pasta" -ForegroundColor Green
Write-Host "Neste PC:   http://localhost:$Porta"
foreach ($ip in $ips) { Write-Host "Colegas:    http://${ip}:$Porta" -ForegroundColor Cyan }
Write-Host "Primeiro acesso: entra como 'Administrador DSI' e cria os utilizadores em Administracao."
