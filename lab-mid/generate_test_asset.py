"""
Generates synthetic high-resolution test video files for benchmarking and evaluation.
No camera or external downloads required!
"""
import argparse
import os
import shutil
import subprocess
import sys


def generate_video(output_path: str = "test_sample_1080p.mp4", duration: int = 15, resolution: str = "1920x1080", fps: int = 30):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("[Error] ffmpeg not found in PATH.")
        sys.exit(1)

    print(f"Generating synthetic {resolution} @ {fps}fps ({duration}s) -> {output_path}...")
    cmd = [
        ffmpeg,
        "-y",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration}:size={resolution}:rate={fps}",
        "-f", "lavfi",
        "-i", f"sine=frequency=1000:duration={duration}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        output_path
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"[Success] Generated '{output_path}' ({size_mb:.2f} MB)")
    else:
        print(f"[Error] Failed to generate test video: {res.stderr}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synthetic Video Generator")
    parser.add_argument("--output", default="test_sample_1080p.mp4", help="Output file path")
    parser.add_argument("--duration", type=int, default=15, help="Duration in seconds")
    parser.add_argument("--res", default="1920x1080", help="Resolution e.g. 1920x1080")
    parser.add_argument("--fps", type=int, default=30, help="Framerate")
    args = parser.parse_args()

    generate_video(args.output, args.duration, args.res, args.fps)

