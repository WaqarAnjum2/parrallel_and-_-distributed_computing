# Performance Benchmarking & Evaluation Methodology

This document outlines the benchmarking formulas, test scenarios, and performance evaluation criteria for the Distributed GPU Task Offloading system.

---

## 📐 Benchmark Metrics & Formulas

### 1. Timing Breakdown
The total remote offloading turnaround time $T_{\text{remote}}$ encompasses network transfer and processing:
$$T_{\text{remote}} = T_{\text{upload}} + T_{\text{gpu}} + T_{\text{download}}$$

Where:
- $T_{\text{upload}}$: Time elapsed from starting HTTP chunked upload until SHA-256 verification completes on worker.
- $T_{\text{gpu}}$: Execution time taken by the worker FFmpeg subprocess using NVIDIA NVENC.
- $T_{\text{download}}$: Time taken to stream the completed output file from the worker back to the client.

### 2. Local Execution Time
$T_{\text{local}}$ is the time taken by the client machine to encode the exact same video file locally using CPU-based FFmpeg (`libx264`) with identical resolution, bitrate, and preset targets.

### 3. Speedup Factor
$$\text{Speedup} = \frac{T_{\text{local}}}{T_{\text{remote}}}$$

- $\text{Speedup} > 1.0$: Remote offloading provides a net performance gain.
- $\text{Speedup} < 1.0$: Network overhead outweighs the computational benefit (typically on very small files or very slow networks).

### 4. Network Overhead Percentage
$$\text{Overhead \%} = \left( \frac{T_{\text{upload}} + T_{\text{download}}}{T_{\text{remote}}} \right) \times 100$$

---

## 🧪 Standard Benchmark Test Scenarios

| Test ID | Scenario | Resolution | Duration | Target Bitrate | Description |
|---|---|---|---|---|---|
| **B01** | Small Video | 1280x720 (720p) | 30s | 3M | Tests low computational load where network transfer may dominate. |
| **B02** | Standard 1080p | 1920x1080 (1080p) | 60s | 5M | Balanced real-world scenario demonstrating significant GPU acceleration. |
| **B03** | Long 1080p | 1920x1080 (1080p) | 300s | 8M | High computational complexity showing maximum offloading efficiency. |
| **B04** | 4K High Bitrate | 3840x2160 (4K UHD) | 60s | 20M | Heavy memory and compute stress test for NVENC hardware encoders. |
| **B05** | Wi-Fi vs Ethernet | 1920x1080 (1080p) | 60s | 5M | Evaluates network transmission latency impact on total turnaround time. |
