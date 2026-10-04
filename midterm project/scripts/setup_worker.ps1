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

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Setup complete! Start worker with:          " -ForegroundColor Cyan
Write-Host "   python worker/main.py                     " -ForegroundColor Yellow
Write-Host "=============================================" -ForegroundColor Cyan
