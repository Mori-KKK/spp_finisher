@echo off
echo ============================================
echo   SPP Finisher - Windows Build
echo ============================================
echo.

REM Check if pyinstaller is available
python -m PyInstaller --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller not found. Install it first:
    echo   pip install pyinstaller
    pause
    exit /b 1
)

echo [1/3] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [2/3] Building SPP_Finisher.exe ...
python -m PyInstaller ^
    --name "SPP_Finisher" ^
    --windowed ^
    --icon "assets/app_icon.png" ^
    --add-data "assets;assets" ^
    --add-data "src/style.qss;." ^
    --paths "src" ^
    --hidden-import "PySide6.QtWidgets" ^
    --hidden-import "PySide6.QtGui" ^
    --hidden-import "PySide6.QtCore" ^
    --hidden-import "cv2" ^
    --hidden-import "numpy" ^
    --hidden-import "tifffile" ^
    --hidden-import "exifread" ^
    --hidden-import "PIL" ^
    --hidden-import "watchdog" ^
    --noconfirm ^
    src/main.py

if %errorlevel% neq 0 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo [3/3] Done!
echo.
echo   Output: dist\SPP_Finisher\SPP_Finisher.exe
echo.
pause
