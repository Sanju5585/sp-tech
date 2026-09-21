@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo   SP-Tech Software Solution
echo   HTTPS on port 443  (HTTP 80 redirects)
echo   Domain: sanjivani.com / www.sanjivani.com
echo ========================================
echo.

REM Require Administrator for ports 80/443
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator privileges for ports 80/443...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtualenv not found at venv\Scripts\python.exe
    echo Create it with: python -m venv venv
    echo Then: venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

echo Stopping any previous instance on ports 80, 443, 8000, and 8001...
powershell -NoProfile -Command "foreach ($p in 80,443,8000,8001) { Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue | ForEach-Object { if ($_.OwningProcess -gt 4) { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } } }"

echo Installing/updating runtime packages...
"venv\Scripts\python.exe" -m pip install -q waitress cryptography python-dotenv

echo Generating SSL certificate for sanjivani.com...
"venv\Scripts\python.exe" deploy\generate_ssl_cert.py --domains "sanjivanione.in,www.sanjivanione.in,sanjivanione.com,www.sanjivanione.com,sanjivani.com,www.sanjivani.com,localhost,127.0.0.1"

echo Trusting SSL certificate in Windows Trusted Root...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy\trust_ssl_cert.ps1"

echo Applying database migrations...
set DJANGO_SETTINGS_MODULE=sanjivani.settings
"venv\Scripts\python.exe" manage.py migrate --noinput
if errorlevel 1 (
    echo ERROR: Database migrate failed.
    pause
    exit /b 1
)

echo Ensuring superAdmin account...
"venv\Scripts\python.exe" manage.py ensure_superadmin

echo Collecting static files...
"venv\Scripts\python.exe" manage.py collectstatic --noinput --clear

echo.
echo Starting server...
echo   HTTP:  http://sanjivani.com/   ^(redirects to HTTPS^)
echo   HTTPS: https://www.sanjivani.com/
echo   Local: https://127.0.0.1/
echo.
echo Press Ctrl+C to stop.
echo.

set PYTHONUNBUFFERED=1
"venv\Scripts\python.exe" runserver.py

echo.
echo Server stopped.
pause
