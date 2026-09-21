# Start SP-Tech Software Solution on ports 80 + 443 with SSL (self-signed).
# Right-click → Run with PowerShell as Administrator, OR from an elevated shell:
#   cd "D:\Site\sanjivanioneSite"
#   .\deploy\start_https.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

# Relaunch elevated if needed
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).
    IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Requesting Administrator privileges for ports 80/443..." -ForegroundColor Yellow
    Start-Process powershell -Verb RunAs -ArgumentList @(
        "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`""
    )
    exit
}

$Python = Join-Path $Root "venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "Virtualenv not found. Create it first:" -ForegroundColor Red
    Write-Host "  python -m venv venv"
    Write-Host "  .\venv\Scripts\pip install -r requirements.txt"
    exit 1
}

Write-Host "Installing/updating HTTPS dependencies..." -ForegroundColor Cyan
& $Python -m pip install -q waitress cryptography python-dotenv

Write-Host "Generating SSL certificate for sanjivani.com..." -ForegroundColor Cyan
& $Python deploy\generate_ssl_cert.py --domains "sanjivanione.in,www.sanjivanione.in,sanjivanione.com,www.sanjivanione.com,sanjivani.com,www.sanjivani.com,localhost,127.0.0.1"

Write-Host "Trusting SSL certificate in Windows (Trusted Root)..." -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "trust_ssl_cert.ps1")

Write-Host "Stopping any previous instance on ports 80, 443, 8000, and 8001..." -ForegroundColor Cyan
foreach ($p in 80, 443, 8000, 8001) {
    Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue |
        ForEach-Object {
            if ($_.OwningProcess -gt 4) {
                Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
            }
        }
}

Write-Host "Applying database migrations..." -ForegroundColor Cyan
$env:DJANGO_SETTINGS_MODULE = "sanjivani.settings"
& $Python manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Database migrate failed." -ForegroundColor Red
    exit 1
}

Write-Host "Ensuring superAdmin account..." -ForegroundColor Cyan
& $Python manage.py ensure_superadmin

Write-Host "Collecting static files..." -ForegroundColor Cyan
& $Python manage.py collectstatic --noinput --clear

Write-Host "Starting SP-Tech Software Solution on http://0.0.0.0:80 and https://0.0.0.0:443 ..." -ForegroundColor Green
Write-Host "Open https://www.sanjivani.com/ or https://localhost/ (cert is trusted on this PC)" -ForegroundColor Green
Write-Host "Local test: https://127.0.0.1/" -ForegroundColor Green
& $Python runserver.py
