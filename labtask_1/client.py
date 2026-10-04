"""
================================================================================
COURSE  : Parallel and Distributed Computing (CSC-334)
LAB 03  : Socket Programming with Multi-Threading
FILE    : client.py
PURPOSE : Interactive TCP Client script communicating continuously with the
          Multi-Threaded TCP Server until user inputs 'exit' or 'quit'.
================================================================================
"""

import socket
import sys
import os
import datetime
import functools

# Force print to always flush immediately
print = functools.partial(print, flush=True)

# Enable VT100 ANSI terminal escape codes on Windows for colored output
if os.name == "nt":
    os.system("")

# ------------------------------------------------------------------------------
# ANSI Color Codes for Clean Terminal Formatting
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
# Default Connection Parameters
# ------------------------------------------------------------------------------
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
BUFFER_SIZE = 1024


def get_current_timestamp() -> str:
    """Returns the current formatted timestamp string."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def print_client_banner(host: str, port: int) -> None:
    """Displays an aesthetically styled client header banner."""
    banner = f"""
{COLOR_CYAN}{COLOR_BOLD}================================================================================
  CSC-334 : Parallel and Distributed Computing - Lab 03
  TCP CLIENT APPLICATION (Continuous Interactive Message Exchange)
================================================================================{COLOR_RESET}
  {COLOR_GREEN}[*] Target Server Host :{COLOR_RESET} {host}
  {COLOR_GREEN}[*] Target Server Port :{COLOR_RESET} {port}
  {COLOR_GREEN}[*] Exit Commands      :{COLOR_RESET} Type 'exit', 'quit', or 'q' to disconnect
{COLOR_CYAN}================================================================================{COLOR_RESET}
"""
    print(banner)


def main() -> None:
    """Connects to the server and maintains continuous message exchange."""
    # Allow command line overrides: python client.py [host] [port]
    host = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT

    print_client_banner(host, port)

    # Create a TCP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        print(f"{COLOR_YELLOW}[...] Connecting to server at {host}:{port}...{COLOR_RESET}")
        client_socket.connect((host, port))

        # Query local socket address assigned by OS to this client
        local_ip, local_port = client_socket.getsockname()
        print(f"{COLOR_GREEN}[✔] Connected successfully!{COLOR_RESET}")
        print(f"    ├── {COLOR_BOLD}Local Client Port :{COLOR_RESET} {COLOR_YELLOW}{local_port}{COLOR_RESET}")
        print(f"    └── {COLOR_BOLD}Connected To      :{COLOR_RESET} {COLOR_CYAN}{host}:{port}{COLOR_RESET}\n")

        # Receive and display the initial server welcome/handshake message
        welcome_data = client_socket.recv(BUFFER_SIZE)
        if welcome_data:
            print(f"{COLOR_MAGENTA}{welcome_data.decode('utf-8')}{COLOR_RESET}")

        print(f"{COLOR_CYAN}────────────────────────────────────────────────────────────────────────────{COLOR_RESET}")
        print(f"{COLOR_BOLD}Enter messages to send to the server below:{COLOR_RESET}\n")

        # Continuous message exchange loop
        while True:
            # Prompt user for input
            try:
                user_message = input(f"{COLOR_GREEN}[Client {local_port}] Enter message > {COLOR_RESET}").strip()
            except EOFError:
                break

            # Skip empty inputs
            if not user_message:
                continue

            # Send the message to the server
            client_socket.sendall(user_message.encode("utf-8"))

            # Check if user entered an exit command
            if user_message.lower() in ("exit", "quit", "bye", "q"):
                print(f"\n{COLOR_YELLOW}[!] Disconnect command sent. Awaiting final server response...{COLOR_RESET}")
                try:
                    # Receive acknowledgment if available
                    client_socket.settimeout(2.0)
                    farewell = client_socket.recv(BUFFER_SIZE)
                    if farewell:
                        print(f"{COLOR_CYAN}{farewell.decode('utf-8').strip()}{COLOR_RESET}")
                except (socket.timeout, socket.error):
                    pass
                print(f"{COLOR_RED}[✔] Session terminated by user. Disconnected.{COLOR_RESET}")
                break

            # Receive and display server response
            response_data = client_socket.recv(BUFFER_SIZE)
            if not response_data:
                print(f"\n{COLOR_RED}[!] Server closed the connection unexpectedly.{COLOR_RESET}")
                break

            response_text = response_data.decode("utf-8").strip()
            print(f"{COLOR_BLUE}[{get_current_timestamp()}]{COLOR_RESET} {COLOR_GREEN}Server Response:{COLOR_RESET} {response_text}\n")

    except ConnectionRefusedError:
        print(f"{COLOR_RED}[✖] Connection Refused: Could not connect to {host}:{port}.{COLOR_RESET}")
        print(f"{COLOR_YELLOW}[i] Please ensure that 'server.py' is running before starting the client.{COLOR_RESET}")
    except KeyboardInterrupt:
        print(f"\n{COLOR_YELLOW}[!] KeyboardInterrupt received. Exiting client...{COLOR_RESET}")
        try:
            client_socket.sendall(b"exit")
        except socket.error:
            pass
    except Exception as exc:
        print(f"{COLOR_RED}[-] An unexpected error occurred: {exc}{COLOR_RESET}")
    finally:
        client_socket.close()
        print(f"{COLOR_CYAN}[✔] Socket closed. Client terminated.{COLOR_RESET}")


if __name__ == "__main__":
    main()
