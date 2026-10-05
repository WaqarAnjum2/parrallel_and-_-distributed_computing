"""
Robust GPU detection using NVML, nvidia-smi, PyTorch, and Windows WMI/CIM.

Gracefully handles hybrid graphics laptops, driver mismatches, and headless environments.
Ensures worker can detect laptop GPUs regardless of library or driver quirks.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import warnings
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("worker")


@dataclass
class GPUInfo:
    """Detected GPU hardware information."""
    available: bool = False
    name: str = "Not detected"
    memory_mb: int = 0
    driver_version: str = ""
    device_count: int = 0


def _detect_via_nvml() -> Optional[GPUInfo]:
    """Tier 1: Detect NVIDIA GPU via pynvml / nvidia-ml-py."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                import nvidia_ml_py as pynvml  # type: ignore[import-untyped]
            except ImportError:
                import pynvml  # type: ignore[import-untyped]

            pynvml.nvmlInit()
            device_count: int = pynvml.nvmlDeviceGetCount()
            if device_count == 0:
                pynvml.nvmlShutdown()
                return None

            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            name: str = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode("utf-8")

            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            memory_mb = int(mem_info.total) // (1024 * 1024)

            driver: str = pynvml.nvmlSystemGetDriverVersion()
            if isinstance(driver, bytes):
                driver = driver.decode("utf-8")

            pynvml.nvmlShutdown()

            return GPUInfo(
                available=True,
                name=name,
                memory_mb=memory_mb,
                driver_version=driver,
                device_count=device_count,
            )
    except Exception as exc:
        logger.debug(f"NVML detection attempt failed: {exc}")
        return None


def _detect_via_nvidia_smi() -> Optional[GPUInfo]:
    """Tier 2: Detect NVIDIA GPU via nvidia-smi command-line utility."""
    candidate_paths = [
        shutil.which("nvidia-smi"),
        r"C:\Windows\System32\nvidia-smi.exe",
        r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
    ]
    for smi_path in candidate_paths:
        if not smi_path or not os.path.exists(smi_path):
            continue
        try:
            res = subprocess.run(
                [
                    smi_path,
                    "--query-gpu=name,memory.total,driver_version",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0 and res.stdout.strip():
                lines = [line.strip() for line in res.stdout.strip().split("\n") if line.strip()]
                if lines:
                    first = [p.strip() for p in lines[0].split(",")]
                    name = first[0] if len(first) > 0 else "NVIDIA GPU"
                    mem = int(float(first[1])) if len(first) > 1 and first[1] else 0
                    drv = first[2] if len(first) > 2 else ""
                    return GPUInfo(
                        available=True,
                        name=name,
                        memory_mb=mem,
                        driver_version=drv,
                        device_count=len(lines),
                    )
        except Exception as exc:
            logger.debug(f"nvidia-smi detection attempt failed: {exc}")
    return None


def _detect_via_torch() -> Optional[GPUInfo]:
    """Tier 3: Detect GPU via PyTorch if installed."""
    try:
        import torch  # type: ignore[import-untyped]
        if torch.cuda.is_available():
            count = torch.cuda.device_count()
            name = torch.cuda.get_device_name(0)
            mem_bytes = torch.cuda.get_device_properties(0).total_memory
            mem_mb = int(mem_bytes) // (1024 * 1024)
            return GPUInfo(
                available=True,
                name=name,
                memory_mb=mem_mb,
                driver_version="CUDA via PyTorch",
                device_count=count,
            )
    except Exception:
        pass
    return None


def _detect_via_windows_wmi() -> Optional[GPUInfo]:
    """Tier 4: Detect discrete or accelerated GPU via Windows CIM/WMI."""
    if os.name != "nt":
        return None
    try:
        ps_cmd = "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion | ConvertTo-Json"
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout)
            controllers = data if isinstance(data, list) else [data]

            # Priority keywords for dedicated GPUs
            priority_keywords = ["nvidia", "geforce", "quadro", "rtx", "gtx", "radeon", "intel(r) arc"]
            for c in controllers:
                name = str(c.get("Name") or "")
                if any(k in name.lower() for k in priority_keywords):
                    ram_bytes = c.get("AdapterRAM") or 0
                    ram_mb = int(ram_bytes) // (1024 * 1024) if ram_bytes else 0
                    driver = str(c.get("DriverVersion") or "")
                    return GPUInfo(
                        available=True,
                        name=name,
                        memory_mb=ram_mb,
                        driver_version=driver,
                        device_count=1,
                    )
    except Exception as exc:
        logger.debug(f"Windows CIM detection failed: {exc}")
    return None


def detect_gpu() -> GPUInfo:
    """
    Multi-tiered hardware GPU detection.

    Evaluates NVML -> nvidia-smi -> PyTorch CUDA -> Windows WMI/CIM.
    Returns GPUInfo with available=False if no GPU is found.
    """
    # 1. Try NVML
    info = _detect_via_nvml()
    if info and info.available:
        logger.info(f"GPU detected via NVML: {info.name} ({info.memory_mb} MB)")
        return info

    # 2. Try nvidia-smi CLI
    info = _detect_via_nvidia_smi()
    if info and info.available:
        logger.info(f"GPU detected via nvidia-smi: {info.name} ({info.memory_mb} MB)")
        return info

    # 3. Try PyTorch CUDA
    info = _detect_via_torch()
    if info and info.available:
        logger.info(f"GPU detected via PyTorch: {info.name} ({info.memory_mb} MB)")
        return info

    # 4. Try Windows CIM/WMI
    info = _detect_via_windows_wmi()
    if info and info.available:
        logger.info(f"GPU detected via Windows CIM: {info.name} ({info.memory_mb} MB)")
        return info

    logger.warning("No hardware GPU detected across all detection layers.")
    return GPUInfo()
