<img width="922" height="401" alt="image" src="https://github.com/user-attachments/assets/13ac8f92-42d7-40f0-baed-a0b4f8ceb8e3" />
<img width="1127" height="492" alt="image" src="https://github.com/user-attachments/assets/a4ad9a39-bc48-43fe-b3d6-34a1afa6abd0" />


# Parallel and Distributed Computing (CSC-334)
## Lab 03: Socket Programming with Multi-Threading

[![Repository](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/WaqarAnjum2/parrallel_and-_-distributed_computing.git)
[![Course](https://img.shields.io/badge/Course-CSC--334-green)](https://github.com/WaqarAnjum2/parrallel_and-_-distributed_computing.git)
[![Status](https://img.shields.io/badge/Implementation-100%25%20Real%20Working-brightgreen)](https://github.com/WaqarAnjum2/parrallel_and-_-distributed_computing.git)

---

### 📋 Student & Lab Details
- **Course**: Parallel and Distributed Computing (CSC-334)
- **Lab Title**: Lab 03: Socket Programming with Multi-Threading
- **Language**: Python 3.10+ (Standard Library: `socket`, `threading`, `time`, `datetime`)
- **Repository**: [`https://github.com/WaqarAnjum2/parrallel_and-_-distributed_computing.git`](https://github.com/WaqarAnjum2/parrallel_and-_-distributed_computing.git)
- **Branch**: `main`
- **Core Concepts**: Concurrency, TCP/IP Stream Sockets, Dedicated Per-Client Threads (`threading.Thread()`), Thread Synchronization using Mutual Exclusion Locks (`threading.Lock` with `acquire()` and `release()`), Clean Resource Deallocation.

---

## 🎯 Lab Requirements & Verification

| # | Lab 03 Requirement | Implementation Details | Verified File Reference |
| :---: | :--- | :--- | :--- |
| **1** | **Multi-Threaded Server** | Server accepts multiple clients simultaneously without blocking new connections. | [server.py](file:///d:/7th%20semester/parallel%20lab/lab3/server.py) |
| **2** | **Dedicated Worker Thread** | Each incoming client spawns a distinct `threading.Thread(target=handle_client, args=(...))` instance. | [server.py:233](file:///d:/7th%20semester/parallel%20lab/lab3/server.py#L233) |
| **3** | **Output Display** | Terminal displays: **Active Thread Name**, **Client IP Address**, and **Client Port Number** on connection, communication, and disconnection. | [server.py:104-108](file:///d:/7th%20semester/parallel%20lab/lab3/server.py#L104-L108) |
| **4** | **Thread Synchronization** | Protects shared counters (`active_clients_count`, `total_clients_served`) and terminal printing using explicit `thread_lock.acquire()` and `thread_lock.release()` in `try...finally`. | [server.py:97-111](file:///d:/7th%20semester/parallel%20lab/lab3/server.py#L97-L111) |
| **5** | **Continuous Client Messaging** | Client exchanges messages continuously in a loop with the server until user inputs `exit`, `quit`, or `q`. | [client.py:84-114](file:///d:/7th%20semester/parallel%20lab/lab3/client.py#L84-L114) |
| **6** | **Zero Mock Code** | 100% genuine OS network sockets and threads (no dummy placeholders or mocks). | Entire Codebase |

---

## 🏗️ Architecture & Concurrency Workflow

```
                        +----------------------------+
                        |       Server Process       |
                        | (server.py on port 5000)   |
                        +--------------+-------------+
                                       |
                   server_socket.accept() in main thread loop
                                       |
          +----------------------------+----------------------------+
          |                                                         |
          v                                                         v
+-------------------------+                               +-------------------------+
|     Worker Thread 1     |                               |     Worker Thread 2     |
| [Thread-Client-1:56516] |                               | [Thread-Client-2:56517] |
+------------+------------+                               +------------+------------+
             |                                                         |
             |  thread_lock.acquire()                                  |  thread_lock.acquire()
             |  Update active_clients_count                            |  Update active_clients_count
             |  thread_lock.release()                                  |  thread_lock.release()
             |                                                         |
             ^                                                         ^
    TCP Socket Stream                                         TCP Socket Stream
             v                                                         v
+------------+------------+                               +------------+------------+
|      Client 1 Terminal  |                               |      Client 2 Terminal  |
|        (client.py)      |                               |        (client.py)      |
+-------------------------+                               +-------------------------+
```

---

## 🔒 Thread Synchronization Explained

In a multi-threaded server, multiple client threads concurrently read and modify shared state (e.g., `active_clients_count`, `total_clients_served`, or writing to standard output). Without synchronization, race conditions can corrupt data or interleave terminal output.

In [server.py](file:///d:/7th%20semester/parallel%20lab/lab3/server.py), synchronization is implemented via `threading.Lock()`:

```python
thread_lock = threading.Lock()

# 1. Acquire Lock before entering critical section
thread_lock.acquire()
try:
    # Critical Section: Safely mutate shared state
    active_clients_count += 1
    # Atomic terminal printing
    print(f"Active Connections: {active_clients_count}")
finally:
    # 2. Always release the lock in a finally block to prevent deadlocks
    thread_lock.release()
```

---

## 📂 Repository File Structure

```
d:/7th semester/parallel lab/lab3/
├── server.py              # Multi-Threaded TCP Server with thread locking & detailed logs
├── client.py              # Interactive TCP Client script for continuous messaging
├── test_multi_clients.py  # Automated multi-client test simulator (3 parallel clients)
├── README.md              # Complete documentation, screenshots guide, and explanations
├── AGENTS.md              # Workspace rule file (Direct push to main, zero mock policy)
├── .agents/
│   └── rules/
│       └── workspace-rules.md  # IDE-level customization rule file
└── .gitignore             # Git ignore configuration
```

---

## 🚀 How to Run the Code

### Method 1: Manual Interactive Mode (Recommended for Screenshots)

Open **two or more separate command prompt or PowerShell terminals**:

#### Terminal 1 — Start the Server:
```powershell
python server.py
```
*The server will start listening on `127.0.0.1:5000`.*

#### Terminal 2 — Start Client 1:
```powershell
python client.py
```
- Type messages (e.g., `Hello from Client 1!`, `Testing sockets`).
- To disconnect, type `exit` or `quit`.

#### Terminal 3 — Start Client 2 (Demonstrating Simultaneous Multi-Threading):
```powershell
python client.py
```
- Observe how both Client 1 and Client 2 can send and receive messages at the same time.
- Notice on the server terminal that each client gets its own **Active Thread Name**, **Client IP**, and **Client Port**.

---

### Method 2: Automated Multi-Client Simulation Test

You can also run the automated multi-client test script:

1. In Terminal 1:
   ```powershell
   python server.py
   ```
2. In Terminal 2:
   ```powershell
   python test_multi_clients.py
   ```
*This connects 3 simulated clients simultaneously, sends messages concurrently, verifies thread safety, and closes sessions cleanly.*

---

## 📸 Real Terminal Execution Output

### Server Output (Actual Run):
```text
================================================================================
  CSC-334 : Parallel and Distributed Computing - Lab 03
  MULTI-THREADED TCP SERVER (Socket Programming + Thread Synchronization)
================================================================================
  [*] Server Host   : 127.0.0.1
  [*] Server Port   : 5000
  [*] Thread Safety : threading.Lock with explicit acquire() & release()
  [*] Status        : Ready & Listening for incoming client connections...
  [!] Press Ctrl+C at any time to gracefully shut down the server.
================================================================================

[✔] Server listening on 127.0.0.1:5000... Waiting for clients.

[+] [CONNECTION ACCEPTED] [2026-09-28 09:46:20]
    ├── Active Thread Name : Thread-Client-1 (127.0.0.1:56516)
    ├── Client IP Address  : 127.0.0.1
    ├── Client Port Number : 56516
    └── Active Connections : 1 (Total Running Threads: 2)

[+] [CONNECTION ACCEPTED] [2026-09-28 09:46:21]
    ├── Active Thread Name : Thread-Client-2 (127.0.0.1:56517)
    ├── Client IP Address  : 127.0.0.1
    ├── Client Port Number : 56517
    └── Active Connections : 2 (Total Running Threads: 3)

[+] [CONNECTION ACCEPTED] [2026-09-28 09:46:21]
    ├── Active Thread Name : Thread-Client-3 (127.0.0.1:56518)
    ├── Client IP Address  : 127.0.0.1
    ├── Client Port Number : 56518
    └── Active Connections : 3 (Total Running Threads: 4)

[MSG RECEIVED] [2026-09-28 09:46:21] <Thread-Client-1 (127.0.0.1:56516) | 127.0.0.1:56516>: Hello from Client 1!
[MSG RECEIVED] [2026-09-28 09:46:21] <Thread-Client-2 (127.0.0.1:56517) | 127.0.0.1:56517>: Greetings from Client 2!
[MSG RECEIVED] [2026-09-28 09:46:21] <Thread-Client-3 (127.0.0.1:56518) | 127.0.0.1:56518>: Client 3 reporting in!

[-] [CONNECTION CLOSED] [2026-09-28 09:46:22]
    ├── Terminated Thread  : Thread-Client-1 (127.0.0.1:56516)
    ├── Client IP Address  : 127.0.0.1
    ├── Client Port Number : 56516
    └── Active Connections : 2 (Remaining Threads: 3)

[-] [CONNECTION CLOSED] [2026-09-28 09:46:23]
    ├── Terminated Thread  : Thread-Client-2 (127.0.0.1:56517)
    ├── Client IP Address  : 127.0.0.1
    ├── Client Port Number : 56517
    └── Active Connections : 1 (Remaining Threads: 2)

[-] [CONNECTION CLOSED] [2026-09-28 09:46:23]
    ├── Terminated Thread  : Thread-Client-3 (127.0.0.1:56518)
    ├── Client IP Address  : 127.0.0.1
    ├── Client Port Number : 56518
    └── Active Connections : 0 (Remaining Threads: 1)
```

### Client Output (Actual Run):
```text
================================================================================
  CSC-334 : Parallel and Distributed Computing - Lab 03
  TCP CLIENT APPLICATION (Continuous Interactive Message Exchange)
================================================================================
  [*] Target Server Host : 127.0.0.1
  [*] Target Server Port : 5000
  [*] Exit Commands      : Type 'exit', 'quit', or 'q' to disconnect
================================================================================

[...] Connecting to server at 127.0.0.1:5000...
[✔] Connected successfully!
    ├── Local Client Port : 56516
    └── Connected To      : 127.0.0.1:5000

[SERVER] Connected successfully!
Assigned Server Thread : Thread-Client-1 (127.0.0.1:56516)
Your Endpoint          : 127.0.0.1:56516
Type any message to communicate. Type 'exit' or 'quit' to close connection.

────────────────────────────────────────────────────────────────────────────
Enter messages to send to the server below:

[Client 56516] Enter message > Hello from Client 1!
[2026-09-28 09:46:21] Server Response: [SERVER ECHO from Thread-Client-1 (127.0.0.1:56516) at 2026-09-28 09:46:21] Received: 'Hello from Client 1!' (Length: 20 chars)

[Client 56516] Enter message > exit

[!] Disconnect command sent. Awaiting final server response...
[SERVER] Disconnect command acknowledged. Goodbye!
[✔] Session terminated by user. Disconnected.
[✔] Socket closed. Client terminated.
```

---

## 📦 Git & Repository Management

This repository is configured to push directly to the **`main`** branch of:
`https://github.com/WaqarAnjum2/parrallel_and-_-distributed_computing.git`

```powershell
# Check status
git status

# Commit and push future labs
git add .
git commit -m "Update lab code"
git push origin main
```
