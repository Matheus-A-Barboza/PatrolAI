
@echo off
cd /d "%~dp0"

echo =================================
echo      PatrolAI v0.1 - Bridge
echo          Python 3.13
echo =================================

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    py -3.13 -m venv .venv

    if errorlevel 1 (
        echo Erro ao criar ambiente virtual.
        pause
        exit /b 1
    )
)

echo Instalando dependencias...
".venv\Scripts\python.exe" -m pip install -r requirements.txt

if errorlevel 1 (
    echo Erro ao instalar dependencias.
    pause
    exit /b 1
)

echo Iniciando PatrolAI...
".venv\Scripts\python.exe" server.py

pause
