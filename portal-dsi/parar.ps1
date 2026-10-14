# Para o Gestor de Pedidos DSI: o processo que escuta na porta e a janela PowerShell que o lancou.
param([int]$Porta = 8010)
$pids = Get-NetTCPConnection -LocalPort $Porta -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
if (-not $pids) { Write-Host "Nao estava a correr."; return }
foreach ($id in $pids) {
    # Sobe na cadeia python.exe (venv) > python.exe > powershell.exe e termina tudo.
    $actual = $id
    while ($actual) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$actual" -ErrorAction SilentlyContinue
        if (-not $proc -or $proc.Name -notin @("python.exe", "powershell.exe", "pwsh.exe")) { break }
        Stop-Process -Id $actual -Force -ErrorAction SilentlyContinue
        $actual = $proc.ParentProcessId
    }
}
Write-Host "Gestor de Pedidos DSI parado." -ForegroundColor Green
