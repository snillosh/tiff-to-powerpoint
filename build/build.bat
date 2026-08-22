@echo off
setlocal
cd /d "%~dp0\.."

where py >nul 2>nul
if errorlevel 1 (
    echo ERROR: The Python launcher was not found. Install 64-bit Python 3.12 on the build machine.
    exit /b 1
)

if not exist ".venv-build\Scripts\python.exe" (
    py -3.12 -m venv .venv-build
    if errorlevel 1 exit /b 1
)

call ".venv-build\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1
python -m pip install --upgrade -e ".[dev,build]"
if errorlevel 1 exit /b 1
python build\build.py
if errorlevel 1 exit /b 1

echo.
echo Native portable application and release archive created successfully.
echo See the build-output and releases directories.
endlocal
