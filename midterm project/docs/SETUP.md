# Installation and Setup Guide

This guide walks through configuring both the **Remote GPU Worker** and the **Client Computer**.

---

## 🖥️ Worker Machine Setup (GPU Node)

### 1. Prerequisites
- **OS**: Windows 10/11 (or Linux with NVIDIA proprietary drivers).
- **GPU**: NVIDIA GeForce, Quadro, Tesla, or RTX GPU with NVENC hardware encoding support.
- **Python**: Version 3.10 to 3.14.

### 2. Install FFmpeg with NVENC Support
1. Download a complete FFmpeg build (e.g. from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)).
2. Extract the archive to `C:\ffmpeg`.
3. Add `C:\ffmpeg\bin` to your system `PATH`.
4. Verify NVENC support in PowerShell:
   ```powershell
   ffmpeg -encoders | findstr nvenc
   ```
   You should see `h264_nvenc`, `hevc_nvenc`, and optionally `av1_nvenc`.

### 3. Install Python Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Worker Environment
Create a `.env` file in the project root:
```ini
WORKER_HOST=0.0.0.0
WORKER_PORT=8000
AUTH_TOKEN=supersecret_token_12345
MAX_QUEUE_SIZE=10
MAX_CONCURRENT_JOBS=1
MAX_JOB_DURATION_SECONDS=7200
DATA_DIR=data
```

### 5. Launch Worker Service
```powershell
python worker/main.py
```

---

## 💻 Client Machine Setup

### 1. Prerequisites
- Python 3.10+
- FFmpeg (required on client for local CPU benchmark comparison and FFprobe metadata extraction).

### 2. Configure Client Environment
In your `.env` (or via the GUI Connection tab):
```ini
WORKER_HOST=192.168.1.10
WORKER_PORT=8000
AUTH_TOKEN=supersecret_token_12345
```

### 3. Launch the Client GUI
```powershell
python client/main.py
```
