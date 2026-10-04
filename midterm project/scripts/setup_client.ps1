# PowerShell Setup Script for Client Node
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Setting up Distributed GPU Client Node      " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 1. Check Python
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python is not installed or not on system PATH."
    exit 1
}
Write-Host "[✓] Python detected: $pythonVersion" -ForegroundColor Green

# 2. Check FFmpeg (optional for client, required for local benchmark)
$ffmpegVersion = ffmpeg -version 2>&1 | Select-Object -First 1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[✓] FFmpeg detected: $ffmpegVersion (Local benchmarks enabled)" -ForegroundColor Green
} else {
    Write-Warning "[!] FFmpeg not detected on client. Local CPU benchmarks will not run."
}

# 3. Install requirements
Write-Host "[*] Installing Python requirements..." -ForegroundColor Yellow
python -m pip install -r requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "[✓] Dependencies installed successfully." -ForegroundColor Green
} else {
    Write-Error "Failed to install dependencies."
    exit 1
}

# 4. Check or create .env
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[✓] Created default .env file from .env.example" -ForegroundColor Green
}

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Setup complete! Launch client GUI with:     " -ForegroundColor Cyan
Write-Host "   python client/main.py                     " -ForegroundColor Yellow
Write-Host "=============================================" -ForegroundColor Cyan
