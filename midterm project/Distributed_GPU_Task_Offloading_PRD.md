# PRD + MASTER IMPLEMENTATION PROMPT
# Distributed GPU Task Offloading & Remote Video Processing System

**Document Version:** 1.0  
**Status:** Implementation Ready  
**Project Type:** Distributed Systems / Client-Server Networking / GPU Computing  
**Primary Workload:** Video Transcoding using FFmpeg + NVIDIA NVENC  
**Client:** Python + PyQt6  
**Worker:** Python + FastAPI  
**Communication:** HTTP/REST + WebSocket over LAN/Wi-Fi  
**Integrity:** SHA-256  
**Target:** Academic demonstration + production-quality engineering practices

---

# 1. MASTER AI AGENT PROMPT

> You are a senior distributed-systems engineer, Python backend engineer, desktop GUI engineer, networking engineer, GPU-computing engineer, security engineer, QA engineer, and DevOps engineer.
>
> Build the complete **Distributed GPU Task Offloading & Remote Video Processing System** described in this document.
>
> The system consists of:
>
> - A **Client Computer** with a PyQt6 desktop GUI.
> - A **Remote Worker Computer** with a Python FastAPI server and an NVIDIA GPU.
> - A LAN/Wi-Fi network connecting both computers.
> - FFmpeg on the worker using NVIDIA NVENC for GPU-accelerated H.264/H.265 video encoding.
>
> The client must never directly control the worker's GPU. It submits a structured job over the network. The worker validates the request, receives the input file, verifies integrity, queues the job, executes FFmpeg locally using its own hardware, streams progress back to the client, and makes the result available for download.
>
> Implement the system as a real distributed application rather than a mock/demo. Do not fake GPU utilization, progress, network transfer, job states, or benchmark values.
>
> Prefer simple, reliable technologies:
>
> - PyQt6 for desktop UI
> - FastAPI + Uvicorn for worker API
> - WebSocket for live events
> - HTTP streaming for file transfer
> - Python asyncio/threading/process management as appropriate
> - FFmpeg subprocess execution
> - NVIDIA NVENC
> - psutil for CPU/RAM metrics
> - NVIDIA NVML/PyNVML when available for GPU metrics
> - SHA-256 for integrity
>
> Do not introduce Redis, Celery, Kubernetes, databases, Docker, cloud services, or unnecessary infrastructure unless explicitly required later. The initial system must work on two ordinary computers connected to the same LAN/Wi-Fi.
>
> Never execute arbitrary shell commands received from the client. The client may send only structured, validated transcoding parameters. The worker must construct the FFmpeg command itself from a strict whitelist.
>
> The implementation must handle normal operation, invalid input, worker failure, network interruption, duplicate requests, cancellation, checksum mismatch, FFmpeg failure, timeout, insufficient disk space, GPU unavailable, and client disconnect scenarios gracefully.
>
> All operations must be observable through structured logs and user-visible status messages.
>
> The final implementation must include automated tests, manual test scenarios, benchmark tooling, setup documentation, network setup documentation, and a final technical report data export.

---

# 2. PROJECT VISION

## 2.1 Goal

Build a distributed computing system where a resource-constrained client offloads computationally intensive video transcoding to a more powerful remote GPU worker.

## 2.2 Core Concept

```text
CLIENT COMPUTER
    |
    | Job + File
    v
LAN / WI-FI
    |
    v
REMOTE GPU WORKER
    |
    +--> Validate
    +--> Queue
    +--> FFmpeg
    +--> NVIDIA NVENC
    +--> Generate Output
    |
    | Progress + Result
    v
CLIENT COMPUTER
```

## 2.3 Academic Concepts Demonstrated

- Distributed computing
- Client-server architecture
- Task offloading
- Network communication
- TCP/IP
- HTTP
- WebSocket
- Asynchronous communication
- Concurrency
- Task queues
- GPU acceleration
- Process management
- Fault tolerance
- Data integrity
- Resource monitoring
- Performance benchmarking

---

# 3. PROBLEM STATEMENT

A resource-constrained computer may require significant time to perform computationally intensive video transcoding. A more powerful computer with a dedicated GPU may be available on the same network.

The system allows the weaker computer to delegate the expensive computation to the GPU-enabled worker.

The system must answer an important engineering question:

> Does remote GPU offloading provide a real end-to-end performance advantage after including upload and download network overhead?

---

# 4. SYSTEM ACTORS

## 4.1 Client User

Uses the PyQt6 application to:

- Configure worker
- Test connectivity
- Select video
- Configure transcoding
- Submit jobs
- Monitor progress
- Cancel jobs
- Download output
- View benchmark results

## 4.2 Worker

A computer running:

- Python
- FastAPI
- FFmpeg
- NVIDIA drivers
- NVIDIA NVENC-capable GPU

The worker:

- Accepts jobs
- Validates requests
- Receives files
- Queues jobs
- Executes transcoding
- Reports progress
- Returns results

## 4.3 Network

LAN/Wi-Fi provides communication between client and worker.

Example:

```text
Client: 192.168.1.20
Worker: 192.168.1.10
Port:   8000
```

---

# 5. HIGH-LEVEL ARCHITECTURE

```text
+---------------------------------------------------------------+
|                         CLIENT COMPUTER                      |
|                                                               |
|  +-------------------+     +-------------------------------+  |
|  |      PyQt6 GUI    |---->| Client Application Services   |  |
|  +-------------------+     | - API Client                  |  |
|                            | - WebSocket Client             |  |
|                            | - File Transfer               |  |
|                            | - SHA-256                      |  |
|                            | - Benchmark                    |  |
|                            +---------------+---------------+  |
+--------------------------------------------|------------------+
                                             |
                                  HTTP / WebSocket
                                             |
                                             v
+---------------------------------------------------------------+
|                       WORKER COMPUTER                        |
|                                                               |
|  +-------------------+                                        |
|  | FastAPI Server    |                                        |
|  +---------+---------+                                        |
|            |                                                  |
|            v                                                  |
|  +-------------------+                                        |
|  | Job Manager       |                                        |
|  +---------+---------+                                        |
|            |                                                  |
|            v                                                  |
|  +-------------------+                                        |
|  | Task Queue        |                                        |
|  +---------+---------+                                        |
|            |                                                  |
|            v                                                  |
|  +-------------------+                                        |
|  | Job Executor      |                                        |
|  +---------+---------+                                        |
|            |                                                  |
|            v                                                  |
|  +-------------------+                                        |
|  | FFmpeg            |                                        |
|  +---------+---------+                                        |
|            |                                                  |
|            v                                                  |
|  +-------------------+                                        |
|  | NVIDIA NVENC GPU  |                                        |
|  +-------------------+                                        |
+---------------------------------------------------------------+
```

---

# 6. DESIGN PRINCIPLES

The implementation must follow these principles:

1. **No arbitrary remote command execution.**
2. **Do not block the PyQt6 GUI thread.**
3. **Do not load entire large video files into RAM.**
4. **Use streaming file transfer.**
5. **Use explicit job states.**
6. **Every job has a unique job ID.**
7. **Every uploaded input has a SHA-256 checksum.**
8. **Worker validates all client-controlled parameters.**
9. **FFmpeg runs as a managed subprocess.**
10. **GPU availability must be detected, not assumed.**
11. **Progress must come from actual FFmpeg execution.**
12. **Benchmark values must be measured, not fabricated.**
13. **Temporary files must be cleaned after completion/failure/cancellation.**
14. **Network failures must not crash the worker.**
15. **The system must remain usable when no worker is available.**

---

# 7. NETWORK COMMUNICATION MODEL

## 7.1 Transport

Use:

- HTTP/REST for request-response operations
- WebSocket for real-time job events
- TCP underneath both protocols

## 7.2 Example

```text
Client
  |
  | GET /health
  v
Worker

Client
  |
  | POST /jobs
  v
Worker

Client
  |
  | POST /jobs/{id}/upload
  v
Worker

Client
  |<================ WebSocket ================|
  |             progress events                |
  |
Worker

Client
  |
  | GET /jobs/{id}/result
  v
Worker
```

---

# 8. WORKER STARTUP

When the worker starts:

1. Load configuration.
2. Create required directories.
3. Detect FFmpeg.
4. Detect FFprobe.
5. Detect NVIDIA GPU.
6. Detect NVENC encoders.
7. Validate storage availability.
8. Start FastAPI/Uvicorn.
9. Initialize task queue.
10. Initialize resource monitor.
11. Log readiness.

Example startup output:

```text
=================================================
 Distributed GPU Worker
=================================================
Host: GPU-WORKER
IP: 192.168.1.10
Port: 8000
Python: 3.x
FFmpeg: detected
FFprobe: detected
GPU: NVIDIA RTX 3060
NVENC: h264_nvenc, hevc_nvenc
Storage: 420 GB available
Queue concurrency: 1
Status: READY
=================================================
```

---

# 9. CLIENT STARTUP

When the client starts:

1. Load saved UI preferences.
2. Display worker connection configuration.
3. Do not automatically submit jobs.
4. Allow manual worker connection.
5. Show disconnected state until health check succeeds.

---

# 10. CONNECTION / HANDSHAKE SCENARIOS

## Scenario A — Successful Connection

```text
Client -> GET /health
Worker -> 200 OK

Client -> GET /worker/info
Worker -> worker metadata

Client -> latency test
Worker -> pong/response

Client UI:
Connected
Worker Ready
GPU Available
```

## Scenario B — Worker Offline

Expected behavior:

```text
Client -> GET /health
        X connection refused

UI:
Worker Offline
Retry
```

The application must not crash.

## Scenario C — Wrong IP

```text
Connection failed
Reason: Timeout
Suggested action:
Verify worker IP and firewall.
```

## Scenario D — Wrong Port

```text
Connection failed
Reason: Connection refused
```

## Scenario E — Worker Online but GPU Unavailable

Worker can remain online.

```text
Worker: ONLINE
GPU: NOT AVAILABLE
NVENC: NOT AVAILABLE
```

The client must clearly display that GPU jobs cannot be submitted.

## Scenario F — Worker Online but NVENC Missing

The worker reports:

```text
GPU: AVAILABLE
NVENC: NOT AVAILABLE
```

The client must prevent NVENC jobs unless a CPU fallback mode is explicitly enabled by configuration.

---

# 11. HEALTH API

## Endpoint

```http
GET /health
```

## Response

```json
{
  "status": "online",
  "ready": true,
  "gpu_available": true,
  "nvenc_available": true,
  "queue_size": 0
}
```

---

# 12. WORKER INFO API

## Endpoint

```http
GET /worker/info
```

## Example

```json
{
  "hostname": "GPU-WORKER",
  "platform": "Windows",
  "cpu": "AMD Ryzen 7",
  "gpu": "NVIDIA RTX 3060",
  "gpu_memory_mb": 12288,
  "ffmpeg_version": "8.x",
  "encoders": [
    "h264_nvenc",
    "hevc_nvenc"
  ],
  "max_concurrent_jobs": 1
}
```

Do not expose unnecessary sensitive operating-system information.

---

# 13. LATENCY TEST

The client must provide a "Test Connection" button.

Measure:

- Minimum latency
- Average latency
- Maximum latency
- Failed requests

Example:

```text
Requests: 5
Successful: 5
Failed: 0

Min: 2.1 ms
Avg: 3.4 ms
Max: 5.2 ms

Worker: READY
```

---

# 14. JOB DATA MODEL

Each job must contain at minimum:

```json
{
  "job_id": "JOB-20261004-000001",
  "status": "CREATED",
  "filename": "input.mp4",
  "input_size": 524288000,
  "input_sha256": "...",
  "codec": "h264",
  "output_codec": "h264_nvenc",
  "resolution": "1280x720",
  "bitrate": "5M",
  "preset": "p4",
  "created_at": "...",
  "started_at": null,
  "completed_at": null
}
```

---

# 15. JOB STATE MACHINE

The job state machine is mandatory.

```text
                     +-----------+
                     |  CREATED  |
                     +-----+-----+
                           |
                           v
                     +-----------+
                     | UPLOADING |
                     +-----+-----+
                           |
                           v
                     +-----------+
                     | UPLOADED  |
                     +-----+-----+
                           |
                           v
                     +-----------+
                     |  QUEUED   |
                     +-----+-----+
                           |
                           v
                   +---------------+
                   |  PROCESSING   |
                   +-------+-------+
                           |
              +------------+------------+
              |            |            |
              v            v            v
         COMPLETED      FAILED      CANCELLED
              |
              v
         DOWNLOADING
              |
              v
           FINISHED
```

Additional terminal state:

```text
TIMEOUT
```

---

# 16. STATE TRANSITION RULES

Valid:

```text
CREATED -> UPLOADING
UPLOADING -> UPLOADED
UPLOADING -> FAILED
UPLOADED -> QUEUED
QUEUED -> PROCESSING
QUEUED -> CANCELLED
PROCESSING -> COMPLETED
PROCESSING -> FAILED
PROCESSING -> CANCELLED
PROCESSING -> TIMEOUT
COMPLETED -> DOWNLOADING
DOWNLOADING -> FINISHED
DOWNLOADING -> FAILED
```

Invalid state transitions must be rejected.

Example:

```text
FINISHED -> PROCESSING
```

must never be allowed.

---

# 17. FILE UPLOAD

The client must:

1. Verify file exists.
2. Verify readable.
3. Determine size.
4. Validate extension/container.
5. Calculate SHA-256.
6. Create job.
7. Upload using streaming chunks.
8. Display upload progress.

Do not read a 5 GB file completely into memory.

---

# 18. UPLOAD FAILURE SCENARIOS

## Scenario A — Connection Lost at 20%

Expected:

```text
Upload interrupted
Job marked FAILED or UPLOAD_INTERRUPTED
Temporary upload deleted
User offered Retry
```

## Scenario B — Client Closes

Worker must eventually clean abandoned temporary data.

## Scenario C — Worker Disk Full

Worker responds:

```text
Insufficient storage
```

and does not start processing.

## Scenario D — Checksum Mismatch

```text
Client SHA:
AAA...

Worker SHA:
BBB...

Result:
INTEGRITY FAILURE
```

Job must not enter PROCESSING.

---

# 19. FILE INTEGRITY

Use SHA-256.

Workflow:

```text
Client
  |
  | Calculate SHA-256
  v
Job Metadata
  |
  | Upload
  v
Worker
  |
  | Calculate SHA-256
  v
Compare
```

If:

```text
client_sha256 == worker_sha256
```

then:

```text
Integrity Verified
```

Otherwise:

```text
Integrity Failed
```

---

# 20. INPUT VALIDATION

Validate:

- File exists
- File size
- Extension
- MIME/container where possible
- Resolution
- Bitrate
- Preset
- Codec
- Output name
- Job ID
- Authentication token

Never trust client input.

---

# 21. FFmpeg SECURITY MODEL

NEVER accept:

```json
{
  "command": "ffmpeg ... arbitrary shell command ..."
}
```

Accept only:

```json
{
  "codec": "h264",
  "resolution": "1280x720",
  "bitrate": "5M",
  "preset": "p4"
}
```

Then construct the FFmpeg argument list internally.

Use subprocess argument arrays rather than unsafe shell-string execution.

Example conceptual command:

```text
[
  "ffmpeg",
  "-i", input_file,
  "-c:v", "h264_nvenc",
  "-preset", "p4",
  "-b:v", "5M",
  "-vf", "scale=1280:720",
  output_file
]
```

Do not use `shell=True`.

---

# 22. ALLOWED CODECS

Initial supported output:

```text
H.264 NVENC
HEVC NVENC
```

Optional future support:

```text
AV1 NVENC
```

Only enable codecs actually detected on the worker.

---

# 23. ALLOWED PRESETS

Use a strict whitelist appropriate to the installed FFmpeg/NVENC version.

Example configuration:

```text
p1
p2
p3
p4
p5
p6
p7
```

The implementation must verify that the selected preset is valid before execution.

---

# 24. RESOLUTION VALIDATION

Allow predefined values:

```text
3840x2160
2560x1440
1920x1080
1280x720
854x480
640x360
```

Optionally allow custom dimensions only when validated.

Reject:

```text
-1x100
0x0
999999x999999
```

---

# 25. BITRATE VALIDATION

Accept controlled values such as:

```text
1M
2M
5M
8M
12M
20M
```

Reject malformed or excessively large values.

---

# 26. JOB QUEUE

The first implementation must support:

```text
max_concurrent_jobs = 1
```

Example:

```text
JOB-001 -> PROCESSING
JOB-002 -> QUEUED
JOB-003 -> QUEUED
```

When JOB-001 completes:

```text
JOB-002 -> PROCESSING
```

Do not start multiple GPU jobs by default.

---

# 27. CONCURRENCY

The worker must remain responsive while a job is processing.

Do not execute FFmpeg synchronously inside the FastAPI request handler.

Recommended architecture:

```text
FastAPI
   |
   +--> Async API
   |
   +--> Async Queue
           |
           +--> Worker Task
                    |
                    +--> FFmpeg subprocess
```

The API must still answer health/status requests while FFmpeg is running.

---

# 28. FFmpeg EXECUTION

The worker starts FFmpeg as a subprocess.

Requirements:

- Capture stdout/stderr
- Capture progress
- Track PID/process handle
- Support cancellation
- Detect non-zero exit code
- Apply timeout
- Store logs
- Clean up temporary files

---

# 29. REAL-TIME FFmpeg PROGRESS

Prefer FFmpeg machine-readable progress output such as:

```text
-progress pipe:1
```

Parse fields such as:

```text
frame
fps
out_time
speed
progress
```

Do not estimate progress using fake timers.

For percentage calculation:

```text
progress =
current_output_time /
input_duration
* 100
```

Clamp between:

```text
0 and 100
```

---

# 30. WEBSOCKET EVENTS

WebSocket endpoint:

```text
/ws/jobs/{job_id}
```

Event types:

```text
job.created
job.upload_started
job.upload_progress
job.upload_completed
job.queued
job.started
job.progress
job.log
job.completed
job.failed
job.cancelled
job.timeout
job.download_started
job.download_progress
job.finished
```

Example:

```json
{
  "event": "job.progress",
  "job_id": "JOB-001",
  "progress": 62,
  "fps": 148,
  "speed": "3.1x",
  "timestamp": "..."
}
```

---

# 31. WEBSOCKET FAILURE SCENARIOS

## Scenario A — WebSocket Disconnect

The job must continue processing.

Important:

> Losing the progress connection must NOT automatically terminate the GPU job.

The client can reconnect and retrieve current status.

## Scenario B — Client Reconnects

Client:

```text
GET /jobs/JOB-001
```

Worker returns current state.

Then client reconnects WebSocket.

## Scenario C — Worker Restart

After worker restart, jobs that were processing may be marked:

```text
INTERRUPTED
```

The initial implementation does not need full persistent job recovery, but it must not claim a lost job completed.

---

# 32. JOB STATUS API

```http
GET /jobs/{job_id}
```

Example:

```json
{
  "job_id": "JOB-001",
  "status": "processing",
  "progress": 74,
  "fps": 151,
  "speed": "3.4x",
  "elapsed_seconds": 43.2
}
```

---

# 33. CANCELLATION

Endpoint:

```http
POST /jobs/{job_id}/cancel
```

## Queued Job

Remove from execution queue and mark:

```text
CANCELLED
```

## Processing Job

Terminate the FFmpeg subprocess safely.

Then:

```text
PROCESSING
    |
    v
CANCELLED
    |
    v
Cleanup
```

Do not kill unrelated worker processes.

---

# 34. TIMEOUT

Each job should have configurable maximum execution time.

If exceeded:

1. Mark TIMEOUT.
2. Terminate FFmpeg.
3. Wait for process termination.
4. Clean temporary output.
5. Notify client.

---

# 35. OUTPUT FILE

After successful processing:

```text
output/
  JOB-001/
      output.mp4
```

The worker must expose the output through a controlled download endpoint.

Do not expose arbitrary filesystem paths.

---

# 36. DOWNLOAD

Client requests:

```http
GET /jobs/{job_id}/result
```

Worker streams the file.

The client displays:

```text
Downloading:
████████████████░░░░ 82%
```

After completion, verify output checksum if the worker provides it.

---

# 37. CLIENT GUI

## Dashboard

Must show:

```text
Worker Status
GPU
NVENC
Latency
Queue Size
```

## Job Configuration

Must include:

```text
Input File
Output Filename
Codec
Resolution
Bitrate
Preset
```

## Progress

Must show:

```text
Upload
Queue
Processing
Download
Overall status
FPS
Encoding speed
Elapsed time
```

## Logs

Display a terminal-style live log.

## Results

Display:

```text
Input size
Output size
Upload time
GPU processing time
Download time
Total remote time
Speedup
Network overhead
```

---

# 38. GUI NON-BLOCKING REQUIREMENT

The PyQt6 UI thread must never perform:

- Large file hashing synchronously
- Large file upload synchronously
- Large file download synchronously
- HTTP request that can block for a long time
- WebSocket receive loop
- FFmpeg execution

Use worker threads, QThread, asyncio integration, or another safe concurrency mechanism.

---

# 39. CLIENT ERROR MESSAGES

Messages must be human-readable.

Bad:

```text
ConnectionError: [Errno 10061]
```

Better:

```text
Unable to connect to the worker.

Check:
- Worker IP
- Worker port
- Worker application
- Windows Firewall
- Network connection
```

---

# 40. ERROR SCENARIOS

The system must explicitly handle:

## E01 — Worker Offline

Result:

```text
Connection failed
```

## E02 — Authentication Failure

```text
Unauthorized worker request
```

## E03 — Invalid File

```text
Unsupported or invalid video file
```

## E04 — File Too Large

```text
File exceeds configured maximum size
```

## E05 — Upload Interrupted

```text
Upload interrupted
```

## E06 — Checksum Mismatch

```text
Input integrity verification failed
```

## E07 — GPU Missing

```text
NVIDIA GPU unavailable
```

## E08 — NVENC Missing

```text
NVENC encoder unavailable
```

## E09 — FFmpeg Failure

```text
Video processing failed
```

## E10 — Disk Full

```text
Insufficient worker storage
```

## E11 — WebSocket Disconnect

Job continues; client reconnects.

## E12 — Client Disconnect

Worker continues job unless cancellation policy says otherwise.

## E13 — Job Timeout

FFmpeg terminated and job marked TIMEOUT.

## E14 — Cancel

Job safely terminated.

## E15 — Worker Crash

In-flight job becomes INTERRUPTED/FAILED after restart detection.

---

# 41. SECURITY REQUIREMENTS

## Authentication

Use a worker authentication token.

Example:

```http
Authorization: Bearer <WORKER_TOKEN>
```

## Token Storage

Do not hardcode secrets into source code.

Use environment/configuration storage.

## Input Security

Never accept arbitrary commands.

## Path Security

Prevent:

```text
../
..\ 
absolute path injection
```

Generate worker-side filenames.

## File Type Security

Do not trust extension alone.

Use FFprobe and controlled formats.

## Resource Limits

Configure:

- Maximum upload size
- Maximum job duration
- Maximum queue length
- Maximum output size
- Maximum concurrent jobs

---

# 42. FIREWALL REQUIREMENTS

Worker must listen on the selected port, for example:

```text
TCP 8000
```

Windows/Linux firewall rules should permit only the required network scope.

For an academic LAN deployment, prefer restricting access to the local subnet rather than exposing the worker to the public Internet.

---

# 43. NETWORK TOPOLOGY

Recommended:

```text
             Wi-Fi Router
                  |
        +---------+---------+
        |                   |
        v                   v
 Client PC             Worker PC
192.168.1.20           192.168.1.10
                            |
                         TCP 8000
```

Alternative:

```text
Laptop <---- Ethernet ----> Worker
```

A direct connection can be used if both computers are configured appropriately.

---

# 44. WORKER RESOURCE MONITORING

Collect:

### CPU

```text
CPU %
```

### RAM

```text
RAM used / total
```

### GPU

```text
GPU utilization
GPU memory
GPU temperature
```

### Job

```text
FPS
Encoding speed
Elapsed time
```

Do not invent values when a metric is unavailable.

---

# 45. PERFORMANCE BENCHMARKING

Benchmark at least:

- 720p
- 1080p
- 4K if hardware permits
- Small file
- Medium file
- Large file

For each test collect:

```text
File size
Resolution
Duration
Local processing time
Upload time
Remote GPU time
Download time
Total remote time
CPU usage
GPU usage
RAM usage
Network throughput
```

---

# 46. BENCHMARK DEFINITIONS

## Local Time

```text
T_local
```

Time required for the client to process the same input locally using the defined baseline.

## Upload

```text
T_upload
```

## Remote GPU Processing

```text
T_gpu
```

## Download

```text
T_download
```

## Total Remote Time

```text
T_remote =
T_upload +
T_gpu +
T_download
```

## Speedup

```text
Speedup =
T_local / T_remote
```

## Network Overhead

```text
Network Overhead =
T_upload + T_download
```

## Network Overhead Percentage

```text
Network Overhead % =
((T_upload + T_download) / T_remote) * 100
```

---

# 47. BENCHMARK SCENARIOS

## Scenario B01 — Small 720p File

Expected purpose:

Demonstrate behavior where network overhead may reduce the advantage of remote processing.

## Scenario B02 — Medium 1080p File

Expected purpose:

Demonstrate normal GPU offloading advantage.

## Scenario B03 — Large 1080p File

Expected purpose:

Measure how file size and processing complexity affect the system.

## Scenario B04 — 4K File

Expected purpose:

Demonstrate GPU advantage for computationally expensive workload.

## Scenario B05 — Slow Network

Artificially or naturally test a slower connection.

Expected:

Remote GPU may become less beneficial due to transfer overhead.

## Scenario B06 — Fast Network

Expected:

Network overhead decreases relative to GPU processing time.

---

# 48. IMPORTANT BENCHMARK PRINCIPLE

Never claim:

```text
GPU is 5x faster
```

using GPU processing time alone.

Compare:

```text
LOCAL TOTAL
vs
REMOTE TOTAL
```

where:

```text
REMOTE TOTAL =
Upload +
GPU processing +
Download
```

This makes the analysis academically meaningful.

---

# 49. BENCHMARK DATA FORMAT

Store measurements as CSV/JSON.

Example:

```json
{
  "test_id": "B03",
  "input_size_mb": 1500,
  "resolution": "1920x1080",
  "duration_seconds": 600,
  "local_time_seconds": 420.2,
  "upload_seconds": 32.1,
  "gpu_seconds": 101.4,
  "download_seconds": 18.3,
  "remote_total_seconds": 151.8,
  "speedup": 2.77,
  "network_overhead_percent": 33.2
}
```

---

# 50. PROJECT DIRECTORY

Recommended structure:

```text
distributed-gpu-offloading/
│
├── client/
│   ├── main.py
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── connection_page.py
│   │   ├── job_page.py
│   │   ├── progress_page.py
│   │   └── result_page.py
│   │
│   ├── network/
│   │   ├── api_client.py
│   │   ├── websocket_client.py
│   │   └── transfer.py
│   │
│   ├── services/
│   │   ├── checksum.py
│   │   ├── benchmark.py
│   │   └── metadata.py
│   │
│   └── models/
│       └── job.py
│
├── worker/
│   ├── main.py
│   ├── api/
│   │   ├── health.py
│   │   ├── worker.py
│   │   ├── jobs.py
│   │   └── websocket.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── logging.py
│   │
│   ├── jobs/
│   │   ├── manager.py
│   │   ├── queue.py
│   │   └── executor.py
│   │
│   ├── gpu/
│   │   ├── detector.py
│   │   └── nvenc.py
│   │
│   ├── transfer/
│   │   ├── upload.py
│   │   └── download.py
│   │
│   └── monitoring/
│       └── resources.py
│
├── shared/
│   ├── schemas/
│   ├── constants/
│   └── protocol/
│
├── tests/
│   ├── client/
│   ├── worker/
│   ├── integration/
│   └── performance/
│
├── benchmarks/
│
├── scripts/
│
├── docs/
│
├── .env.example
├── README.md
└── requirements.txt
```

---

# 51. CONFIGURATION

Worker configuration should include:

```text
HOST=0.0.0.0
PORT=8000

AUTH_TOKEN=change-me

MAX_FILE_SIZE_MB=4096
MAX_JOB_DURATION_SECONDS=7200
MAX_QUEUE_SIZE=20
MAX_CONCURRENT_JOBS=1

INPUT_DIRECTORY=./data/inputs
OUTPUT_DIRECTORY=./data/outputs
TEMP_DIRECTORY=./data/temp
```

Client configuration:

```text
WORKER_HOST=192.168.1.10
WORKER_PORT=8000
AUTH_TOKEN=change-me
```

Never commit real credentials.

---

# 52. API CONTRACT

## POST /jobs

Request:

```json
{
  "filename": "video.mp4",
  "size": 524288000,
  "sha256": "...",
  "codec": "h264",
  "resolution": "1280x720",
  "bitrate": "5M",
  "preset": "p4"
}
```

Response:

```json
{
  "job_id": "JOB-001",
  "status": "CREATED"
}
```

## POST /jobs/{id}/upload

Streaming request body.

Response:

```json
{
  "job_id": "JOB-001",
  "status": "UPLOADED",
  "sha256_verified": true
}
```

## GET /jobs/{id}

Response:

```json
{
  "job_id": "JOB-001",
  "status": "PROCESSING",
  "progress": 52
}
```

## POST /jobs/{id}/cancel

Response:

```json
{
  "job_id": "JOB-001",
  "status": "CANCELLED"
}
```

## GET /jobs/{id}/result

Streams the completed output.

---

# 53. IDEMPOTENCY

The client must avoid accidental duplicate job creation caused by double-clicks or retries.

Use an idempotency key:

```text
X-Idempotency-Key: UUID
```

If the same request is repeated, the worker should return the original job rather than creating duplicate work when feasible.

---

# 54. RETRY POLICY

Retry only operations that are safe to retry.

Examples:

Safe:

```text
GET /health
GET /jobs/{id}
```

Potentially retryable:

```text
Upload if resumable upload is implemented
```

Do not blindly retry:

```text
POST /jobs
```

unless idempotency is enforced.

---

# 55. CLIENT DISCONNECT POLICY

If client disconnects during processing:

```text
Worker keeps processing.
```

Reason:

The job exists independently of the GUI connection.

The user can reconnect and query:

```text
GET /jobs/{job_id}
```

---

# 56. WORKER DISCONNECT POLICY

If worker becomes unreachable:

Client shows:

```text
Worker connection lost.
```

The client should periodically retry health/status.

If status cannot be confirmed, do not display:

```text
Job failed
```

unless the worker explicitly reports failure.

Use:

```text
UNKNOWN / CONNECTION LOST
```

when the true job state cannot be determined.

---

# 57. TEMPORARY FILE CLEANUP

Clean:

- Failed uploads
- Cancelled jobs
- Timed-out jobs
- Failed outputs
- Expired completed jobs

Never delete a file currently being processed.

Implement safe cleanup based on job ownership.

---

# 58. STORAGE MANAGEMENT

Before upload/processing:

```text
required_space =
input_size +
estimated_output_space +
safety_margin
```

If insufficient space:

```text
Reject job:
INSUFFICIENT_STORAGE
```

---

# 59. OBSERVABILITY

Worker logs should contain:

```text
timestamp
level
event
job_id
duration
error_code
```

Example:

```text
2026-10-04T21:00:00 INFO job.created job_id=JOB-001
2026-10-04T21:00:04 INFO upload.completed job_id=JOB-001
2026-10-04T21:00:05 INFO processing.started job_id=JOB-001
2026-10-04T21:00:48 INFO processing.completed job_id=JOB-001
```

Never log authentication tokens.

---

# 60. TESTING STRATEGY

Testing must include:

## Unit Tests

- Checksum
- Validation
- Job state transitions
- FFmpeg command builder
- Progress parser
- Benchmark calculations

## Integration Tests

- Client -> worker health
- Job creation
- File upload
- Processing
- WebSocket
- Download

## Failure Tests

- Worker offline
- Wrong IP
- Wrong port
- Network disconnect
- Checksum mismatch
- FFmpeg failure
- GPU unavailable
- Disk full
- Cancellation
- Timeout

## Performance Tests

- Different file sizes
- Different resolutions
- Different network conditions

---

# 61. ACCEPTANCE TEST CASES

## AT-01 Worker Startup

**Given:** FFmpeg and NVIDIA drivers are installed.

**When:** Worker starts.

**Then:** Worker reports GPU and NVENC status and becomes READY.

## AT-02 Client Connection

**Given:** Worker is reachable.

**When:** Client clicks Test Connection.

**Then:** Client displays worker status and latency.

## AT-03 Job Submission

**Given:** Valid video.

**When:** User submits job.

**Then:** Worker creates unique job ID.

## AT-04 Upload

**Given:** Valid job.

**When:** Client uploads.

**Then:** Worker receives complete file.

## AT-05 Integrity

**Given:** Correct upload.

**Then:** SHA-256 values match.

## AT-06 GPU Processing

**Given:** NVENC available.

**Then:** FFmpeg uses an NVENC encoder.

## AT-07 Progress

**Given:** Processing job.

**Then:** Client receives live progress.

## AT-08 Download

**Given:** Completed job.

**Then:** Client downloads output successfully.

## AT-09 Cancellation

**Given:** Processing job.

**When:** User cancels.

**Then:** FFmpeg terminates and temporary data is cleaned.

## AT-10 Failure

**Given:** FFmpeg returns non-zero exit code.

**Then:** Job becomes FAILED and client receives an error.

## AT-11 Reconnection

**Given:** WebSocket disconnects.

**Then:** Processing continues and client can reconnect.

## AT-12 Benchmark

**Given:** Same input and encoding parameters.

**Then:** Local and remote timings are recorded and speedup is calculated.

---

# 62. DEMONSTRATION SCENARIOS

## Demo 1 — Normal Operation

```text
Start worker
   ↓
Start client
   ↓
Connect
   ↓
Select video
   ↓
Submit
   ↓
Upload
   ↓
Queue
   ↓
GPU processing
   ↓
Progress
   ↓
Complete
   ↓
Download
   ↓
Verify
```

## Demo 2 — Worker Offline

Stop worker.

Client attempts connection.

Expected:

```text
Worker unavailable
```

## Demo 3 — Upload Interruption

Disconnect network during upload.

Expected:

```text
Upload interrupted
No corrupted file processed
```

## Demo 4 — GPU Failure

Configure a worker without NVENC.

Expected:

```text
GPU/NVENC unavailable
Job rejected or CPU fallback if explicitly enabled
```

## Demo 5 — Cancellation

Start large job.

Click Cancel.

Expected:

```text
FFmpeg terminated
Job CANCELLED
Temporary files removed
```

## Demo 6 — WebSocket Failure

Close/restart client UI connection while job is running.

Expected:

```text
Worker continues job
Client reconnects
Current status recovered
```

## Demo 7 — Checksum Failure

Intentionally alter a test upload.

Expected:

```text
Checksum mismatch
Processing never starts
```

## Demo 8 — Queue

Submit three jobs.

Expected:

```text
JOB-001 PROCESSING
JOB-002 QUEUED
JOB-003 QUEUED
```

## Demo 9 — Benchmark

Run the same input locally and remotely.

Expected:

```text
Local time
Remote total time
Network overhead
Speedup
```

---

# 63. DEVELOPMENT PHASES

## Phase 1 — Environment

- Python
- PyQt6
- FastAPI
- FFmpeg
- NVIDIA driver
- NVENC
- Network

Deliverable:

```text
Both machines can communicate.
```

## Phase 2 — Worker Skeleton

Implement:

```text
/health
/worker/info
```

Deliverable:

```text
Worker READY
```

## Phase 3 — Client Connection

Implement:

```text
Worker IP
Port
Connect
Health
Latency
```

## Phase 4 — Job API

Implement:

```text
POST /jobs
GET /jobs/{id}
```

## Phase 5 — File Transfer

Implement:

```text
Upload
SHA-256
Download
```

## Phase 6 — FFmpeg

Implement:

```text
Job queue
FFmpeg
NVENC
```

## Phase 7 — WebSocket

Implement:

```text
Live progress
Live logs
Reconnect
```

## Phase 8 — Reliability

Implement:

```text
Timeout
Cancel
Retry
Cleanup
Failure handling
```

## Phase 9 — GUI Polish

Implement:

```text
Dashboard
Progress
Logs
Results
```

## Phase 10 — Benchmarking

Implement:

```text
Local test
Remote test
Metrics
CSV/JSON export
Charts
```

## Phase 11 — Final Validation

Run every acceptance test.

---

# 64. DEFINITION OF DONE

The project is complete only when all of the following are true:

- [ ] Client runs independently.
- [ ] Worker runs independently.
- [ ] Client can connect over LAN.
- [ ] Health check works.
- [ ] Latency measurement works.
- [ ] Worker GPU detection works.
- [ ] NVENC detection works.
- [ ] Job creation works.
- [ ] File upload works.
- [ ] SHA-256 verification works.
- [ ] Queue works.
- [ ] FFmpeg executes.
- [ ] Actual NVENC encoder is used.
- [ ] Progress is streamed.
- [ ] WebSocket reconnect works.
- [ ] Cancellation works.
- [ ] Timeout works.
- [ ] Failure handling works.
- [ ] Output download works.
- [ ] Output integrity can be verified.
- [ ] Temporary files are cleaned.
- [ ] Benchmark data is recorded.
- [ ] Speedup is calculated correctly.
- [ ] Network overhead is calculated.
- [ ] CPU/GPU/RAM metrics are recorded where supported.
- [ ] Unit tests exist.
- [ ] Integration tests exist.
- [ ] README exists.
- [ ] Installation instructions exist.
- [ ] Network/firewall instructions exist.
- [ ] Final report data can be exported.

---

# 65. FINAL REPORT REQUIREMENTS

The technical report should contain:

1. Introduction
2. Problem Statement
3. Motivation
4. Objectives
5. Related Concepts
6. System Architecture
7. Network Architecture
8. Client Design
9. Worker Design
10. Communication Protocol
11. Job State Machine
12. GPU Processing
13. File Transfer
14. Integrity Verification
15. Error Handling
16. Security
17. Testing
18. Benchmark Methodology
19. Benchmark Results
20. Performance Analysis
21. Limitations
22. Future Work
23. Conclusion

---

# 66. ARCHITECTURE DIAGRAM FOR REPORT

```text
                    DISTRIBUTED GPU OFFLOADING

              +-----------------------------+
              |        CLIENT COMPUTER      |
              |                             |
              |       PyQt6 GUI             |
              |            |                |
              |       Client Services       |
              +------------+----------------+
                           |
                     HTTP/WebSocket
                           |
                    LAN / Wi-Fi
                           |
                           v
              +-----------------------------+
              |       REMOTE WORKER         |
              |                             |
              |        FastAPI              |
              |            |                |
              |       Job Manager           |
              |            |                |
              |       Task Queue             |
              |            |                |
              |       FFmpeg Executor       |
              |            |                |
              |      NVIDIA NVENC           |
              |            |                |
              |       GPU Processing         |
              +-----------------------------+
                           |
                           v
                     Output Video
                           |
                           |
                           v
                     CLIENT RESULT
```

---

# 67. IMPORTANT ENGINEERING DECISIONS

## Decision 1

Use **FastAPI + WebSocket** instead of implementing the entire application using raw TCP sockets.

Reason:

- Easier API design
- Easier debugging
- Built-in HTTP semantics
- WebSocket support
- Good academic demonstration of networking

Raw sockets can be added as an optional educational comparison.

## Decision 2

Use **single GPU job concurrency initially**.

Reason:

- Predictable benchmarking
- Prevent GPU memory contention
- Easier scheduling
- Easier debugging

## Decision 3

Use **streaming transfer**.

Reason:

- Large files
- Low RAM consumption
- Better scalability

## Decision 4

Use **actual FFmpeg progress**.

Reason:

- Accurate measurements
- No fake progress
- Better technical credibility

---

# 68. OPTIONAL RAW SOCKET EXTENSION

If the course specifically requires socket programming, add a lightweight TCP control channel.

Example:

```text
Client
  |
  | TCP
  v
Worker
```

Protocol:

```text
HELLO
HELLO_ACK
AUTH
AUTH_ACK
PING
PONG
JOB_REQUEST
JOB_ACK
PROGRESS
JOB_COMPLETE
ERROR
```

However, the core implementation should remain HTTP/WebSocket unless raw sockets are explicitly required.

---

# 69. OPTIONAL CPU FALLBACK

CPU fallback must be disabled by default if the assignment specifically evaluates GPU offloading.

If enabled:

```text
NVENC available?
    |
   YES ---> GPU
    |
    NO
    |
    v
CPU fallback
```

The benchmark must label the execution mode clearly:

```text
GPU NVENC
```

or:

```text
CPU
```

Never mix results.

---

# 70. EXPECTED FINAL USER EXPERIENCE

The final user experience should be:

```text
1. Open Client

2. Enter:
   Worker IP = 192.168.1.10
   Port = 8000

3. Click:
   Test Connection

4. See:
   Worker Online
   GPU: RTX 3060
   NVENC: Available
   Latency: 3 ms

5. Select:
   movie.mp4

6. Configure:
   1080p
   H.264
   8 Mbps
   P4

7. Click:
   Start Remote Processing

8. See:
   Uploading 100%
   Queued
   GPU Processing 25%
   GPU Processing 50%
   GPU Processing 75%
   GPU Processing 100%

9. See:
   Job Completed

10. Download:
    output.mp4

11. See:
    Integrity Verified

12. See:
    Local: 320 sec
    Remote: 105 sec
    Speedup: 3.05x
```

---

# 71. FINAL SYSTEM PRINCIPLE

The entire project can be summarized as:

```text
              USER
               |
               v
        +-------------+
        | PyQt6 GUI   |
        +------+------+
               |
               | Submit Job
               v
        +-------------+
        | LAN / Wi-Fi |
        +------+------+
               |
               v
        +-------------+
        | FastAPI     |
        | Worker      |
        +------+------+
               |
               v
        +-------------+
        | Job Queue   |
        +------+------+
               |
               v
        +-------------+
        | FFmpeg      |
        +------+------+
               |
               v
        +-------------+
        | NVIDIA GPU  |
        | NVENC       |
        +------+------+
               |
               v
          OUTPUT VIDEO
               |
               v
        +-------------+
        | Client      |
        | Download    |
        +-------------+
```

The system is therefore a **true distributed task-offloading application**: the client owns the request and user experience, while the worker owns the computation and GPU resources. The network is the communication layer between them.
