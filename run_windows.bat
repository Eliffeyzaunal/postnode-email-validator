@echo off
setlocal
cd /d "%~dp0"
docker compose up -d --wait mysql
if errorlevel 1 (
  echo MySQL baslatilamadi. Docker Desktop'in acik oldugunu kontrol edin.
  exit /b 1
)
if not exist .venv (
  py -m venv .venv
)
call .venv\Scripts\activate.bat
if errorlevel 1 exit /b 1
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
rem This launcher starts the monitor, so a missing heartbeat must fail health.
set "BLOCKLIST_MONITOR_REQUIRED=true"
start "Postnode Blocklist Monitor" cmd /k python -m app.blocklist.scheduler_cli
start "Postnode API" cmd /k python -m uvicorn app.main:app --reload
timeout /t 3 /nobreak >nul
start http://127.0.0.1:8000/docs
endlocal
