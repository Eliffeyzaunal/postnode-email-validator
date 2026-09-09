@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\activate.bat (
  echo Projenin .venv ortami bulunamadi.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
if errorlevel 1 exit /b 1
docker compose up -d --wait mysql
if errorlevel 1 (
  echo MySQL baslatilamadi. Docker Desktop'i acip tekrar deneyin.
  pause
  exit /b 1
)
python scripts\collect_delivery_evidence.py
if errorlevel 1 (
  echo Olcum tamamlanamadi. Yukaridaki hata giderilmeden teslim kaniti hazir sayilmaz.
  pause
  exit /b 1
)
echo Sonuclar outputs\evidence klasorunde.
pause
endlocal
