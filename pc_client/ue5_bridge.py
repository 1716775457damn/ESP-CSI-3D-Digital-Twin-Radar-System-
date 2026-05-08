import os
import sys
import socket
import json
import time
import threading
import numpy as np

# Add parent directory to path so we can import our model
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from deep_learning_model import CSIDeepLearningModel

class UE5CSIBridge:
    """
    SOTA Unreal Engine 5 Real-Time Digital Twin Telemetry Bridge.
    Listens to ESP32-S3 CSI UDP stream, processes signals with SOTA AoA-ToF polar tracking,
    and broadcasts structured JSON packets over a local UDP port for UE5 Blueprints / C++ to consume.
    """
    def __init__(self, esp32_ip="0.0.0.0", esp32_port=5555, ue5_ip="127.0.0.1", ue5_port=12345):
        self.esp32_ip = esp32_ip
        self.esp32_port = esp32_port
        self.ue5_ip = ue5_ip
        self.ue5_port = ue5_port
        
        # Initialize our 10-gen SOTA DSP and AoA-ToF Estimator
        self.ai_model = CSIDeepLearningModel()
        
        # State
        self.running = False
        self.latest_data = {
            "subcarriers": [10.0] * 64,
            "subcarriers_phase": [0.0] * 64,
            "packet_count": 0
        }
        
    def start(self):
        self.running = True
        
        # Socket to receive from ESP32 (listen on all interfaces)
        self.esp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Reuse address to allow co-existence with realworld_renderer
        self.esp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.esp_sock.bind(("0.0.0.0", 5555))
        print(f"[UE5 Bridge] Listening for ESP32 stream on port 5555...")
        
        # Socket to broadcast to UE5
        self.ue_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"[UE5 Bridge] Telemetry output configured for UE5 on {self.ue5_ip}:{self.ue5_port}")
        
        # Start receiver thread
        self.recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self.recv_thread.start()
        
        # Start broadcast loop
        self._broadcast_loop()
        
    def _recv_loop(self):
        while self.running:
            try:
                data, addr = self.esp_sock.recvfrom(4096)
                # Parse custom ESP32 CSI binary frame
                # Custom frame: [magic_byte, packet_idx, 64_amps..., 64_phases...]
                if len(data) >= 130:
                    packet_count = (data[1] << 8) | data[2]
                    
                    # Extract 64 amplitudes (bytes 3 to 66)
                    amps = [float(b) for b in data[3:67]]
                    
                    # Extract 64 phases (bytes 67 to 130)
                    phases = []
                    for i in range(64):
                        p_byte = data[67 + i]
                        # map raw byte back to phase [-pi, pi]
                        phases.append(float((p_byte / 255.0) * 2 * np.pi - np.pi))
                        
                    self.latest_data = {
                        "subcarriers": amps,
                        "subcarriers_phase": phases,
                        "packet_count": packet_count
                    }
            except Exception as e:
                pass
                
    def _broadcast_loop(self):
        print("[UE5 Bridge] Live Link Broadcast loop running at 60 FPS...")
        while self.running:
            start_time = time.time()
            
            amps = self.latest_data["subcarriers"]
            phases = self.latest_data["subcarriers_phase"]
            
            # Run SOTA DSP & High-Fidelity AoA-ToF Estimator
            state_code, coords, smoothed_amps = self.ai_model.process_new_packet(amps, phases)
            
            # Map state code to text
            states = {0: "Vacant", 1: "Breathing/Typing", 2: "Walking/Motion"}
            state_text = states.get(state_code, "Unknown")
            
            # Construct a premium, highly structured JSON telemetry packet
            payload = {
                "timestamp": time.time(),
                "packet_id": self.latest_data["packet_count"],
                "target": {
                    "is_active": state_code > 0,
                    "state_code": state_code,
                    "state_text": state_text,
                    "x": coords[0], # Normalized cartesian [0, 1] relative to center
                    "y": coords[1],
                    "unreal_x": (coords[0] - 0.5) * 1000.0, # Mapped to Unreal centimeters (-500cm to 500cm)
                    "unreal_y": (coords[1] - 0.5) * 1000.0,
                },
                # Spatial subcarriers split (amplitudes)
                "subspaces": {
                    "sub_a": list(smoothed_amps[0:22]),
                    "sub_b": list(smoothed_amps[22:43]),
                    "sub_c": list(smoothed_amps[43:64])
                },
                # Full 64 amplitudes array for driving UE5 Niagara / Materials
                "spectrum_amplitudes": list(smoothed_amps)
            }
            
            # Send payload to UE5 via UDP
            try:
                msg_bytes = json.dumps(payload).encode('utf-8')
                self.ue_sock.sendto(msg_bytes, (self.ue5_ip, self.ue5_port))
            except Exception as e:
                print(f"[UE5 Bridge Broadcast Error] {e}")
                
            # Cap at 60Hz matching standard UE5 frame rate
            elapsed = time.time() - start_time
            sleep_dur = max(0.001, 1.0/60.0 - elapsed)
            time.sleep(sleep_dur)

if __name__ == "__main__":
    esp_ip = "0.0.0.0"
    if len(sys.argv) > 1:
        esp_ip = sys.argv[1]
    
    bridge = UE5CSIBridge(esp32_ip=esp_ip)
    try:
        bridge.start()
    except KeyboardInterrupt:
        print("\n[UE5 Bridge] Exiting...")
        bridge.running = False
