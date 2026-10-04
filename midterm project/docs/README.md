# Distributed GPU Task Offloading & Remote Video Processing System

A distributed client-server computing system that offloads computationally intensive video transcoding from a resource-constrained client machine to an NVIDIA GPU-accelerated worker over a local area network (LAN/Wi-Fi).

---

## ⚡ Key Highlights

- **Real Hardware Offloading**: Real FFmpeg subprocess orchestration leveraging NVIDIA NVENC hardware encoders (`h264_nvenc`, `hevc_nvenc`, `av1_nvenc`). Zero simulated or mocked metrics.
- **Advanced Desktop Interface**: PyQt6 dark-mode industrial console with real-time latency ping meters, 4-stage pipeline tracker, live FPS/speed counters, syntax-highlighted terminal log, and benchmark comparisons.
- **Zero-RAM Streaming**: End-to-end chunked streaming file transfers (upload and download) with on-the-fly SHA-256 integrity verification. Large multi-gigabyte video files never load into RAM.
- **Academic Benchmark Suite**: Measures exact timing breakdown ($T_{\text{upload}}$, $T_{\text{gpu}}$, $T_{\text{download}}$, $T_{\text{remote}}$, $T_{\text{local}}$), computes real speedup factor ($\text{Speedup} = T_{\text{local}} / T_{\text{remote}}$) and network overhead percentage, and exports data to JSON & CSV.
- **Enterprise-Grade Reliability**: Full handling of all 15 failure scenarios (E01–E15) including worker offline, checksum mismatch, worker disk exhaustion, cancellation, timeouts, and WebSocket reconnects.

---

## 🏛️ System Architecture

```text
┌───────────────────────────────────────────────┐
│              CLIENT COMPUTER (PyQt6)          │
│  - Advanced Dark Cyber Console                │
│  - Streaming SHA-256 Hasher                   │
│  - Chunked Transfer (HTTPX)                   │
│  - Live WebSocket Progress Receiver           │
│  - Local CPU Benchmark Engine (FFmpeg CPU)    │
└───────────────────────┬───────────────────────┘
                        │ HTTP / WebSocket (LAN/Wi-Fi)
                        ▼
┌───────────────────────────────────────────────┐
│             WORKER COMPUTER (FastAPI)         │
│  - REST API + Bearer Token Auth               │
│  - Real-time Hardware Detector (NVML + NVENC) │
│  - Strict Parameter Whitelist Validation      │
│  - Async Job Queue & Concurrency Controller   │
│  - FFmpeg Subprocess Runner (-progress pipe:1)│
│  - WebSocket Progress Broadcaster             │
└───────────────────────────────────────────────┘
```

---

## 🚀 Quick Start Guide

### 1. Requirements
- Python 3.10+
- FFmpeg & FFprobe installed and available on system PATH
- NVIDIA GPU with compatible driver (for the Worker node)

### 2. Installation
```powershell
pip install -r requirements.txt
```

### 3. Start the Worker (on GPU Machine)
```powershell
# Copy environment configuration
cp .env.example .env

# Run the FastAPI worker
python worker/main.py
```
The worker will display its readiness banner, detected GPU model, available NVENC encoders, and listening IP/Port.

### 4. Start the Client (on Client Machine)
```powershell
python client/main.py
```
- Navigate to the **Connection** tab, input the Worker's IP, port, and authentication token, and click **Test Connection**.
- Switch to the **Job** tab, select any video file, pick your target resolution/bitrate/preset, and click **Start Remote Processing**.
- Watch real-time multi-stage progress on the **Progress** tab and view complete benchmark analytics on the **Results** tab.

---

## 🧪 Testing Suite
Run all unit, integration, and failure test suites:
```powershell
pytest tests/ -v
```

---

## 📚 Documentation
- [Installation & Setup Guide](SETUP.md)
- [Network & Firewall Configuration](NETWORK.md)
- [Benchmark Methodology & Test Scenarios](BENCHMARKS.md)
- [Academic Report Data Export](REPORT_DATA.md)
