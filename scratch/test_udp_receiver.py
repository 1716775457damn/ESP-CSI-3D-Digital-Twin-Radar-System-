import socket
import json

UDP_IP = "127.0.0.1"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print(f"[UDP Test Receiver] Listening on {UDP_IP}:{UDP_PORT}... Press Ctrl+C to stop.")

try:
    while True:
        data, addr = sock.recvfrom(1024)
        try:
            payload = json.loads(data.decode("utf-8"))
            print(f"Received from {addr}: "
                  f"State: {payload.get('state_text')} ({payload.get('state_code')}) | "
                  f"Coords: ({payload.get('x'):.3f}, {payload.get('y'):.3f}) | "
                  f"Variance: {payload.get('variance'):.3f}")
        except Exception as e:
            print(f"Raw data from {addr}: {data} (Error decoding JSON: {e})")
except KeyboardInterrupt:
    print("\n[UDP Test Receiver] Stopped by user.")
