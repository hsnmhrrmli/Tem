@echo off
REM ============================================================
REM  Qaime -> Excel Cevirici - Windows .exe qurma skripti
REM  Bu faylı QaimeToExcel qovluğunda, Windows-da işə salın.
REM ============================================================

echo [1/3] Lazimi kitabxanalar qurulur...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo [2/3] .exe faylı hazırlanır (PyInstaller)...
python -m PyInstaller --onefile --windowed --name "QaimeToExcel" ^
  --icon "app_icon.ico" ^
  --add-data "app_icon.ico;." ^
  --add-data "app_icon.png;." ^
  --collect-data tkinterdnd2 app.py

echo.
echo [3/3] Hazırdır!
echo Nəticə fayl: dist\QaimeToExcel.exe
echo.
pause
