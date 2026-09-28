# Workspace Rules: Parallel & Distributed Computing (CSC-334)

> **Scope**: These rules apply strictly and exclusively to this workspace (`d:/7th semester/parallel lab/lab3` and related lab folders). They take precedence over any global branch restrictions.

---

## 1. Mandatory Git Repository & Main Branch Target
- **Target Repository**: `https://github.com/WaqarAnjum2/parrallel_and-_-distributed_computing.git`
- **Target Branch**: **`main`**
- **OVERRIDE OF GLOBAL U-6**: Do **NOT** create, commit to, or push to a `testing` branch in this repository. All lab tasks, commits, and pushes MUST target the **`main`** branch directly.

---

## 2. 100% Real Working Code Policy (Absolute Zero Mocks)
- **Zero Mock / Zero Placeholder Rule**: Every script (`server.py`, `client.py`, etc.) must be 100% real, functional, and directly executable code.
- Never use fake network wrappers, simulated stubs, or placeholder prints in place of real socket / thread / distributed operations.
- Real TCP/IP sockets (`socket.socket(AF_INET, SOCK_STREAM)`), real OS threads (`threading.Thread`), and real mutual exclusion locks (`threading.Lock` with explicit `acquire()` and `release()`) must be implemented and tested.

---

## 3. Comprehensive Documentation (`README.md`)
- Every lab task MUST maintain a high-quality, comprehensive `README.md` that documents:
  1. Lab title, course code, and objectives.
  2. Architecture and communication flow diagrams.
  3. Step-by-step instructions to run server and clients in separate terminals.
  4. Real, un-faked terminal output logs showing connection, thread IDs, IPs, ports, and clean shutdown.
  5. GitHub push and submission instructions.

---

## 4. Code Quality & Modularity
- Extensive, crystal-clear inline documentation and comments explaining distributed computing concepts.
- ANSI color formatting for terminal outputs to clearly separate thread events, client messages, and errors.
- Clean exception handling (`KeyboardInterrupt`, `ConnectionResetError`, `BrokenPipeError`) and guaranteed cleanup via `try...finally`.
