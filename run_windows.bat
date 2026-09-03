@echo off
setlocal
cd /d "%~dp0"
if not exist .venv (
  py -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
start "Postnode API" cmd /k python -m uvicorn app.main:app --reload
timeout /t 3 /nobreak >nul
start http://127.0.0.1:8000/docs
endlocal
