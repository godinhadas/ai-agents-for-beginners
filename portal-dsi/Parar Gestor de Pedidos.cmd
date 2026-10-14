@echo off
rem Para o Gestor de Pedidos DSI (porta 8010) e fecha a janela do servidor.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0parar.ps1"
timeout /t 3 >nul
