"""
================================================================================
COURSE  : Parallel and Distributed Computing (CSC-334)
LAB 03  : Socket Programming with Multi-Threading
FILE    : server.py
PURPOSE : Multi-Threaded TCP Server using Python's 'threading' and 'socket' modules.
          Supports simultaneous multi-client handling, dedicated per-client threads,
          detailed terminal logging (Thread Name, IP, Port), and thread synchronization
          using explicit Lock acquire() and release() methods.
================================================================================
"""

import socket
import threading
import sys
import os
import datetime
import functools

# Force print to always flush immediately (prevents output buffering issues)
print = functools.partial(print, flush=True)

# Enable VT100 ANSI terminal escape codes on Windows for colored output
if os.name == "nt":
    os.system("")

# ------------------------------------------------------------------------------
# ANSI Color Codes for Clean, Beautiful Terminal Formatting
# ------------------------------------------------------------------------------
COLOR_RESET   = "\033[0m"
COLOR_BOLD    = "\033[1m"
COLOR_CYAN    = "\033[96m"
COLOR_GREEN   = "\033[92m"
COLOR_YELLOW  = "\033[93m"
COLOR_RED     = "\033[91m"
COLOR_MAGENTA = "\033[95m"
COLOR_BLUE    = "\033[94m"

# ------------------------------------------------------------------------------
# Server Configuration Constants
# ------------------------------------------------------------------------------
HOST = "127.0.0.1"       # Standard loopback interface (localhost)
PORT = 5000              # Port to listen on (non-privileged ports > 1023)
BUFFER_SIZE = 1024       # Buffer size in bytes for incoming socket packets

# ------------------------------------------------------------------------------
# Shared Resources & Thread Synchronization
# ------------------------------------------------------------------------------
# Lock for synchronizing access to shared resources and terminal output
thread_lock = threading.Lock()

# Shared state variables protected by the thread_lock
active_clients_count = 0
total_clients_served = 0


def get_current_timestamp() -> str:
    """Returns the current formatted timestamp string for logging."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def print_server_banner() -> None:
    """Displays an aesthetically styled startup banner for the server."""
    banner = f"""
{COLOR_CYAN}{COLOR_BOLD}================================================================================
  CSC-334 : Parallel and Distributed Computing - Lab 03
  MULTI-THREADED TCP SERVER (Socket Programming + Thread Synchronization)
================================================================================{COLOR_RESET}
  {COLOR_GREEN}[*] Server Host   :{COLOR_RESET} {HOST}
  {COLOR_GREEN}[*] Server Port   :{COLOR_RESET} {PORT}
  {COLOR_GREEN}[*] Thread Safety :{COLOR_RESET} threading.Lock with explicit acquire() & release()
  {COLOR_GREEN}[*] Status        :{COLOR_RESET} Ready & Listening for incoming client connections...
  {COLOR_YELLOW}[!] Press Ctrl+C at any time to gracefully shut down the server.{COLOR_RESET}
{COLOR_CYAN}================================================================================{COLOR_RESET}
"""
    print(banner)


def handle_client(client_socket: socket.socket, client_address: tuple) -> None:
    """
    Worker function executed in a dedicated thread for each connected client.

    Requirements Handled:
    1. Runs inside a distinct threading.Thread instance.
    2. Identifies Active Thread Name, Client IP, and Client Port Number.
    3. Uses thread_lock.acquire() and thread_lock.release() to safely update
       shared state (active client count, total client counter) and serialize console output.
    4. Continuously receives messages until the client issues an 'exit' command or disconnects.
    """
    global active_clients_count, total_clients_served

    # Extract client network parameters and current thread metadata
    client_ip, client_port = client_address
    current_thread = threading.current_thread()
    thread_name = current_thread.name

    # --------------------------------------------------------------------------
    # THREAD SYNCHRONIZATION: Client Registration (Lock acquire & release)
    # --------------------------------------------------------------------------
    # Explicitly acquiring the lock before updating shared state
    thread_lock.acquire()
    try:
        active_clients_count += 1
        total_clients_served += 1
        total_active_threads = threading.active_count()

        # Display client connection details as required by Lab 03
        print(f"\n{COLOR_GREEN}[+] [CONNECTION ACCEPTED]{COLOR_RESET} [{get_current_timestamp()}]")
        print(f"    ├── {COLOR_BOLD}Active Thread Name :{COLOR_RESET} {COLOR_MAGENTA}{thread_name}{COLOR_RESET}")
        print(f"    ├── {COLOR_BOLD}Client IP Address  :{COLOR_RESET} {COLOR_CYAN}{client_ip}{COLOR_RESET}")
        print(f"    ├── {COLOR_BOLD}Client Port Number :{COLOR_RESET} {COLOR_YELLOW}{client_port}{COLOR_RESET}")
        print(f"    └── {COLOR_BOLD}Active Connections :{COLOR_RESET} {COLOR_GREEN}{active_clients_count}{COLOR_RESET} (Total Running Threads: {total_active_threads})")
    finally:
        # Explicitly releasing the lock
        thread_lock.release()

    # Send initial welcome and handshake message to client
    welcome_message = (
        f"[SERVER] Connected successfully!\n"
        f"Assigned Server Thread : {thread_name}\n"
        f"Your Endpoint          : {client_ip}:{client_port}\n"
        f"Type any message to communicate. Type 'exit' or 'quit' to close connection.\n"
    )
    try:
        client_socket.sendall(welcome_message.encode("utf-8"))
    except (socket.error, BrokenPipeError):
        pass

    # --------------------------------------------------------------------------
    # Continuous Message Exchange Loop
    # --------------------------------------------------------------------------
    try:
        while True:
            # Block until message bytes are received from this client
            data = client_socket.recv(BUFFER_SIZE)

            # An empty byte sequence indicates the client closed the connection
            if not data:
                break

            # Decode the received message
            message = data.decode("utf-8").strip()

            # Check if client requested to terminate the session
            if message.lower() in ("exit", "quit", "bye", "q"):
                # Send polite acknowledgment before closing
                farewell = "[SERVER] Disconnect command acknowledged. Goodbye!\n"
                try:
                    client_socket.sendall(farewell.encode("utf-8"))
                except socket.error:
                    pass
                break

            # Synchronize console logging so output from multiple threads does not interleave
            thread_lock.acquire()
            try:
                print(f"{COLOR_BLUE}[MSG RECEIVED]{COLOR_RESET} [{get_current_timestamp()}] "
                      f"<{COLOR_MAGENTA}{thread_name}{COLOR_RESET} | {COLOR_CYAN}{client_ip}:{client_port}{COLOR_RESET}>: "
                      f"{COLOR_BOLD}{message}{COLOR_RESET}")
            finally:
                thread_lock.release()

            # Prepare server response (Echo + thread information + server timestamp)
            response = (
                f"[SERVER ECHO from {thread_name} at {get_current_timestamp()}] "
                f"Received: '{message}' (Length: {len(message)} chars)"
            )
            client_socket.sendall(response.encode("utf-8"))

    except ConnectionResetError:
        # Handle abrupt client disconnects (e.g., client terminal closed)
        thread_lock.acquire()
        try:
            print(f"{COLOR_YELLOW}[!] [CONNECTION RESET]{COLOR_RESET} Client {client_ip}:{client_port} closed unexpectedly.")
        finally:
            thread_lock.release()

    except Exception as exc:
        thread_lock.acquire()
        try:
            print(f"{COLOR_RED}[-] [ERROR in {thread_name}]:{COLOR_RESET} {exc}")
        finally:
            thread_lock.release()

    finally:
        # ----------------------------------------------------------------------
        # THREAD SYNCHRONIZATION: Client Deregistration & Cleanup
        # ----------------------------------------------------------------------
        thread_lock.acquire()
        try:
            active_clients_count -= 1
            remaining_threads = threading.active_count() - 1  # Excluding the current finishing thread

            print(f"\n{COLOR_RED}[-] [CONNECTION CLOSED]{COLOR_RESET} [{get_current_timestamp()}]")
            print(f"    ├── {COLOR_BOLD}Terminated Thread  :{COLOR_RESET} {COLOR_MAGENTA}{thread_name}{COLOR_RESET}")
            print(f"    ├── {COLOR_BOLD}Client IP Address  :{COLOR_RESET} {COLOR_CYAN}{client_ip}{COLOR_RESET}")
            print(f"    ├── {COLOR_BOLD}Client Port Number :{COLOR_RESET} {COLOR_YELLOW}{client_port}{COLOR_RESET}")
            print(f"    └── {COLOR_BOLD}Active Connections :{COLOR_RESET} {COLOR_GREEN}{active_clients_count}{COLOR_RESET} (Remaining Threads: {remaining_threads})")
        finally:
            # Release the lock so other threads can proceed
            thread_lock.release()

        # Close client socket handle to free system descriptors
        client_socket.close()


def main() -> None:
    """Initializes the TCP socket server and accepts client connections in a multi-threaded loop."""
    print_server_banner()

    # Create a TCP/IP streaming socket using IPv4
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Set socket option SO_REUSEADDR so the port can be immediately rebound on restart
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        # Bind socket to host and port
        server_socket.bind((HOST, PORT))

        # Listen for incoming connections (backlog queue of 10)
        server_socket.listen(10)
        print(f"{COLOR_GREEN}[✔] Server listening on {HOST}:{PORT}... Waiting for clients.{COLOR_RESET}\n")

        client_counter = 0

        # Main server accept loop
        while True:
            # accept() blocks until a new client initiates a TCP 3-way handshake
            client_socket, client_address = server_socket.accept()
            client_counter += 1

            # Requirement: Start a new thread for each client using threading.Thread()
            # Assign a clean, recognizable name to the thread for identification
            thread_name = f"Thread-Client-{client_counter} ({client_address[0]}:{client_address[1]})"

            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket, client_address),
                name=thread_name,
                daemon=True  # Allows graceful server exit even if worker threads are running
            )

            # Start execution of the new thread
            client_thread.start()

    except KeyboardInterrupt:
        print(f"\n{COLOR_YELLOW}[!] KeyboardInterrupt received. Shutting down server gracefully...{COLOR_RESET}")
    except Exception as exc:
        print(f"\n{COLOR_RED}[-] Server startup error: {exc}{COLOR_RESET}")
    finally:
        server_socket.close()
        print(f"{COLOR_CYAN}[✔] Server socket closed. Exiting program.{COLOR_RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
