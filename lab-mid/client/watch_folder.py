"""
Universal Hot Folder Watcher for Task Offloading.
Allows ANY video editor (Clipchamp, CapCut, Premiere, DaVinci) to automatically
offload rendering to the second GPU laptop simply by exporting or dropping videos into a folder.
"""
import asyncio
import os
import shutil
import sys
import time
from typing import Callable, Optional
import requests

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.protocol import RenderConfig, compute_sha256
from client.client_network import NetworkClient


def is_file_fully_written(file_path: str, wait_seconds: float = 2.0) -> bool:
    """
    Edge-Case Handler: Checks if a video exported by Clipchamp/Premiere has finished writing.
    Returns True only when file size is stable and file is not locked by another process.
    """
    if not os.path.exists(file_path):
        return False
    try:
        size1 = os.path.getsize(file_path)
        time.sleep(wait_seconds)
        size2 = os.path.getsize(file_path)
        if size1 != size2 or size1 == 0:
            return False

        # Attempt to open exclusively to ensure no editor is currently holding write lock
        with open(file_path, "rb"):
            pass
        return True
    except (IOError, OSError, PermissionError):
        return False


class HotFolderWatcher:
    def __init__(
        self,
        watch_dir: str = "exports_to_render",
        output_dir: str = "completed_renders",
        server_host: str = "192.168.1.100",
        server_port: int = 8500,
        render_config: Optional[RenderConfig] = None
    ):
        self.watch_dir = os.path.abspath(watch_dir)
        self.output_dir = os.path.abspath(output_dir)
        self.processed_dir = os.path.join(self.watch_dir, "processed")
        os.makedirs(self.watch_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)

        self.client = NetworkClient(host=server_host, port=server_port)
        self.render_config = render_config or RenderConfig(
            resolution="1920x1080",
            bitrate="6M",
            preset="p4",
            codec="h264_nvenc"
        )
        self.is_running = False

    def start_watching(self, log_cb: Optional[Callable[[str], None]] = None):
        """Continuously watch for exported files and auto-offload them."""
        self.is_running = True
        logger = log_cb or print
        logger(f"[HotFolder] Watching '{self.watch_dir}' for exported videos...")
        logger(f"[HotFolder] Target Worker Node: {self.client.base_url}")

        valid_exts = {".mp4", ".mov", ".mkv", ".avi", ".wmv"}

        while self.is_running:
            try:
                for entry in os.listdir(self.watch_dir):
                    if not self.is_running:
                        break

                    full_path = os.path.join(self.watch_dir, entry)
                    if os.path.isdir(full_path) or entry == "processed":
                        continue

                    ext = os.path.splitext(entry)[1].lower()
                    if ext not in valid_exts:
                        continue

                    logger(f"\n[Detected File] '{entry}' found. Checking write completion...")
                    if not is_file_fully_written(full_path, wait_seconds=1.5):
                        logger(f"[Busy] '{entry}' is still being exported by video editor. Waiting...")
                        time.sleep(2.0)
                        continue

                    logger(f"[Ready] '{entry}' export complete! Offloading to second GPU laptop...")
                    self._process_file(full_path, entry, logger)

                time.sleep(2.0)
            except Exception as e:
                logger(f"[Watch Error] {e}")
                time.sleep(3.0)

    def _process_file(self, full_path: str, filename: str, logger: Callable[[str], None]):
        """Upload, render on remote GPU, download finished file, and archive original."""
        t0 = time.time()
        # 1. Handshake
        ok, rtt, resp, err = self.client.handshake()
        if not ok:
            logger(f"[Error] Second laptop unreachable ({err}). Will retry in next cycle.")
            return

        # 2. Upload with SHA-256 validation
        logger(f"[Upload] Streaming '{filename}' across CAT6 cable to {resp.gpu.name}...")
        ok, job_id, in_sha, err = self.client.upload_file(full_path)
        if not ok:
            logger(f"[Upload Failed] {err}")
            return

        # 3. Trigger remote execution
        cfg = self.render_config.model_copy()
        cfg.input_sha256 = in_sha
        logger(f"[Execution] Starting render job {job_id} ({cfg.resolution}, {cfg.codec})...")
        ok, err = self.client.start_job(job_id, cfg)
        if not ok:
            logger(f"[Job Start Failed] {err}")
            return

        # 4. Stream progress
        def _prog(pct, fps, spd, msg):
            if int(pct) % 25 == 0:
                logger(f"  -> Rendering Progress: {pct:.1f}% (FPS: {fps:.1f}, Speed: {spd})")

        success, out_sha = asyncio.run(
            self.client.listen_progress_ws(job_id, _prog, lambda l: None, lambda: not self.is_running)
        )
        if not success:
            logger(f"[Failure] Render failed on remote GPU.")
            return

        # 5. Download rendered output
        out_name = f"rendered_{os.path.splitext(filename)[0]}_{job_id}.mp4"
        dest_path = os.path.join(self.output_dir, out_name)
        logger(f"[Download] Downloading finished video to '{dest_path}'...")
        dl_ok, dl_err = self.client.download_file(job_id, dest_path, out_sha)

        if dl_ok:
            total_sec = time.time() - t0
            logger(f"[SUCCESS] Finished in {total_sec:.2f}s! Saved: {dest_path}")
            # Move source file to processed folder
            archived_path = os.path.join(self.processed_dir, filename)
            shutil.move(full_path, archived_path)
        else:
            logger(f"[Download Error] {dl_err}")

    def stop(self):
        self.is_running = False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Universal Hot Folder Offloader")
    parser.add_argument("--watch", default="exports_to_render", help="Folder to watch")
    parser.add_argument("--host", default="192.168.1.100", help="Second laptop IP")
    parser.add_argument("--port", type=int, default=8500, help="Port")
    args = parser.parse_args()

    watcher = HotFolderWatcher(watch_dir=args.watch, server_host=args.host, server_port=args.port)
    try:
        watcher.start_watching()
    except KeyboardInterrupt:
        watcher.stop()
        print("\nWatcher stopped.")
