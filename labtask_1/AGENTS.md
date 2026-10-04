# Workspace Rules: Parallel & Distributed Computing (CSC-334)

> **Scope**: These rules apply strictly to this workspace (`d:/7th semester/parallel lab/lab3` and related lab directories). They explicitly override any conflicting global branch restrictions.

---

## 1. Mandatory Git Target: Direct Push to `main`
- **Target Repository**: `https://github.com/WaqarAnjum2/parrallel_and-_-distributed_computing.git`
- **Target Branch**: **`main`**
- **OVERRIDE**: Do **NOT** create or push to a `testing` branch. Always commit and push directly to the **`main`** branch.

---

## 2. 100% Real Working Code Policy (Absolute Zero Mocks)
- All implementations must be 100% real, fully functional, and production-tested Python code.
- Zero mock or placeholder code. Real TCP/IP sockets, real multi-threading, and real thread locks must be used.

---

## 3. Mandatory Comprehensive `README.md`
- Always maintain an in-depth `README.md` with:
  - Complete lab requirements and architecture explanation.
  - Clear terminal execution commands.
  - Verified real terminal execution logs and outputs.
  - Evaluation and submission checklist.

---

## 4. Code Standards & Aesthetics
- Detailed inline comments explaining networking, concurrency, and synchronization.
- Beautiful terminal output layout with colors, timestamps, and thread identifiers.
- Graceful error handling and socket resource cleanup in `finally` blocks.
