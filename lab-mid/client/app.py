"""
Desktop Client Application - Pro Light + Lava + Obsidian Black UX/UI.
Built with CustomTkinter for Distributed Task Offloading & Remote GPU Rendering.
"""
import asyncio
import os
import subprocess
import sys
import threading
import time
from typing import Optional
from tkinter import filedialog, messagebox

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import customtkinter as ctk

from common.protocol import HandshakeResponse, RenderConfig, format_bytes
from client.client_network import NetworkClient

# Configure Pro Light Mode
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# Design Palette Constants
COLOR_BG = "#F8FAFC"             # Slate-50 main window
COLOR_CARD_BG = "#FFFFFF"        # Pure white card
COLOR_BORDER = "#E2E8F0"         # 1px subtle divider
COLOR_TEXT_PRIMARY = "#0F172A"   # Obsidian Black text
COLOR_TEXT_MUTED = "#64748B"     # Slate-500 secondary text
COLOR_LAVA = "#FF4500"           # Fiery Lava Orange-Red (Primary Brand Accent)
COLOR_LAVA_HOVER = "#D83A00"     # Lava Hover State
COLOR_LAVA_LIGHT = "#FFF2EB"     # Lava Subtle Badge Fill
COLOR_EMERALD = "#10B981"        # Emerald Health / Success
COLOR_TERMINAL_BG = "#0B0F19"    # Dark Obsidian Console Box


class RemoteRenderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Cobalt Studio — Distributed GPU Render Offloader")
        self.geometry("1060x860")
        self.minsize(940, 740)
        self.configure(fg_color=COLOR_BG)

        # Network client
        self.client = NetworkClient(host="127.0.0.1", port=8500)

        # State management
        self.selected_file_path: Optional[str] = None
        self.current_job_id: Optional[str] = None
        self.last_output_path: Optional[str] = None
        self.is_running: bool = False
        self.cancel_requested: bool = False

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Top Header Bar
        header = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
        header.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")

        brand_frame = ctk.CTkFrame(header, fg_color="transparent")
        brand_frame.pack(side="left", padx=16, pady=10)

        ctk.CTkLabel(
            brand_frame,
            text="COBALT DISTRIBUTED",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color=COLOR_LAVA_LIGHT,
            text_color=COLOR_LAVA,
            corner_radius=6,
            padx=8,
            pady=2
        ).pack(anchor="w")

        ctk.CTkLabel(
            brand_frame,
            text="Remote GPU Task Offloader & Studio Editor",
            font=ctk.CTkFont(family="Segoe UI", size=19, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        ).pack(anchor="w")

        info_frame = ctk.CTkFrame(header, fg_color="transparent")
        info_frame.pack(side="right", padx=16, pady=10)

        ctk.CTkLabel(
            info_frame,
            text="CSC-334: Parallel & Distributed Computing",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        ).pack(anchor="e")

        ctk.CTkLabel(
            info_frame,
            text="Peer-to-Peer LAN / Wi-Fi Subnet Offload Daemon",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_TEXT_MUTED
        ).pack(anchor="e")

        # -------------------------------------------------------------
        # 2. NETWORK HANDSHAKE & NODE STATUS CARD
        # -------------------------------------------------------------
        net_card = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
        net_card.grid(row=1, column=0, padx=16, pady=6, sticky="ew")

        ctk.CTkLabel(net_card, text="Node IP:", font=ctk.CTkFont(weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, padx=(16, 4), pady=12)
        self.ip_entry = ctk.CTkEntry(net_card, width=130, fg_color="#F1F5F9", border_color=COLOR_BORDER, text_color=COLOR_TEXT_PRIMARY)
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.grid(row=0, column=1, padx=4, pady=12)

        ctk.CTkLabel(net_card, text="Port:", font=ctk.CTkFont(weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=2, padx=(10, 4), pady=12)
        self.port_entry = ctk.CTkEntry(net_card, width=70, fg_color="#F1F5F9", border_color=COLOR_BORDER, text_color=COLOR_TEXT_PRIMARY)
        self.port_entry.insert(0, "8500")
        self.port_entry.grid(row=0, column=3, padx=4, pady=12)

        self.btn_ping = ctk.CTkButton(
            net_card,
            text="⚡ Ping & Handshake",
            font=ctk.CTkFont(weight="bold"),
            command=self.on_ping_clicked,
            fg_color=COLOR_LAVA,
            hover_color=COLOR_LAVA_HOVER,
            text_color="#FFFFFF",
            width=150,
            height=32
        )
        self.btn_ping.grid(row=0, column=4, padx=12, pady=12)

        self.status_pill = ctk.CTkLabel(
            net_card,
            text="● Node Offline",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        self.status_pill.grid(row=0, column=5, padx=8, pady=12)

        self.gpu_badge = ctk.CTkLabel(
            net_card,
            text="Worker GPU: Not Connected",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        self.gpu_badge.grid(row=0, column=6, padx=(12, 16), pady=12, sticky="e")

        # -------------------------------------------------------------
        # 3. MAIN WORKSPACE (2-COLUMN DUAL PANE)
        # -------------------------------------------------------------
        workspace = ctk.CTkFrame(self, fg_color="transparent")
        workspace.grid(row=2, column=0, padx=16, pady=6, sticky="nsew")
        workspace.grid_columnconfigure(0, weight=4)  # Left Config Column
        workspace.grid_columnconfigure(1, weight=5)  # Right Telemetry/Console Column
        workspace.grid_rowconfigure(0, weight=1)

        # =============================================================
        # LEFT COLUMN: JOB CONFIGURATION & HARDWARE MATRIX
        # =============================================================
        left_col = ctk.CTkFrame(workspace, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
        left_col.grid(row=0, column=0, padx=(0, 8), pady=0, sticky="nsew")
        left_col.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left_col,
            text="1. Input Media Asset",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        ).pack(anchor="w", padx=16, pady=(16, 6))

        # File picker box
        file_box = ctk.CTkFrame(left_col, fg_color="#F8FAFC", corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        file_box.pack(fill="x", padx=16, pady=(0, 10))

        self.file_entry = ctk.CTkEntry(
            file_box,
            placeholder_text="Browse or choose video file (MP4, MKV, MOV)...",
            fg_color="#FFFFFF",
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT_PRIMARY
        )
        self.file_entry.pack(side="left", fill="x", expand=True, padx=(10, 8), pady=10)

        self.btn_browse = ctk.CTkButton(
            file_box,
            text="Browse",
            width=80,
            command=self.on_browse_file,
            fg_color=COLOR_TEXT_PRIMARY,
            hover_color="#334155",
            text_color="#FFFFFF"
        )
        self.btn_browse.pack(side="right", padx=(0, 10), pady=10)

        self.file_meta_lbl = ctk.CTkLabel(
            left_col,
            text="Size: 0 MB | Duration: --:-- | SHA-256: Uncalculated",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED
        )
        self.file_meta_lbl.pack(anchor="w", padx=18, pady=(0, 12))

        # Hardware Encoding Matrix
        ctk.CTkLabel(
            left_col,
            text="2. Hardware Encoding Matrix",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        ).pack(anchor="w", padx=16, pady=(8, 8))

        matrix_frame = ctk.CTkFrame(left_col, fg_color="#F8FAFC", corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        matrix_frame.pack(fill="x", padx=16, pady=(0, 14))

        # Resolution
        ctk.CTkLabel(matrix_frame, text="Resolution Target:", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, padx=12, pady=(10, 2), sticky="w")
        self.res_menu = ctk.CTkOptionMenu(
            matrix_frame,
            values=["Original", "1920x1080 (1080p)", "1280x720 (720p)", "854x480 (480p)"],
            fg_color="#FFFFFF",
            button_color=COLOR_TEXT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
            dropdown_text_color=COLOR_TEXT_PRIMARY
        )
        self.res_menu.set("1920x1080 (1080p)")
        self.res_menu.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="ew")

        # Bitrate
        ctk.CTkLabel(matrix_frame, text="Target Bitrate:", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=1, padx=12, pady=(10, 2), sticky="w")
        self.bitrate_menu = ctk.CTkOptionMenu(
            matrix_frame,
            values=["2M (Low)", "5M (Standard)", "8M (High Quality)", "15M (Production)"],
            fg_color="#FFFFFF",
            button_color=COLOR_TEXT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
            dropdown_text_color=COLOR_TEXT_PRIMARY
        )
        self.bitrate_menu.set("5M (Standard)")
        self.bitrate_menu.grid(row=1, column=1, padx=12, pady=(0, 10), sticky="ew")

        # Preset
        ctk.CTkLabel(matrix_frame, text="Encoder Preset:", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=2, column=0, padx=12, pady=(4, 1), sticky="w")
        self.preset_menu = ctk.CTkOptionMenu(
            matrix_frame,
            values=["p1 (Fastest)", "p4 (Balanced)", "p7 (Highest Quality)"],
            fg_color="#FFFFFF",
            button_color=COLOR_TEXT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
            dropdown_text_color=COLOR_TEXT_PRIMARY
        )
        self.preset_menu.set("p4 (Balanced)")
        self.preset_menu.grid(row=3, column=0, padx=12, pady=(0, 8), sticky="ew")

        # Engine Codec
        ctk.CTkLabel(matrix_frame, text="Execution Engine:", font=ctk.CTkFont(size=11, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=2, column=1, padx=12, pady=(4, 1), sticky="w")
        self.codec_menu = ctk.CTkOptionMenu(
            matrix_frame,
            values=["h264_nvenc (NVIDIA GPU)", "libx264 (CPU Only)"],
            fg_color="#FFFFFF",
            button_color=COLOR_TEXT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
            dropdown_text_color=COLOR_TEXT_PRIMARY
        )
        self.codec_menu.set("h264_nvenc (NVIDIA GPU)")
        self.codec_menu.grid(row=3, column=1, padx=12, pady=(0, 8), sticky="ew")

        # 3. Creative Video Editing Studio
        ctk.CTkLabel(
            left_col,
            text="3. Video Editing Studio",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        ).pack(anchor="w", padx=16, pady=(4, 6))

        edit_frame = ctk.CTkFrame(left_col, fg_color="#F8FAFC", corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        edit_frame.pack(fill="x", padx=16, pady=(0, 10))

        # Trim Start & End
        ctk.CTkLabel(edit_frame, text="Trim Start (sec):", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=0, padx=8, pady=(6, 1), sticky="w")
        self.trim_start_entry = ctk.CTkEntry(edit_frame, width=90, placeholder_text="0.0")
        self.trim_start_entry.insert(0, "0.0")
        self.trim_start_entry.grid(row=1, column=0, padx=8, pady=(0, 6), sticky="w")

        ctk.CTkLabel(edit_frame, text="Trim End (sec):", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=0, column=1, padx=8, pady=(6, 1), sticky="w")
        self.trim_end_entry = ctk.CTkEntry(edit_frame, width=90, placeholder_text="Full")
        self.trim_end_entry.insert(0, "Full")
        self.trim_end_entry.grid(row=1, column=1, padx=8, pady=(0, 6), sticky="w")

        # Color Filter & Speed
        ctk.CTkLabel(edit_frame, text="Color Grading Filter:", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=2, column=0, padx=8, pady=(4, 1), sticky="w")
        self.filter_menu = ctk.CTkOptionMenu(
            edit_frame,
            values=["None (Original)", "Grayscale (B&W)", "Vintage Sepia", "Vignette Focus", "High Contrast", "Invert Negative"],
            fg_color="#FFFFFF",
            button_color=COLOR_TEXT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
            dropdown_text_color=COLOR_TEXT_PRIMARY,
            width=150
        )
        self.filter_menu.set("None (Original)")
        self.filter_menu.grid(row=3, column=0, padx=8, pady=(0, 6), sticky="ew")

        ctk.CTkLabel(edit_frame, text="Playback Speed:", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=2, column=1, padx=8, pady=(4, 1), sticky="w")
        self.speed_menu = ctk.CTkOptionMenu(
            edit_frame,
            values=["1.0x (Normal)", "0.5x (Slow-Mo)", "1.5x (Fast)", "2.0x (Hyperlapse)"],
            fg_color="#FFFFFF",
            button_color=COLOR_TEXT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
            dropdown_text_color=COLOR_TEXT_PRIMARY,
            width=130
        )
        self.speed_menu.set("1.0x (Normal)")
        self.speed_menu.grid(row=3, column=1, padx=8, pady=(0, 6), sticky="ew")

        # Watermark Text & Audio Mode
        ctk.CTkLabel(edit_frame, text="Title / Watermark Text:", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=4, column=0, padx=8, pady=(4, 1), sticky="w")
        self.watermark_entry = ctk.CTkEntry(edit_frame, placeholder_text="e.g. Distributed Project 2026")
        self.watermark_entry.grid(row=5, column=0, padx=8, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(edit_frame, text="Audio Track:", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_PRIMARY).grid(row=4, column=1, padx=8, pady=(4, 1), sticky="w")
        self.audio_menu = ctk.CTkOptionMenu(
            edit_frame,
            values=["Original (100%)", "Boost (+60%)", "Mute (Silent)"],
            fg_color="#FFFFFF",
            button_color=COLOR_TEXT_PRIMARY,
            text_color=COLOR_TEXT_PRIMARY,
            dropdown_text_color=COLOR_TEXT_PRIMARY,
            width=130
        )
        self.audio_menu.set("Original (100%)")
        self.audio_menu.grid(row=5, column=1, padx=8, pady=(0, 8), sticky="ew")

        # Action Buttons Section
        btn_container = ctk.CTkFrame(left_col, fg_color="transparent")
        btn_container.pack(fill="x", padx=16, pady=(10, 16), side="bottom")

        self.btn_submit = ctk.CTkButton(
            btn_container,
            text="🚀 Offload & Render to Remote GPU",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLOR_LAVA,
            hover_color=COLOR_LAVA_HOVER,
            text_color="#FFFFFF",
            height=44,
            corner_radius=8,
            command=self.on_submit_job
        )
        self.btn_submit.pack(fill="x", pady=(0, 8))

        sub_btns = ctk.CTkFrame(btn_container, fg_color="transparent")
        sub_btns.pack(fill="x")

        self.btn_cancel = ctk.CTkButton(
            sub_btns,
            text="Abort Job",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#EF4444",
            hover_color="#DC2626",
            text_color="#FFFFFF",
            height=34,
            state="disabled",
            command=self.on_cancel_job
        )
        self.btn_cancel.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_open_folder = ctk.CTkButton(
            sub_btns,
            text="Open Output Folder",
            font=ctk.CTkFont(size=12),
            fg_color="#F1F5F9",
            hover_color=COLOR_BORDER,
            text_color=COLOR_TEXT_PRIMARY,
            height=34,
            state="disabled",
            command=self.on_open_output_folder
        )
        self.btn_open_folder.pack(side="right", fill="x", expand=True, padx=(6, 0))

        # =============================================================
        # RIGHT COLUMN: TELEMETRY HUD & OBSIDIAN TERMINAL
        # =============================================================
        right_col = ctk.CTkFrame(workspace, fg_color=COLOR_CARD_BG, corner_radius=10, border_width=1, border_color=COLOR_BORDER)
        right_col.grid(row=0, column=1, padx=(8, 0), pady=0, sticky="nsew")
        right_col.grid_columnconfigure(0, weight=1)
        right_col.grid_rowconfigure(3, weight=1)

        # Telemetry Stat Cards
        hud_frame = ctk.CTkFrame(right_col, fg_color="transparent")
        hud_frame.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        hud_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Card 1: FPS
        c1 = ctk.CTkFrame(hud_frame, fg_color="#F8FAFC", corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        c1.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkLabel(c1, text="ENCODE FPS", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(pady=(8, 0))
        self.fps_metric = ctk.CTkLabel(c1, text="0.0", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_PRIMARY)
        self.fps_metric.pack(pady=(0, 8))

        # Card 2: Speed Factor
        c2 = ctk.CTkFrame(hud_frame, fg_color="#F8FAFC", corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        c2.grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkLabel(c2, text="SPEED FACTOR", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(pady=(8, 0))
        self.speed_metric = ctk.CTkLabel(c2, text="0.0x", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_LAVA)
        self.speed_metric.pack(pady=(0, 8))

        # Card 3: Frame Counter
        c3 = ctk.CTkFrame(hud_frame, fg_color="#F8FAFC", corner_radius=8, border_width=1, border_color=COLOR_BORDER)
        c3.grid(row=0, column=2, padx=(4, 0), sticky="ew")
        ctk.CTkLabel(c3, text="FRAMES RENDERED", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLOR_TEXT_MUTED).pack(pady=(8, 0))
        self.frame_metric = ctk.CTkLabel(c3, text="0", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLOR_TEXT_PRIMARY)
        self.frame_metric.pack(pady=(0, 8))

        # Progress bar in Lava styling
        prog_frame = ctk.CTkFrame(right_col, fg_color="transparent")
        prog_frame.grid(row=1, column=0, padx=16, pady=4, sticky="ew")

        bar_sub = ctk.CTkFrame(prog_frame, fg_color="transparent")
        bar_sub.pack(fill="x")

        self.progress_bar = ctk.CTkProgressBar(bar_sub, progress_color=COLOR_LAVA, fg_color="#E2E8F0", height=14)
        self.progress_bar.set(0.0)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 12))

        self.pct_label = ctk.CTkLabel(bar_sub, text="0.0%", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_LAVA, width=55)
        self.pct_label.pack(side="right")

        self.status_detail = ctk.CTkLabel(
            prog_frame,
            text="Status: Ready for submission",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED
        )
        self.status_detail.pack(anchor="w", pady=(4, 6))

        # Obsidian Dark Terminal
        ctk.CTkLabel(
            right_col,
            text="Live Remote Worker Daemon Telemetry Stream",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT_PRIMARY
        ).grid(row=2, column=0, padx=16, pady=(6, 2), sticky="w")

        term_card = ctk.CTkFrame(right_col, fg_color=COLOR_TERMINAL_BG, corner_radius=8)
        term_card.grid(row=3, column=0, padx=16, pady=(0, 16), sticky="nsew")
        term_card.grid_columnconfigure(0, weight=1)
        term_card.grid_rowconfigure(0, weight=1)

        self.terminal = ctk.CTkTextbox(
            term_card,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=COLOR_TERMINAL_BG,
            text_color="#F1F5F9",
            activate_scrollbars=True
        )
        self.terminal.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

    # -------------------------------------------------------------
    # LOGGING & ACTIONS
    # -------------------------------------------------------------
    def log(self, text: str):
        """Append log line to embedded obsidian terminal."""
        def _append():
            self.terminal.insert("end", text + "\n")
            self.terminal.see("end")
        self.after(0, _append)

    def on_browse_file(self):
        filetypes = [
            ("Video Files", "*.mp4 *.mkv *.avi *.mov *.wmv *.flv"),
            ("All Files", "*.*")
        ]
        chosen = filedialog.askopenfilename(title="Select Video to Transcode", filetypes=filetypes)
        if chosen:
            self.selected_file_path = chosen
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, chosen)
            sz = os.path.getsize(chosen)
            self.file_meta_lbl.configure(
                text=f"Size: {format_bytes(sz)} | Ready | Checksum computed at transmission"
            )

    def on_ping_clicked(self):
        host = self.ip_entry.get().strip()
        port = int(self.port_entry.get().strip() or "8500")
        self.client = NetworkClient(host=host, port=port)

        self.status_pill.configure(text="● Connecting...", text_color="#F59E0B")
        self.log(f"[Network Handshake] Pinging worker node at {host}:{port}...")

        def _worker():
            success, rtt, resp, err = self.client.handshake()
            if success and resp:
                def _update():
                    self.status_pill.configure(text=f"● Online ({rtt} ms)", text_color=COLOR_EMERALD)
                    gpu_name = resp.gpu.name if resp.gpu.available else "No GPU"
                    vram_mb = f"{resp.gpu.vram_total_mb}MB" if resp.gpu.available else "N/A"
                    nvenc_badge = "NVENC Enabled" if resp.gpu.nvenc_supported else "CPU Mode"
                    self.gpu_badge.configure(
                        text=f"Worker: {gpu_name} ({vram_mb}) | {nvenc_badge}",
                        text_color=COLOR_LAVA
                    )
                    self.log(f"[Handshake Verified] Node: {resp.worker_id} | RTT: {rtt}ms | GPU: {gpu_name} | VRAM: {vram_mb}")
                self.after(0, _update)
            else:
                def _fail():
                    self.status_pill.configure(text="● Offline", text_color="#EF4444")
                    self.gpu_badge.configure(text="Worker: Unreachable", text_color="#EF4444")
                    self.log(f"[Handshake Failed] {err}")
                self.after(0, _fail)

        threading.Thread(target=_worker, daemon=True).start()

    def on_submit_job(self):
        if not self.selected_file_path or not os.path.exists(self.selected_file_path):
            messagebox.showerror("Error", "Please select a valid video asset first.")
            return

        self.is_running = True
        self.cancel_requested = False
        self.btn_submit.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        self.btn_open_folder.configure(state="disabled")
        self.progress_bar.set(0.0)
        self.pct_label.configure(text="0.0%")
        self.fps_metric.configure(text="0.0")
        self.speed_metric.configure(text="0.0x")
        self.frame_metric.configure(text="0")
        self.status_detail.configure(text="Status: Preparing upload pipeline...")

        # Parse config parameters
        codec_choice = "h264_nvenc" if "NVENC" in self.codec_menu.get() else "libx264"
        raw_res = self.res_menu.get().split()[0]
        raw_bitrate = self.bitrate_menu.get().split()[0]
        raw_preset = self.preset_menu.get().split()[0]

        # Parse Video Editing Parameters
        trim_s = None
        try:
            val_s = float(self.trim_start_entry.get().strip())
            if val_s > 0:
                trim_s = val_s
        except ValueError:
            pass

        trim_e = None
        try:
            val_e = float(self.trim_end_entry.get().strip())
            if val_e > 0:
                trim_e = val_e
        except ValueError:
            pass

        speed_val = 1.0
        try:
            speed_val = float(self.speed_menu.get().split("x")[0])
        except ValueError:
            pass

        wm_text = self.watermark_entry.get().strip()
        audio_choice = self.audio_menu.get().split()[0]

        config = RenderConfig(
            resolution=raw_res,
            bitrate=raw_bitrate,
            preset=raw_preset,
            codec=codec_choice,
            trim_start=trim_s,
            trim_end=trim_e,
            filter_effect=self.filter_menu.get(),
            playback_speed=speed_val,
            watermark_text=wm_text if wm_text else None,
            audio_mode=audio_choice
        )

        threading.Thread(target=self._run_pipeline, args=(config,), daemon=True).start()

    def _run_pipeline(self, config: RenderConfig):
        t0 = time.time()
        self.log("\n=======================================================")
        self.log(f"[Pipeline Started] Offloading {os.path.basename(self.selected_file_path)}")

        # 1. Handshake verification
        ok, rtt, _, err = self.client.handshake()
        if not ok:
            self.log(f"[Aborted] Remote daemon is unreachable: {err}")
            self._finish_job(False)
            return

        # 2. Upload asset with SHA-256 verification
        self.log("[Upload Stage] Generating SHA-256 checksum and streaming file to worker node...")
        def _upload_cb(pct, msg):
            self.after(0, lambda: self.status_detail.configure(text=f"Status: {msg}"))

        ok, job_id, in_sha256, err = self.client.upload_file(self.selected_file_path, _upload_cb)
        if not ok:
            self.log(f"[Upload Failure] {err}")
            self._finish_job(False)
            return

        self.current_job_id = job_id
        config.input_sha256 = in_sha256
        upload_time = time.time() - t0
        self.log(f"[Upload Success] Asset received by worker in {upload_time:.2f}s (Job ID: {job_id})")

        # 3. Start remote render
        self.log(f"[Execution Stage] Initiating FFmpeg on remote worker ({config.codec}, {config.resolution}, {config.bitrate})...")
        ok, err = self.client.start_job(job_id, config)
        if not ok:
            self.log(f"[Execution Failure] {err}")
            self._finish_job(False)
            return

        # 4. Stream live progress via WebSocket
        self.log("[Stream Stage] Connected to worker WebSocket. Streaming live telemetry...")
        def _prog_cb(pct: float, fps: float, spd: str, msg: str):
            def _update():
                self.progress_bar.set(pct / 100.0)
                self.pct_label.configure(text=f"{pct:.1f}%")
                self.fps_metric.configure(text=f"{fps:.1f}")
                self.speed_metric.configure(text=f"{spd}")
                self.status_detail.configure(text=f"Status: Rendering on GPU ({pct:.1f}%)")
            self.after(0, _update)

        def _log_cb(line: str):
            self.log(line)

        success, out_sha256 = asyncio.run(
            self.client.listen_progress_ws(job_id, _prog_cb, _log_cb, lambda: self.cancel_requested)
        )

        if not success:
            self.log("[Pipeline Terminated] Remote job failed or was aborted.")
            self._finish_job(False)
            return

        # 5. Download rendered output
        self.log("[Download Stage] Remote transcode finished. Downloading verified rendered stream...")
        output_dir = os.path.join(os.path.dirname(self.selected_file_path), "rendered_outputs")
        os.makedirs(output_dir, exist_ok=True)
        dest_path = os.path.join(output_dir, f"rendered_{job_id}.mp4")

        def _dl_cb(pct, msg):
            self.after(0, lambda: self.status_detail.configure(text=f"Status: {msg}"))

        dl_ok, dl_err = self.client.download_file(job_id, dest_path, out_sha256, _dl_cb)
        total_time = time.time() - t0

        if dl_ok:
            self.last_output_path = dest_path
            self.log("\n=======================================================")
            self.log(f"[SUCCESS] Distributed pipeline completed in {total_time:.2f}s!")
            self.log(f"[Integrity Verified] SHA-256: {out_sha256}")
            self.log(f"[Saved Location] {dest_path}")
            self._finish_job(True, dest_path)
        else:
            self.log(f"[Download Error] {dl_err}")
            self._finish_job(False)

    def on_cancel_job(self):
        if self.current_job_id and self.is_running:
            self.cancel_requested = True
            self.log("[Signal] Abort requested by user. Terminating remote subprocess...")
            self.client.cancel_job(self.current_job_id)
            self._finish_job(False)

    def on_open_output_folder(self):
        if self.last_output_path and os.path.exists(self.last_output_path):
            folder = os.path.dirname(self.last_output_path)
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])

    def _finish_job(self, success: bool, output_path: str = ""):
        def _reset():
            self.is_running = False
            self.btn_submit.configure(state="normal")
            self.btn_cancel.configure(state="disabled")
            if success:
                self.btn_open_folder.configure(state="normal")
                self.progress_bar.set(1.0)
                self.pct_label.configure(text="100.0%")
                self.status_detail.configure(text="Status: Completed & Verified OK")
                messagebox.showinfo("Job Completed", f"Video rendered and downloaded successfully!\n\nFile:\n{output_path}")
            else:
                self.status_detail.configure(text="Status: Job Aborted / Failed")
        self.after(0, _reset)


if __name__ == "__main__":
    app = RemoteRenderApp()
    app.mainloop()
