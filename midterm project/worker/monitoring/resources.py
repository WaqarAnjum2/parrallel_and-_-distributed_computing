"""
Worker resource monitoring — CPU, RAM, and GPU metrics.

Uses psutil for CPU/RAM and pynvml for GPU when available.
Never invents values when a metric source is unavailable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import psutil

logger = logging.getLogger("worker")


@dataclass
class ResourceSnapshot:
    """Point-in-time resource utilization snapshot."""
    cpu_percent: float = 0.0
    ram_used_mb: float = 0.0
    ram_total_mb: float = 0.0
    gpu_utilization_percent: Optional[float] = None
    gpu_memory_used_mb: Optional[float] = None
    gpu_memory_total_mb: Optional[float] = None
    gpu_temperature_c: Optional[float] = None


def collect_resources() -> ResourceSnapshot:
    """
    Collect current system resource metrics.

    GPU metrics are None when pynvml is unavailable or no GPU is present.
    """
    # CPU & RAM via psutil
    cpu_percent = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    ram_used_mb = mem.used / (1024 * 1024)
    ram_total_mb = mem.total / (1024 * 1024)

    snapshot = ResourceSnapshot(
        cpu_percent=cpu_percent,
        ram_used_mb=round(ram_used_mb, 1),
        ram_total_mb=round(ram_total_mb, 1),
    )

    # GPU via pynvml (optional)
    try:
        import pynvml  # type: ignore[import-untyped]

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)

        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
        snapshot.gpu_utilization_percent = float(utilization.gpu)

        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        snapshot.gpu_memory_used_mb = round(mem_info.used / (1024 * 1024), 1)
        snapshot.gpu_memory_total_mb = round(mem_info.total / (1024 * 1024), 1)

        temp = pynvml.nvmlDeviceGetTemperature(
            handle, pynvml.NVML_TEMPERATURE_GPU
        )
        snapshot.gpu_temperature_c = float(temp)

        pynvml.nvmlShutdown()

    except ImportError:
        pass  # pynvml not installed
    except Exception as exc:
        logger.debug(f"GPU metrics unavailable: {exc}")

    return snapshot
