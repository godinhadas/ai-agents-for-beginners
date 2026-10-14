@echo off
rem Arranca o Gestor de Pedidos DSI na rede (porta 8010) e abre o browser.
rem Se ja estiver a correr, so abre o browser.
cd /d "%~dp0"
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue) { exit 1 }"
if errorlevel 1 goto abrir
start "Gestor de Pedidos DSI (servidor)" /min powershell -NoProfile -ExecutionPolicy Bypass -NoExit -File "%~dp0iniciar.ps1" -Rede
echo A arrancar o Gestor de Pedidos DSI...
rem Espera ate 3 minutos (a primeira vez instala as dependencias).
powershell -NoProfile -Command "for ($i=0; $i -lt 180; $i++) { if (Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue) { exit 0 }; Start-Sleep 1 }; exit 1"
if errorlevel 1 (
  echo Nao arrancou. Abre a janela "Gestor de Pedidos DSI (servidor)" na barra de tarefas para ver o erro.
  pause
  exit /b 1
)
:abrir
start "" http://localhost:8010
