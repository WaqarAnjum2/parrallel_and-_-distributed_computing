# Academic Report Data Export Guide

This document explains how to export, interpret, and format the measured benchmark data for academic reports, lab assignments, and research publications.

---

## 📊 Exporting Benchmark Data

After running jobs and local benchmarks in the client application:
1. Navigate to the **Results** tab.
2. Click **Export Results**.
3. Choose a destination folder (e.g. `benchmarks/results/`).
4. Two files will be generated:
   - `benchmarks_<timestamp>.json`: Full structured JSON dataset with machine details and timestamps.
   - `benchmarks_<timestamp>.csv`: Flat tabular format directly importable into Excel, Google Sheets, or Pandas.

---

## 📑 CSV Schema & Field Definitions

| Column Header | Unit | Description |
|---|---|---|
| `test_id` | string | Unique Job ID identifier |
| `input_filename` | string | Base name of the source video |
| `resolution` | string | Output target resolution (e.g. 1920x1080) |
| `duration_seconds` | seconds | Length of video stream |
| `local_time_seconds` | seconds | Measured CPU execution time ($T_{\text{local}}$) |
| `upload_time_seconds` | seconds | Streaming upload duration ($T_{\text{upload}}$) |
| `gpu_time_seconds` | seconds | Worker NVENC encoding duration ($T_{\text{gpu}}$) |
| `download_time_seconds` | seconds | Streaming download duration ($T_{\text{download}}$) |
| `remote_total_seconds` | seconds | Sum of upload, GPU, and download times ($T_{\text{remote}}$) |
| `speedup` | factor | Ratio of $T_{\text{local}} / T_{\text{remote}}$ |
| `network_overhead_percent` | % | Ratio of network time to total remote time |

---

## 📈 Generating Report Graphs in Python

You can easily generate report charts from the exported CSV with `matplotlib`:
```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("benchmarks_results.csv")

# Bar chart comparing Local CPU vs Remote GPU
df[["test_id", "local_time_seconds", "remote_total_seconds"]].plot(
    x="test_id", kind="bar", figsize=(10, 6)
)
plt.ylabel("Time (seconds)")
plt.title("Execution Time Comparison: Local CPU vs Remote GPU Offloading")
plt.savefig("benchmark_comparison.png")
```
