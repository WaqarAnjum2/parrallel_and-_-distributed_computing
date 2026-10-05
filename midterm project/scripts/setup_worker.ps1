# PowerShell Setup Script for Remote GPU Worker
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Setting up Distributed GPU Worker Node      " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 1. Check Python version
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python is not installed or not on system PATH."
    exit 1
}
Write-Host "[✓] Python detected: $pythonVersion" -ForegroundColor Green

# 2. Check FFmpeg and NVENC
$ffmpegVersion = ffmpeg -version 2>&1 | Select-Object -First 1
if ($LASTEXITCODE -ne 0) {
    Write-Warning "[!] FFmpeg was not detected on system PATH. Please install FFmpeg."
} else {
    Write-Host "[✓] FFmpeg detected: $ffmpegVersion" -ForegroundColor Green
    $nvenc = ffmpeg -encoders 2>&1 | Select-String "nvenc"
    if ($nvenc) {
        Write-Host "[✓] NVENC hardware encoders detected:" -ForegroundColor Green
        $nvenc | ForEach-Object { Write-Host "    $($_)" -ForegroundColor Gray }
    } else {
        Write-Warning "[!] No NVENC encoders detected. GPU acceleration will not be available."
    }
}

# 3. Install Python requirements
Write-Host "[*] Installing Python requirements..." -ForegroundColor Yellow
python -m pip install -r requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "[✓] Dependencies installed successfully." -ForegroundColor Green
} else {
    Write-Error "Failed to install dependencies."
    exit 1
}

# 4. Check or create .env file
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[✓] Created default .env file from .env.example" -ForegroundColor Green
} else {
    Write-Host "[✓] .env file already exists." -ForegroundColor Gray
}

# 5. Configure Windows Firewall for Port 8000
Write-Host "[*] Checking Windows Firewall rule for Port 8000..." -ForegroundColor Yellow
try {
    $existingRule = Get-NetFirewallRule -DisplayName "Distributed GPU Worker (TCP 8000)" -ErrorAction SilentlyContinue
    if (-not $existingRule) {
        $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        if ($isAdmin) {
            New-NetFirewallRule -DisplayName "Distributed GPU Worker (TCP 8000)" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Any -ErrorAction SilentlyContinue | Out-Null
            Write-Host "[✓] Windows Firewall rule created for TCP Port 8000." -ForegroundColor Green
        } else {
            Write-Host "[!] Note: To allow other laptops to connect over Wi-Fi, run in Admin PowerShell:" -ForegroundColor Yellow
            Write-Host "    New-NetFirewallRule -DisplayName 'Distributed GPU Worker (TCP 8000)' -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Any" -ForegroundColor Cyan
        }
    } else {
        Write-Host "[✓] Windows Firewall rule already active." -ForegroundColor Green
    }
} catch {
    Write-Host "[!] Firewall check skipped: $($_.Exception.Message)" -ForegroundColor Gray
}

# 6. Display Local Network IP
$localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch "Loopback|vEthernet|Virtual" -and $_.IPAddress -notmatch "^169\." } | Select-Object -ExpandProperty IPAddress -First 1)

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Setup complete!                             " -ForegroundColor Cyan
Write-Host " Your Local LAN IP: $localIP                 " -ForegroundColor Green
Write-Host " Start worker with:                          " -ForegroundColor Cyan
Write-Host "   python worker/main.py                     " -ForegroundColor Yellow
Write-Host " Connect client to: http://${localIP}:8000   " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
