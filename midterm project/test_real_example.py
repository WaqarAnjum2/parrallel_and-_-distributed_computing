"""
Quick CLI verification script to run a real video transcode job against the local worker node.
Demonstrates the full distributed offload pipeline in the terminal.
"""

import sys
import time
from pathlib import Path

from client.config import load_config
from client.network.api_client import APIClient
from client.network.transfer import upload_file, download_file
from client.services.checksum import compute_sha256
from client.services.metadata import probe_video
from shared.schemas import JobCreateRequest


def main() -> None:
    video_path = Path("demo_real_test.mp4")
    if not video_path.exists():
        video_path = Path("sample_video.mp4")
    
    if not video_path.exists():
        print(f"[!] Error: Neither demo_real_test.mp4 nor sample_video.mp4 found.")
        sys.exit(1)

    print("=======================================================")
    print(" 🚀 REAL EXAMPLE: DISTRIBUTED GPU OFFLOADING TEST")
    print("=======================================================")
    print(f" Source Video:  {video_path.resolve()}")
    print(f" File Size:     {video_path.stat().st_size / (1024*1024):.2f} MB")

    config = load_config()
    api = APIClient(config)

    # 1. Health check & hardware telemetry
    print("\n[1/5] Checking Worker Hardware Telemetry...")
    try:
        health = api.health()
        info = api.worker_info()
        print(f"      Node Status:   ONLINE")
        print(f"      Host / OS:     {info.hostname} ({info.platform})")
        print(f"      GPU:           {info.gpu} ({info.gpu_memory_mb} MB VRAM)")
        print(f"      Encoders:      {', '.join(info.encoders)}")
    except Exception as err:
        print(f"[!] Cannot reach worker at {config.base_url}: {err}")
        print("    Ensure worker node is running with: python worker/main.py")
        sys.exit(1)

    # 2. Extract metadata & compute SHA-256
    print("\n[2/5] Inspecting Video & Generating Checksum...")
    meta = probe_video(str(video_path))
    sha256 = compute_sha256(str(video_path))
    res_str = meta.resolution if meta else "1920x1080"
    dur_str = f"{meta.duration:.2f}s" if meta else "10.00s"
    codec_str = meta.codec if meta else "h264"
    print(f"      Resolution:    {res_str}")
    print(f"      Duration:      {dur_str}")
    print(f"      Input Codec:   {codec_str}")
    print(f"      SHA-256:       {sha256[:16]}...{sha256[-8:]}")

    # 3. Create job
    print("\n[3/5] Registering Offload Job with Worker...")
    req = JobCreateRequest(
        filename=video_path.name,
        size=video_path.stat().st_size,
        sha256=sha256,
        codec="h264",
        resolution="1280x720",
        bitrate="3M",
        preset="p4",
    )
    job_resp = api.create_job(req)
    job_id = job_resp.job_id
    print(f"      Assigned Job ID: {job_id}")

    # 4. Upload video
    print("\n[4/5] Streaming Video Upload to Worker...")
    t_up_start = time.perf_counter()
    upload_file(config, job_id, str(video_path.resolve()))
    t_upload = time.perf_counter() - t_up_start
    file_size_mb = video_path.stat().st_size / (1024 * 1024)
    speed_mb = (file_size_mb / t_upload) if t_upload > 0 else 0
    print(f"      Upload Finished in {t_upload:.2f}s (Speed: {speed_mb:.1f} MB/s)")

    # 5. Monitor GPU transcoding
    print("\n[5/5] Monitoring Remote GPU Hardware Transcode...")
    while True:
        status_resp = api.get_job_status(job_id)
        current_state = status_resp.status.value if hasattr(status_resp.status, "value") else str(status_resp.status)
        progress = status_resp.progress
        fps = status_resp.fps
        speed = status_resp.speed
        
        sys.stdout.write(f"\r      State: {current_state:<12} | Progress: {progress:>3}% | Speed: {fps:.0f} FPS ({speed})")
        sys.stdout.flush()

        if current_state in ("COMPLETED", "FAILED", "CANCELLED"):
            print()
            break
        time.sleep(0.3)

    if current_state != "COMPLETED":
        print(f"[!] Job ended with state: {current_state}. Error: {status_resp.error_message}")
        sys.exit(1)

    t_gpu = status_resp.elapsed_seconds

    # 6. Download encoded result
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    out_file = output_dir / f"{job_id}_output.mp4"
    print(f"\n[*] Downloading Encoded Stream -> {out_file}...")
    t_down_start = time.perf_counter()
    download_file(config, job_id, str(out_file))
    t_download = time.perf_counter() - t_down_start

    t_total = t_upload + t_gpu + t_download
    overhead_pct = ((t_upload + t_download) / t_total) * 100 if t_total > 0 else 0

    print("\n=======================================================")
    print(" 🏁 DEMO RUN SUCCESSFUL — TELEMETRY METRICS")
    print("=======================================================")
    print(f" Output Video File:       {out_file.resolve()}")
    print(f" Output File Size:        {out_file.stat().st_size / (1024*1024):.2f} MB")
    print(f" Upload Time (T_upload):  {t_upload:.2f} s")
    print(f" GPU Encode Time (T_gpu): {t_gpu:.2f} s")
    print(f" Download Time (T_down):  {t_download:.2f} s")
    print(f" Total Remote Time:       {t_total:.2f} s")
    print(f" Network Overhead:        {overhead_pct:.1f} %")
    print("=======================================================\n")


if __name__ == "__main__":
    main()
