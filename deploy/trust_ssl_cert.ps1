# Trust deploy/certs/cert.pem so browsers stop showing
# NET::ERR_CERT_AUTHORITY_INVALID for local HTTPS.
#
# Prefers Current User store (no admin). Falls back to Local Machine Root if elevated.

$ErrorActionPreference = "Stop"
$CertPem = Join-Path $PSScriptRoot "certs\cert.pem"

if (-not (Test-Path $CertPem)) {
    Write-Host "Certificate not found: $CertPem" -ForegroundColor Red
    exit 1
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).
    IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

function Remove-MatchingRoots {
    param([string]$StorePath)
    Get-ChildItem $StorePath -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Subject -match 'CN=(sanjivanione\.in|www\.sanjivanione\.in|sanjivanione\.com|www\.sanjivanione\.com|sanjivani\.com|www\.sanjivani\.com|localhost)' -or
            $_.Issuer -match 'O=SP-Tech Software Solution'
        } |
        ForEach-Object {
            Write-Host "Removing old trusted cert: $($_.Subject)" -ForegroundColor DarkYellow
            Remove-Item $_.PSPath -Force -ErrorAction SilentlyContinue
        }
}

# Convert PEM -> DER .cer for Import-Certificate
$CertCer = Join-Path $PSScriptRoot "certs\cert.cer"
$pemText = Get-Content -Raw $CertPem
$b64 = ($pemText -replace '-----BEGIN CERTIFICATE-----', '' -replace '-----END CERTIFICATE-----', '' -replace '\s', '')
[IO.File]::WriteAllBytes($CertCer, [Convert]::FromBase64String($b64))

# 1) Current user (works for Edge/Chrome for this Windows account)
Remove-MatchingRoots 'Cert:\CurrentUser\Root'
Import-Certificate -FilePath $CertCer -CertStoreLocation Cert:\CurrentUser\Root | Out-Null
Write-Host "Trusted in Current User Root: $CertPem" -ForegroundColor Green

# 2) Also Local Machine if we already have admin (startup scripts run elevated)
if ($isAdmin) {
    Remove-MatchingRoots 'Cert:\LocalMachine\Root'
    & certutil -addstore -f "Root" $CertPem | Out-Host
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Trusted in Local Machine Root (all users on this PC)." -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Close ALL browser windows, then open https://localhost/ or https://127.0.0.1/" -ForegroundColor Cyan
Write-Host "It should show as Secure." -ForegroundColor Cyan
Write-Host "Note: other PCs / the public internet still need a real CA (Let's Encrypt)." -ForegroundColor DarkGray
