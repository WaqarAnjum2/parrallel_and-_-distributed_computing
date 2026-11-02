"""
Visual GPU Worker Node Application for Laptop 2.
Runs the background FastAPI daemon while displaying live visual video preview,
GPU VRAM metrics, and real-time transcode telemetry on the second laptop's screen.
"""
import asyncio
import os
import sys
import threading
import time
from typing import Optional
from PIL import Image
import customtkinter as ctk
import uvicorn

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.protocol import format_bytes
from server.daemon import app, queue_mgr

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

COLOR_BG = "#0A0E1A"             # Dark Cobalt 950
COLOR_CARD = "#111629"           # Cobalt 900
COLOR_BORDER = "#1E293B"         # Border
COLOR_TEXT_WHITE = "#F8FAFC"     # Primary text
COLOR_TEXT_MUTED = "#94A3B8"     # Muted text
COLOR_LAVA = "#FF4500"           # Lava Orange
COLOR_EMERALD = "#10B981"        # Emerald Active
COLOR_TERMINAL_BG = "#050811"    # Terminal black


class WorkerNodeApp(ctk.CTk):
    def __init__(self, port: int = 8500):
        super().__init__()

        self.port = port
        self.title("Cobalt GPU Worker Node — Remote Rendering Daemon")
        self.geometry("980x780")
        self.minsize(850, 680)
        self.configure(fg_color=COLOR_BG)

        # Wire task queue event listener to GUI
        queue_mgr.event_listener = self._on_server_event

        self._build_ui()
        self._start_server_thread()
        self._start_telemetry_loop()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. Top Header Card
        header = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
        header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")

        brand_box = ctk.CTkFrame(header, fg_color="transparent")
        brand_box.pack(side="left", padx=16, pady=12)

        tag = ctk.CTkLabel(
            brand_box,
            text="COBALT REMOTE GPU WORKER NODE",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#2A1608",
            text_color=COLOR_LAVA,
            corner_radius=4,
            padx=8,
            pady=2
        )
        tag.pack(anchor="w")

        title = ctk.CTkLabel(
            brand_box,
            text="Headless GPU Daemon & Visual Monitor",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLOR_TEXT_WHITE
        )
        title.pack(anchor="w")

        info_box = ctk.CTkFrame(header, fg_color="transparent")
        info_box.pack(side="right", padx=16, pady=12)

        self.server_status_badge = ctk.CTkLabel(
            info_box,
            text=f"● LISTENING ON PORT {self.port}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_EMERALD
        )
        self.server_status_badge.pack(anchor="e")

        self.ip_display = ctk.CTkLabel(
            info_box,
            text="Ready for incoming jobs from Client Laptop",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED
        )
        self.ip_display.pack(anchor="e")

        # 2. Hardware Specs & VRAM Bar
        gpu_info = queue_mgr.engine.get_gpu_status()
        hw_card = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
        hw_card.grid(row=1, column=0, padx=16, pady=6, sticky="ew")
        hw_card.grid_columnconfigure((0, 1, 2), weight=1)

        # Col 0: GPU Name
        c0 = ctk.CTkFrame(hw_card, fg_color="transparent")
        c0.grid(row=0, column=0, padx=16, pady=10, sticky="w")
        ctk.CTkLabel(c0, text="DEDICATED GPU HARDWARE", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(anchor="w")
        gpu_label = gpu_info.name if gpu_info.available else "CPU Execution Mode"
        self.gpu_lbl = ctk.CTkLabel(c0, text=gpu_label, font=ctk.CTkFont(size=15, weight="bold"), text_color="#3B5BFF")
        self.gpu_lbl.pack(anchor="w")

        # Col 1: VRAM Meter
        c1 = ctk.CTkFrame(hw_card, fg_color="transparent")
        c1.grid(row=0, column=1, padx=16, pady=10, sticky="ew")
        ctk.CTkLabel(c1, text="ACTIVE GPU VRAM USAGE", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(anchor="w")
        self.vram_lbl = ctk.CTkLabel(c1, text=f"{gpu_info.vram_used_mb} MB / {gpu_info.vram_total_mb} MB", font=ctk.CTkFont(size=13, weight="bold"), text_color=COLOR_TEXT_WHITE)
        self.vram_lbl.pack(anchor="w")
        self.vram_bar = ctk.CTkProgressBar(c1, progress_color=COLOR_LAVA, fg_color="#1E293B", height=8)
        self.vram_bar.set(0.1)
        self.vram_bar.pack(fill="x", pady=(4, 0))

        # Col 2: Engine Capability
        c2 = ctk.CTkFrame(hw_card, fg_color="transparent")
        c2.grid(row=0, column=2, padx=16, pady=10, sticky="e")
        ctk.CTkLabel(c2, text="HARDWARE ACCELERATION", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(anchor="e")
        nv_text = "NVIDIA NVENC ACTIVE" if gpu_info.nvenc_supported else "CPU / MFT ENGINE"
        self.nv_lbl = ctk.CTkLabel(c2, text=nv_text, font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_EMERALD)
        self.nv_lbl.pack(anchor="e")

        # 3. Main Workspace: Live Visual Preview Box + Live Telemetry Terminal
        workspace = ctk.CTkFrame(self, fg_color="transparent")
        workspace.grid(row=2, column=0, padx=16, pady=6, sticky="nsew")
        workspace.grid_columnconfigure(0, weight=5)  # Left: Visual Frame Preview
        workspace.grid_columnconfigure(1, weight=5)  # Right: Live Terminal
        workspace.grid_rowconfigure(0, weight=1)

        # ----------------- Visual Frame Preview Box -----------------
        preview_card = ctk.CTkFrame(workspace, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
        preview_card.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="nsew")
        preview_card.grid_columnconfigure(0, weight=1)
        preview_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            preview_card,
            text="Live Video Visual Frame Monitor",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_TEXT_WHITE
        ).grid(row=0, column=0, padx=16, pady=(12, 6), sticky="w")

        # Container for preview image
        self.preview_container = ctk.CTkFrame(preview_card, fg_color="#060913", corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        self.preview_container.grid(row=1, column=0, padx=16, pady=(0, 10), sticky="nsew")

        self.preview_image_label = ctk.CTkLabel(
            self.preview_container,
            text="🎬 [ Live Visual Display ]\n\nWaiting for video transmission from Client Laptop...\nWhen a job arrives, actual frames appear here!",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_MUTED
        )
        self.preview_image_label.pack(expand=True, fill="both", padx=10, pady=10)

        # Active Job Info & Progress
        job_info_box = ctk.CTkFrame(preview_card, fg_color="transparent")
        job_info_box.grid(row=2, column=0, padx=16, pady=(0, 12), sticky="ew")

        self.active_job_label = ctk.CTkLabel(
            job_info_box,
            text="Current Job: IDLE | Ready for tasks",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_LAVA
        )
        self.active_job_label.pack(anchor="w")

        prog_row = ctk.CTkFrame(job_info_box, fg_color="transparent")
        prog_row.pack(fill="x", pady=(4, 2))

        self.job_progress_bar = ctk.CTkProgressBar(prog_row, progress_color=COLOR_LAVA, fg_color="#1E293B", height=12)
        self.job_progress_bar.set(0.0)
        self.job_progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.job_pct_lbl = ctk.CTkLabel(prog_row, text="0.0%", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_LAVA, width=50)
        self.job_pct_lbl.pack(side="right")

        self.telemetry_stat_lbl = ctk.CTkLabel(
            job_info_box,
            text="Telemetry: Speed: 0x | FPS: 0.0 | Frames: 0",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED
        )
        self.telemetry_stat_lbl.pack(anchor="w")

        # ----------------- Right: Live Terminal Stream -----------------
        term_card = ctk.CTkFrame(workspace, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
        term_card.grid(row=0, column=1, padx=(8, 0), pady=0, sticky="nsew")
        term_card.grid_columnconfigure(0, weight=1)
        term_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            term_card,
            text="Daemon Terminal & Hardware Execution Logs",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_TEXT_WHITE
        ).grid(row=0, column=0, padx=16, pady=(12, 6), sticky="w")

        self.terminal = ctk.CTkTextbox(
            term_card,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=COLOR_TERMINAL_BG,
            text_color="#E2E8F0",
            activate_scrollbars=True
        )
        self.terminal.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="nsew")

    def log(self, text: str):
        """Append log line to terminal."""
        def _append():
            self.terminal.insert("end", text + "\n")
            self.terminal.see("end")
        self.after(0, _append)

    def _on_server_event(self, event_type: str, data: dict):
        """Receive real-time notifications from task queue and update Laptop 2's screen."""
        if event_type == "job_started":
            job_id = data.get("job_id", "")
            self.after(0, lambda: self.active_job_label.configure(
                text=f"Active Job: {job_id} | Rendering on GTX 1050...",
                text_color=COLOR_LAVA
            ))
            self.log(f"\n[JOB RECEIVED] Processing Job {job_id} on local NVIDIA GPU...")

        elif event_type == "job_preview":
            prev_path = data.get("preview_path", "")
            if prev_path and os.path.exists(prev_path):
                self._update_preview_image(prev_path)

        elif event_type == "job_progress":
            pct = data.get("percent", 0.0)
            frame = data.get("frame", 0)
            fps = data.get("fps", 0.0)
            spd = data.get("speed", "0x")
            def _update():
                self.job_progress_bar.set(pct / 100.0)
                self.job_pct_lbl.configure(text=f"{pct:.1f}%")
                self.telemetry_stat_lbl.configure(text=f"Telemetry: Speed: {spd} | FPS: {fps:.1f} | Frame: {frame}")
            self.after(0, _update)

        elif event_type == "job_completed":
            job_id = data.get("job_id", "")
            elapsed = data.get("elapsed", 0.0)
            def _complete():
                self.active_job_label.configure(
                    text=f"Job {job_id} COMPLETED ({elapsed:.2f}s) -> Returning to Laptop 1!",
                    text_color=COLOR_EMERALD
                )
                self.job_progress_bar.set(1.0)
                self.job_pct_lbl.configure(text="100.0%")
            self.after(0, _complete)
            self.log(f"[SUCCESS] Job {job_id} finished in {elapsed:.2f}s. Streamed back to client.")

    def _update_preview_image(self, image_path: str):
        """Load and display preview image frame on Laptop 2's screen."""
        try:
            pil_img = Image.open(image_path)
            # Resize keeping aspect ratio
            w, h = pil_img.size
            target_w = 400
            target_h = int((h / w) * target_w) if w > 0 else 225
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(target_w, target_h))
            def _set():
                self.preview_image_label.configure(image=ctk_img, text="")
            self.after(0, _set)
        except Exception as e:
            self.log(f"[Preview Error] Could not render frame: {e}")

    def _start_server_thread(self):
        """Launch FastAPI daemon in background thread."""
        def _run():
            self.log(f"[Daemon Boot] Initializing FastAPI on http://0.0.0.0:{self.port}...")
            uvicorn.run(app, host="0.0.0.0", port=self.port, log_level="warning")

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def _start_telemetry_loop(self):
        """Periodically refresh VRAM and GPU metrics."""
        def _loop():
            while True:
                fresh = queue_mgr.engine.get_gpu_status()
                if fresh.available and fresh.vram_total_mb > 0:
                    ratio = fresh.vram_used_mb / fresh.vram_total_mb
                    def _gui():
                        self.vram_lbl.configure(text=f"{fresh.vram_used_mb} MB / {fresh.vram_total_mb} MB")
                        self.vram_bar.set(ratio)
                    self.after(0, _gui)
                time.sleep(2.0)

        threading.Thread(target=_loop, daemon=True).start()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cobalt GPU Worker Node GUI")
    parser.add_argument("--port", type=int, default=8500, help="Port (default: 8500)")
    args = parser.parse_args()

    app_gui = WorkerNodeApp(port=args.port)
    app_gui.mainloop()
