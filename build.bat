@echo off
cd /d %~dp0
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Building with PyInstaller...
pyinstaller --clean build.spec
echo.
if exist dist\MT5_EA_Tester.exe (
    echo Build successful: dist\MT5_EA_Tester.exe
) else (
    echo Build failed. Check the output above.
)
pause
