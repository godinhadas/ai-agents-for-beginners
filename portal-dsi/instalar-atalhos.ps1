# Cria os atalhos do Gestor de Pedidos DSI (corre uma vez):
#   ambiente de trabalho: "Gestor de Pedidos DSI" (arranca e abre) e "Parar Gestor de Pedidos"
#   arranque do Windows: arranca sozinho quando entras no PC (depois de reiniciar)
#   .\instalar-atalhos.ps1                         cria tudo
#   .\instalar-atalhos.ps1 -SemArranqueAutomatico  so os atalhos do ambiente de trabalho
#   .\instalar-atalhos.ps1 -Remover                apaga todos os atalhos
param([switch]$SemArranqueAutomatico, [switch]$Remover)
$pasta = $PSScriptRoot
$sh = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath("Desktop")
$startup = [Environment]::GetFolderPath("Startup")
$atalhos = @(
    @{ Ficheiro = Join-Path $desktop "Gestor de Pedidos DSI.lnk"; Alvo = "Arrancar Gestor de Pedidos.cmd"; Icone = "shell32.dll,13" },
    @{ Ficheiro = Join-Path $desktop "Parar Gestor de Pedidos.lnk"; Alvo = "Parar Gestor de Pedidos.cmd"; Icone = "shell32.dll,27" }
)
if (-not $SemArranqueAutomatico) {
    $atalhos += @{ Ficheiro = Join-Path $startup "Gestor de Pedidos DSI.lnk"; Alvo = "Arrancar Gestor de Pedidos.cmd"; Icone = "shell32.dll,13" }
}
if ($Remover) {
    foreach ($f in @((Join-Path $desktop "Gestor de Pedidos DSI.lnk"), (Join-Path $desktop "Parar Gestor de Pedidos.lnk"), (Join-Path $startup "Gestor de Pedidos DSI.lnk"))) {
        if (Test-Path $f) { Remove-Item $f; Write-Host "Removido: $f" }
    }
    return
}
foreach ($a in $atalhos) {
    $s = $sh.CreateShortcut($a.Ficheiro)
    $s.TargetPath = Join-Path $pasta $a.Alvo
    $s.WorkingDirectory = $pasta
    $s.IconLocation = "$env:SystemRoot\System32\$($a.Icone)"
    $s.WindowStyle = 7
    $s.Save()
    Write-Host "Criado: $($a.Ficheiro)" -ForegroundColor Green
}
