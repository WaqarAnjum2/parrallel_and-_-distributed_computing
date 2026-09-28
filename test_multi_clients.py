"""
================================================================================
COURSE  : Parallel and Distributed Computing (CSC-334)
LAB 03  : Socket Programming with Multi-Threading
FILE    : test_multi_clients.py
PURPOSE : Automated Multi-Client Simulation Test Script.
          Spawns multiple simultaneous clients to demonstrate concurrent
          multi-threading, socket communication, and server thread locking.
================================================================================
"""

import socket
import threading
import time
import sys

HOST = "127.0.0.1"
PORT = 5000
BUFFER_SIZE = 1024


def run_simulated_client(client_id: int, messages: list) -> None:
    """Simulates a single client connecting, sending messages, and disconnecting."""
    time.sleep(0.2 * client_id)  # Stagger connections slightly
    print(f"[Sim-Client {client_id}] Connecting to {HOST}:{PORT}...")

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        local_port = s.getsockname()[1]
        print(f"[Sim-Client {client_id} (Port {local_port})] Connected!")

        # Read server welcome message
        welcome = s.recv(BUFFER_SIZE).decode("utf-8")

        for msg in messages:
            time.sleep(0.5)
            s.sendall(msg.encode("utf-8"))
            resp = s.recv(BUFFER_SIZE).decode("utf-8")
            print(f"[Sim-Client {client_id}] Sent: '{msg}' | Got: {resp.strip()}")

        # Send exit command
        time.sleep(0.5)
        s.sendall(b"exit")
        farewell = s.recv(BUFFER_SIZE).decode("utf-8")
        print(f"[Sim-Client {client_id}] Disconnected gracefully: {farewell.strip()}")
        s.close()
    except Exception as exc:
        print(f"[Sim-Client {client_id}] Error: {exc}")


def main() -> None:
    print("================================================================================")
    print("  AUTOMATED MULTI-CLIENT SIMULATION TEST (3 Simultaneous Clients)")
    print("================================================================================")

    clients_data = [
        (1, ["Hello from Client 1!", "Testing parallel processing", "Final message 1"]),
        (2, ["Greetings from Client 2!", "Multi-threading is working!", "Goodbye 2"]),
        (3, ["Client 3 reporting in!", "Thread synchronization verified", "Bye 3"]),
    ]

    threads = []
    for cid, msgs in clients_data:
        t = threading.Thread(target=run_simulated_client, args=(cid, msgs), name=f"SimClient-{cid}")
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    print("\n[✔] Multi-Client Simulation Test Finished Successfully!")


if __name__ == "__main__":
    main()
