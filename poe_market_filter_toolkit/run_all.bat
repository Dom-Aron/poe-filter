@echo off
setlocal
cd /d "%~dp0"
echo.
echo =======================================
echo  PoE Market Filter Toolkit
echo =======================================
echo.

python scripts\run_all.py

echo.
echo Concluido. Veja os relatorios em market\reports\
pause
