"""
NVIDIA GPU detection using pynvml.

Gracefully handles missing GPU / drivers — the worker can still serve
CPU-only info when no GPU is available.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("worker")


@dataclass
class GPUInfo:
    """Detected GPU hardware information."""
    available: bool = False
    name: str = "Not detected"
    memory_mb: int = 0
    driver_version: str = ""
    device_count: int = 0


def detect_gpu() -> GPUInfo:
    """
    Attempt to detect an NVIDIA GPU via pynvml.

    Returns GPUInfo with available=False if pynvml is missing or
    no NVIDIA GPU is installed.
    """
    try:
        import pynvml  # type: ignore[import-untyped]

        pynvml.nvmlInit()
        device_count: int = pynvml.nvmlDeviceGetCount()
        if device_count == 0:
            pynvml.nvmlShutdown()
            logger.warning("pynvml initialised but no GPU devices found")
            return GPUInfo()

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

        info = GPUInfo(
            available=True,
            name=name,
            memory_mb=memory_mb,
            driver_version=driver,
            device_count=device_count,
        )
        logger.info(f"GPU detected: {info.name} ({info.memory_mb} MB)")
        return info

    except ImportError:
        logger.warning("pynvml not installed — GPU detection unavailable")
        return GPUInfo()

    except Exception as exc:
        logger.warning(f"GPU detection failed: {exc}")
        return GPUInfo()
