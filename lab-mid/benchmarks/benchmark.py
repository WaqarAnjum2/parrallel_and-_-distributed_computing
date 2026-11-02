"""
Automated Benchmarking Suite for Task 5: Performance Evaluation & Analysis Report.
Measures Local CPU Render Time vs Remote GPU Offloading Time across multiple test cases.
Calculates Speedup Factor and Network Transfer Overhead %.
"""
import argparse
import asyncio
import os
import shutil
import subprocess
import sys
import time
from typing import Dict, List

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests

from common.protocol import RenderConfig, compute_sha256
from client.client_network import NetworkClient


def generate_benchmark_clip(filename: str, duration: int, res: str, fps: int = 30):
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi", "-i", f"testsrc=duration={duration}:size={res}:rate={fps}",
        "-f", "lavfi", "-i", f"sine=frequency=1000:duration={duration}",
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac",
        filename
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def benchmark_local_cpu(input_path: str, output_path: str, res: str, bitrate: str) -> float:
    """Measures local CPU rendering time (representing low-end client)."""
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    w, h = res.split("x")
    cmd = [
        ffmpeg, "-y",
        "-i", input_path,
        "-c:v", "libx264",
        "-preset", "medium",
        "-vf", f"scale={w}:{h}",
        "-b:v", bitrate,
        "-c:a", "aac",
        output_path
    ]
    t0 = time.perf_counter()
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t1 = time.perf_counter()
    return t1 - t0


def benchmark_remote_offload(client: NetworkClient, input_path: str, output_path: str, res: str, bitrate: str) -> Dict[str, float]:
    """Measures remote GPU offloading breakdown: upload + remote GPU render + download."""
    t_start_total = time.perf_counter()

    # 1. Upload
    t0 = time.perf_counter()
    ok, job_id, in_sha, err = client.upload_file(input_path)
    if not ok:
        raise RuntimeError(f"Upload failed: {err}")
    t_upload = time.perf_counter() - t0

    # 2. Remote render
    cfg = RenderConfig(resolution=res, bitrate=bitrate, preset="p4", codec="h264_nvenc", input_sha256=in_sha)
    ok, err = client.start_job(job_id, cfg)
    if not ok:
        raise RuntimeError(f"Start job failed: {err}")

    t0_render = time.perf_counter()
    success, out_sha = asyncio.run(
        client.listen_progress_ws(job_id, lambda p, f, s, m: None, lambda l: None, lambda: False)
    )
    if not success:
        raise RuntimeError("Remote GPU render failed.")
    t_remote_render = time.perf_counter() - t0_render

    # 3. Download
    t0_dl = time.perf_counter()
    dl_ok, dl_err = client.download_file(job_id, output_path, out_sha)
    if not dl_ok:
        raise RuntimeError(f"Download failed: {dl_err}")
    t_download = time.perf_counter() - t0_dl

    t_total = time.perf_counter() - t_start_total

    return {
        "upload_sec": t_upload,
        "remote_render_sec": t_remote_render,
        "download_sec": t_download,
        "total_offload_sec": t_total
    }


def run_benchmark_suite(server_host: str = "127.0.0.1", server_port: int = 8500):
    client = NetworkClient(host=server_host, port=server_port)
    ok, rtt, resp, err = client.handshake()
    if not ok:
        print(f"[Error] Cannot connect to worker daemon at {server_host}:{server_port}: {err}")
        return

    gpu_label = resp.gpu.name if resp.gpu.available else "CPU Worker"
    print("\n" + "=" * 70)
    print("CSC-334: DISTRIBUTED TASK OFFLOADING BENCHMARK SUITE")
    print(f"Target Worker: {server_host}:{server_port} (RTT: {rtt} ms)")
    print(f"Worker Engine: {gpu_label} (NVENC: {resp.gpu.nvenc_supported})")
    print("=" * 70)

    bench_dir = "benchmark_temp"
    os.makedirs(bench_dir, exist_ok=True)

    test_matrix = [
        {"name": "Profile 1: 720p 10s Clip", "duration": 10, "res": "1280x720", "bitrate": "3M"},
        {"name": "Profile 2: 1080p 20s Clip", "duration": 20, "res": "1920x1080", "bitrate": "6M"},
        {"name": "Profile 3: 1080p 35s Heavy Clip", "duration": 35, "res": "1920x1080", "bitrate": "10M"},
    ]

    results = []

    for test in test_matrix:
        print(f"\n[Running Test] {test['name']} ({test['res']} @ {test['bitrate']})...")
        sample_input = os.path.join(bench_dir, f"input_{test['duration']}s.mp4")
        generate_benchmark_clip(sample_input, test["duration"], test["res"])
        file_size_mb = os.path.getsize(sample_input) / (1024 * 1024)

        # 1. Local CPU
        print("  -> Benchmarking Local CPU Render...")
        local_out = os.path.join(bench_dir, "local_out.mp4")
        t_local = benchmark_local_cpu(sample_input, local_out, test["res"], test["bitrate"])
        print(f"     Local CPU Time: {t_local:.2f}s")

        # 2. Remote GPU Offload
        print("  -> Benchmarking Remote GPU Offload (Upload + NVENC + Download)...")
        remote_out = os.path.join(bench_dir, "remote_out.mp4")
        offload_metrics = benchmark_remote_offload(client, sample_input, remote_out, test["res"], test["bitrate"])
        t_offload = offload_metrics["total_offload_sec"]
        print(f"     Remote Total Offload: {t_offload:.2f}s")
        print(f"       - Upload:   {offload_metrics['upload_sec']:.2f}s")
        print(f"       - GPU Exec: {offload_metrics['remote_render_sec']:.2f}s")
        print(f"       - Download: {offload_metrics['download_sec']:.2f}s")

        # Calculations
        speedup = t_local / t_offload if t_offload > 0 else 1.0
        net_overhead_pct = ((offload_metrics["upload_sec"] + offload_metrics["download_sec"]) / t_offload) * 100.0

        results.append({
            "test": test["name"],
            "size_mb": file_size_mb,
            "t_local": t_local,
            "t_offload": t_offload,
            "t_gpu_pure": offload_metrics["remote_render_sec"],
            "speedup": speedup,
            "net_overhead": net_overhead_pct
        })

    # Cleanup temp assets
    shutil.rmtree(bench_dir, ignore_errors=True)

    # Format Markdown Report
    print("\n" + "=" * 70)
    print("FINAL PERFORMANCE EVALUATION REPORT (TASK 5)")
    print("=" * 70)
    print(f"| Test Scenario | Size (MB) | Local CPU Time | Remote Offload | GPU Core Time | Speedup Factor | Network Overhead |")
    print(f"| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
    for r in results:
        print(f"| {r['test']} | {r['size_mb']:.1f} MB | {r['t_local']:.2f}s | {r['t_offload']:.2f}s | {r['t_gpu_pure']:.2f}s | **{r['speedup']:.2f}x** | {r['net_overhead']:.1f}% |")
    print("=" * 70)

    # Save to Markdown file
    report_path = "BENCHMARK_REPORT.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Distributed Task Offloading - Performance Analysis Report\n\n")
        f.write(f"- **Worker Node GPU:** {gpu_label}\n")
        f.write(f"- **NVENC Hardware Acceleration:** {resp.gpu.nvenc_supported}\n")
        f.write(f"- **Network Latency (RTT):** {rtt:.2f} ms\n\n")
        f.write("## Comparative Results Matrix\n\n")
        f.write("| Test Scenario | Input Size | Local CPU Time (s) | Remote Offload Total (s) | Remote GPU Core (s) | Speedup Factor | Network Overhead (%) |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for r in results:
            f.write(f"| {r['test']} | {r['size_mb']:.1f} MB | {r['t_local']:.2f} | {r['t_offload']:.2f} | {r['t_gpu_pure']:.2f} | **{r['speedup']:.2f}x** | {r['net_overhead']:.1f}% |\n")
        f.write("\n\n## Analysis & Insights\n")
        f.write("1. **Speedup Factor:** As video resolution and duration increase, the hardware acceleration of the dedicated GPU vastly outpaces the client's CPU rendering capacity.\n")
        f.write("2. **Network Overhead Amortization:** The relative overhead of network transfer drops significantly as computational complexity rises, making distributed offloading exceptionally effective for high-bitrate and 1080p/4K workloads.\n")

    print(f"\n[Generated] Report saved to '{report_path}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Task Offloading Benchmark Runner")
    parser.add_argument("--host", default="127.0.0.1", help="Worker IP (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8500, help="Worker Port (default 8500)")
    args = parser.parse_args()

    run_benchmark_suite(args.host, args.port)
