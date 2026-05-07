import sys
import os
import time
import math
import json
import threading
import socket
import numpy as np

# Suppress Pygame welcome message
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame

# Import deep learning model
from deep_learning_model import CSIDeepLearningModel

# Default Configuration
ESP32_IP = "192.168.4.1" # Default fallback IP (configured from your AP/STA)
WS_URL = f"ws://{ESP32_IP}/ws"

class RealWorldRenderer:
    def __init__(self, ip_address):
        self.ip_address = ip_address
        self.ws_url = f"ws://{self.ip_address}/ws"
        
        # Initialize Pygame
        pygame.init()
        pygame.display.set_caption("ESP-CSI Deep Learning Real-World Digital Twin Monitor")
        self.width = 1280
        self.height = 720
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.clock = pygame.time.Clock()
        
        # Color System (Cyberpunk/Dark Room palette)
        self.colors = {
            "bg": (5, 8, 16),
            "panel": (13, 18, 34),
            "border": (30, 41, 59),
            "text": (241, 245, 249),
            "text_muted": (148, 163, 184),
            "cyan": (59, 130, 246),
            "purple": (139, 92, 246),
            "green": (16, 185, 129),
            "orange": (245, 158, 11),
            "red": (239, 68, 68),
            "grid": (15, 23, 42),
            "wood": (34, 25, 20),
            "wood_light": (46, 35, 28)
        }
        
        # Setup fonts with graceful fallback (bypasses Windows registry-scanning bugs in older Pygame versions)
        def load_safe_font(name, size, bold=False):
            try:
                return pygame.font.SysFont(name, size, bold=bold)
            except Exception:
                return pygame.font.Font(None, size)

        self.fonts = {
            "title": load_safe_font("Segoe UI", 20, bold=True),
            "header": load_safe_font("Segoe UI", 16, bold=True),
            "body": load_safe_font("Segoe UI", 14),
            "mono": load_safe_font("Consolas", 12),
            "digital": load_safe_font("Consolas", 28, bold=True)
        }
        
        # Initialize deep learning model
        self.num_subcarriers = 64
        self.ai_model = CSIDeepLearningModel(num_subcarriers=self.num_subcarriers)
        
        # Thread shared states
        self.latest_metrics = {
            "amplitude": 0.0,
            "variance": 0.0,
            "packet_count": 0,
            "subcarriers": [0.0] * self.num_subcarriers,
            "subcarriers_phase": [0.0] * self.num_subcarriers
        }
        
        # UDP JSON/OSC Broadcast Setup (for Unity / Unreal Engine 5)
        self.udp_broadcast_enabled = True
        self.udp_ip = "127.0.0.1"
        self.udp_port = 5005
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            print(f"[UDP Broadcaster] Socket configured successfully. Broadcasting to {self.udp_ip}:{self.udp_port}")
        except Exception as e:
            print(f"[UDP Broadcaster Error] {e}")
            self.udp_broadcast_enabled = False
        self.packet_rate = 0
        self.last_packet_count = 0
        self.last_rate_time = time.time()
        self.connected = False
        
        # Real-time state smoothing for visual elements
        self.current_state_code = 0
        self.current_state_text = "NoMotion"
        self.target_coords = (0.5, 0.5)
        self.smooth_coords = [0.5, 0.5] # for easing animations
        
        # Spectrogram history queue
        self.spectrogram_history_len = 100
        self.spectrogram_matrix = np.zeros((self.spectrogram_history_len, self.num_subcarriers))
        
        # Isometric coordinate factors
        self.iso_scale = 180
        self.iso_origin_x = 360
        self.iso_origin_y = 440
        
        # Particle System for WiFi waves
        self.particles = []
        self.antenna_waves = []
        self.frame_count = 0
        
        # Calibration State Machine
        self.calibration_state = 0 # 0=Normal, 1=Couch pre-rec, 2=Couch rec active, 3=TV pre-rec, ...
        self.calib_samples_x = []
        self.calib_samples_y_class = []
        self.calib_samples_y_coord = []
        self.calib_progress = 0
        self.calib_max_samples = 120 # ~6 seconds at 20Hz
        
        # Start background listener thread
        self.ws_thread = threading.Thread(target=self._websocket_listener, daemon=True)
        self.ws_thread.start()

    def _websocket_listener(self):
        """
        Background listener to pull real-time CSI JSON streams via WebSockets.
        """
        import websocket
        while True:
            try:
                print(f"[WS Connection] Connecting to {self.ws_url}...")
                ws = websocket.WebSocket()
                ws.connect(self.ws_url)
                self.connected = True
                print("[WS Connection] Established successfully.")
                
                # Request Loop at 30Hz
                while True:
                    ws.send("get")
                    response = ws.recv()
                    data = json.loads(response)
                    
                    # Store latest data
                    self.latest_metrics["amplitude"] = data.get("amplitude", 0.0)
                    self.latest_metrics["variance"] = data.get("variance", 0.0)
                    self.latest_metrics["packet_count"] = data.get("packet_count", 0)
                    
                    subcarriers = data.get("subcarriers", [])
                    if len(subcarriers) > 0:
                        self.latest_metrics["subcarriers"] = subcarriers
                        
                    phases = data.get("subcarriers_phase", [])
                    if len(phases) > 0:
                        self.latest_metrics["subcarriers_phase"] = phases
                    
                    # Throttling
                    time.sleep(0.033)
                    
            except Exception as e:
                self.connected = False
                print(f"[WS Connection] Lost connection: {e}. Retrying in 3 seconds...")
                time.sleep(3.0)

    def _to_iso(self, x, y, z=0):
        """
        Converts normalized 2D coordinates (x, y) in range [0, 1] to 3D isometric projection coordinates on screen.
        """
        # Center coordinates to [-0.5, 0.5]
        nx = (x - 0.5) * 2.0
        ny = (y - 0.5) * 2.0
        
        # Isometric formulas
        iso_x = (nx - ny) * math.cos(math.radians(30))
        iso_y = (nx + ny) * math.sin(math.radians(30)) - (z / 200.0)
        
        screen_x = int(self.iso_origin_x + iso_x * self.iso_scale)
        screen_y = int(self.iso_origin_y + iso_y * self.iso_scale)
        return screen_x, screen_y

    def run(self):
        running = True
        while running:
            # 1. Handle user inputs
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    # Allow manual testing with keyboard when ESP32 is not connected!
                    elif event.key == pygame.K_0:
                        self.latest_metrics["variance"] = 0.5
                    elif event.key == pygame.K_1:
                        self.latest_metrics["variance"] = 3.5
                    elif event.key == pygame.K_2:
                        self.latest_metrics["variance"] = 18.0
                    elif event.key == pygame.K_c:
                        # Toggle Calibration Mode
                        if self.calibration_state == 0:
                            self.calibration_state = 1
                            self.calib_samples_x = []
                            self.calib_samples_y_class = []
                            self.calib_samples_y_coord = []
                        else:
                            self.calibration_state = 0 # Abort
                    elif event.key == pygame.K_SPACE:
                        # Start recording current step
                        if self.calibration_state == 1:
                            self.calibration_state = 2
                            self.calib_progress = 0
                        elif self.calibration_state == 3:
                            self.calibration_state = 4
                            self.calib_progress = 0
                        elif self.calibration_state == 5:
                            self.calibration_state = 6
                            self.calib_progress = 0
                        elif self.calibration_state == 7:
                            self.calibration_state = 8
                            self.calib_progress = 0
                    elif event.key == pygame.K_RETURN:
                        # Accept and exit calibration
                        if self.calibration_state in [10, 11]:
                            self.calibration_state = 0

            # 2. Update logic and run AI Model
            self._update_and_infer()

            # 3. Draw screen layers
            self.screen.fill(self.colors["bg"])
            
            # Divide screen to 2 panels: Left (3D Real-World), Right (Scientific Spectrograms)
            self._draw_isometric_room()
            self._draw_scientific_dashboard()
            
            # Draw Calibration Overlays
            self._draw_calibration_hud()
            
            # Render frame
            pygame.display.flip()
            self.clock.tick(60)
            self.frame_count += 1
            
        pygame.quit()
        sys.exit()

    def _update_and_infer(self):
        """
        Calculates packet rates, feeds subcarriers into Deep Learning inference,
        and manages visual animation states.
        """
        now = time.time()
        if now - self.last_rate_time >= 1.0:
            count = self.latest_metrics["packet_count"]
            self.packet_rate = count - self.last_packet_count
            self.last_packet_count = count
            self.last_rate_time = now
            
        # Run deep learning inference
        subcarrier_amps = self.latest_metrics["subcarriers"]
        subcarrier_phases = self.latest_metrics.get("subcarriers_phase")
        self.current_state_code, self.target_coords, amps = self.ai_model.process_new_packet(subcarrier_amps, subcarrier_phases)
        
        # --- CALIBRATION DATA GATHERING (MAIN THREAD) ---
        if self.calibration_state in [2, 4, 6, 8]:
            if len(self.ai_model.csi_buffer) == self.ai_model.sequence_length:
                seq_data = np.array(self.ai_model.csi_buffer, dtype=np.float32)
                
                # Check for new packet count to avoid duplicate recording
                if not hasattr(self, "last_recorded_packet_count"):
                    self.last_recorded_packet_count = -1
                
                current_pc = self.latest_metrics["packet_count"]
                if current_pc != self.last_recorded_packet_count:
                    self.last_recorded_packet_count = current_pc
                    self.calib_samples_x.append(seq_data)
                    
                    # Labels and coords based on calibration step
                    if self.calibration_state == 2: # Couch Zone
                        self.calib_samples_y_class.append(1)
                        self.calib_samples_y_coord.append([0.25, 0.35])
                    elif self.calibration_state == 4: # TV Zone
                        self.calib_samples_y_class.append(2)
                        self.calib_samples_y_coord.append([0.75, 0.65])
                    elif self.calibration_state == 6: # Center
                        self.calib_samples_y_class.append(2)
                        self.calib_samples_y_coord.append([0.5, 0.5])
                    elif self.calibration_state == 8: # Vacant
                        self.calib_samples_y_class.append(0)
                        self.calib_samples_y_coord.append([0.5, 0.5])
                        
                    self.calib_progress += 1
                    if self.calib_progress >= self.calib_max_samples:
                        self.calibration_state += 1 # Transition state (2->3, 4->5, 6->7, 8->9)
                        if self.calibration_state == 9:
                            self._trigger_training()
        
        # Map state code to text representation
        state_map = {0: "NoMotion", 1: "MinorMotion (Breathing)", 2: "MajorMotion (Walking)"}
        self.current_state_text = state_map.get(self.current_state_code, "NoMotion")
        
        # Smooth coordinates with exponential easing (lerp)
        self.smooth_coords[0] += (self.target_coords[0] - self.smooth_coords[0]) * 0.08
        self.smooth_coords[1] += (self.target_coords[1] - self.smooth_coords[1]) * 0.08
        
        # Broadcast via UDP JSON/OSC for external 3D game engines (Unity / Unreal Engine 5)
        if self.udp_broadcast_enabled:
            try:
                payload = {
                    "timestamp": time.time(),
                    "state_code": int(self.current_state_code),
                    "state_text": self.current_state_text,
                    "x": float(self.smooth_coords[0]),
                    "y": float(self.smooth_coords[1]),
                    "variance": float(self.latest_metrics["variance"])
                }
                msg_bytes = json.dumps(payload).encode("utf-8")
                self.udp_socket.sendto(msg_bytes, (self.udp_ip, self.udp_port))
            except Exception:
                pass
        
        # Roll the spectrogram matrix
        self.spectrogram_matrix = np.roll(self.spectrogram_matrix, -1, axis=0)
        self.spectrogram_matrix[-1, :] = amps

    def _draw_isometric_room(self):
        """
        Renders a gorgeous realistic isometric bedroom/living room scene.
        """
        # Outer room boundary card background
        room_panel_rect = pygame.Rect(15, 15, 700, 690)
        pygame.draw.rect(self.screen, self.colors["panel"], room_panel_rect, border_radius=16)
        pygame.draw.rect(self.screen, self.colors["border"], room_panel_rect, width=1, border_radius=16)
        
        # Panel Title
        title_surf = self.fonts["title"].render("🌐 Real-World 3D Digital Twin Simulation (Living Room)", True, self.colors["text"])
        self.screen.blit(title_surf, (30, 30))
        
        # Draw isometric room floor tiles (realistic wooden floor texture)
        grid_res = 12
        for i in range(grid_res):
            for j in range(grid_res):
                x_val_0 = i / grid_res
                x_val_1 = (i + 1) / grid_res
                y_val_0 = j / grid_res
                y_val_1 = (j + 1) / grid_res
                
                pt_a = self._to_iso(x_val_0, y_val_0)
                pt_b = self._to_iso(x_val_1, y_val_0)
                pt_c = self._to_iso(x_val_1, y_val_1)
                pt_d = self._to_iso(x_val_0, y_val_1)
                
                # Checkered floorboard colors for wooden deck texture
                tile_color = self.colors["wood"] if (i + j) % 2 == 0 else self.colors["wood_light"]
                pygame.draw.polygon(self.screen, tile_color, [pt_a, pt_b, pt_c, pt_d])
                pygame.draw.polygon(self.screen, (20, 15, 12), [pt_a, pt_b, pt_c, pt_d], width=1)
                
        # Draw Isometric Walls (left wall and right wall)
        wall_h = 100
        wall_l_a = self._to_iso(0, 0)
        wall_l_b = self._to_iso(0, 1)
        wall_l_c = self._to_iso(0, 1, wall_h)
        wall_l_d = self._to_iso(0, 0, wall_h)
        pygame.draw.polygon(self.screen, (20, 26, 42), [wall_l_a, wall_l_b, wall_l_c, wall_l_d])
        pygame.draw.polygon(self.screen, self.colors["border"], [wall_l_a, wall_l_b, wall_l_c, wall_l_d], width=1)
        
        wall_r_a = self._to_iso(0, 1)
        wall_r_b = self._to_iso(1, 1)
        wall_r_c = self._to_iso(1, 1, wall_h)
        wall_r_d = self._to_iso(0, 1, wall_h)
        pygame.draw.polygon(self.screen, (25, 33, 52), [wall_r_a, wall_r_b, wall_r_c, wall_r_d])
        pygame.draw.polygon(self.screen, self.colors["border"], [wall_r_a, wall_r_b, wall_r_c, wall_r_d], width=1)
        
        # RENDER FURNITURE MODELS (using isometric projection)
        # Couch (located around x=[0.2, 0.4], y=[0.2, 0.6])
        couch_color = (64, 46, 82)
        c_p1 = self._to_iso(0.15, 0.2)
        c_p2 = self._to_iso(0.4, 0.2)
        c_p3 = self._to_iso(0.4, 0.6)
        c_p4 = self._to_iso(0.15, 0.6)
        c_p1_up = self._to_iso(0.15, 0.2, 25)
        c_p2_up = self._to_iso(0.4, 0.2, 25)
        c_p3_up = self._to_iso(0.4, 0.6, 25)
        c_p4_up = self._to_iso(0.15, 0.6, 25)
        pygame.draw.polygon(self.screen, couch_color, [c_p1, c_p2, c_p3, c_p4])
        pygame.draw.polygon(self.screen, (84, 61, 107), [c_p1_up, c_p2_up, c_p3_up, c_p4_up])
        pygame.draw.polygon(self.screen, couch_color, [c_p1, c_p2, c_p2_up, c_p1_up])
        pygame.draw.polygon(self.screen, couch_color, [c_p2, c_p3, c_p3_up, c_p2_up])
        pygame.draw.polygon(self.screen, couch_color, [c_p3, c_p4, c_p4_up, c_p3_up])
        
        # Flat TV Screen (on the right wall, x=0.9, y=0.4 to 0.7)
        tv_color = (15, 23, 42)
        tv_p1 = self._to_iso(0.9, 0.4, 30)
        tv_p2 = self._to_iso(0.9, 0.7, 30)
        tv_p3 = self._to_iso(0.9, 0.7, 75)
        tv_p4 = self._to_iso(0.9, 0.4, 75)
        pygame.draw.polygon(self.screen, tv_color, [tv_p1, tv_p2, tv_p3, tv_p4])
        pygame.draw.polygon(self.screen, self.colors["text_muted"], [tv_p1, tv_p2, tv_p3, tv_p4], width=1)
        
        # Room Accessories labels
        lbl_tv = self.fonts["mono"].render("TV", True, self.colors["text_muted"])
        self.screen.blit(lbl_tv, self._to_iso(0.91, 0.55, 50))
        lbl_couch = self.fonts["mono"].render("COUCH", True, self.colors["text_muted"])
        self.screen.blit(lbl_couch, self._to_iso(0.27, 0.4, 30))
        
        # --- DRAW COEXISTING ROUTER TX & ESP32 RX NODES ---
        # Router TX (located at bottom wall, x=0, y=0.5)
        tx_pos = self._to_iso(0.05, 0.5, 30)
        pygame.draw.circle(self.screen, self.colors["cyan"], tx_pos, 8)
        pygame.draw.circle(self.screen, self.colors["bg"], tx_pos, 4)
        
        # ESP32 RX (located at opposite wall, x=0.95, y=0.5)
        rx_pos = self._to_iso(0.95, 0.5, 30)
        pygame.draw.circle(self.screen, self.colors["purple"], rx_pos, 8)
        pygame.draw.circle(self.screen, self.colors["bg"], rx_pos, 4)
        
        # Antennas wave propagation ring emitters
        if self.frame_count % 40 == 0:
            self.antenna_waves.append({"pos": (0.05, 0.5), "r": 0, "color": self.colors["cyan"]})
        
        # Draw emitting WiFi rings
        for r_wave in self.antenna_waves[:]:
            r_wave["r"] += 0.012
            if r_wave["r"] > 1.5:
                self.antenna_waves.remove(r_wave)
                continue
            
            # Renders 16 point circle along isometric plane
            steps = 24
            pts = []
            for s in range(steps):
                theta = math.radians(s * (360 / steps))
                rad_x = r_wave["pos"][0] + r_wave["r"] * math.cos(theta)
                rad_y = r_wave["pos"][1] + r_wave["r"] * math.sin(theta)
                if 0 <= rad_x <= 1 and 0 <= rad_y <= 1:
                    pts.append(self._to_iso(rad_x, rad_y, 30))
            if len(pts) > 2:
                # Fade color based on radius
                alpha = int(255 * (1.0 - (r_wave["r"] / 1.5)))
                pygame.draw.lines(self.screen, (*r_wave["color"], alpha), False, pts, width=1)

        # --- DRAW GRAPHICAL SKELETON AVATAR (REAL-WORLD DIGITAL TWIN TARGET) ---
        if self.current_state_code > 0:
            hx, hy = self.smooth_coords[0], self.smooth_coords[1]
            
            # Draw Projected 3D Laser Tracker Target Ring on Floor (z = 0)
            floor_theme = self.colors["orange"] if self.current_state_code == 1 else self.colors["red"]
            ring_steps = 12
            ring_pts = []
            for s in range(ring_steps):
                theta = math.radians(s * (360 / ring_steps))
                rx = hx + 0.08 * math.cos(theta)
                ry = hy + 0.08 * math.sin(theta)
                ring_pts.append(self._to_iso(rx, ry, 0))
            
            # Projected target ring outlines for glowing vector HUD effect
            pygame.draw.polygon(self.screen, floor_theme, ring_pts, width=2)
            
            # Target Crosshair lines on floor
            pt_left = self._to_iso(hx - 0.12, hy, 0)
            pt_right = self._to_iso(hx + 0.12, hy, 0)
            pt_top = self._to_iso(hx, hy - 0.12, 0)
            pt_bottom = self._to_iso(hx, hy + 0.12, 0)
            pygame.draw.line(self.screen, floor_theme, pt_left, pt_right, 1)
            pygame.draw.line(self.screen, floor_theme, pt_top, pt_bottom, 1)
            
            # Breathing expansion factor (0.95 to 1.05) using sine loop
            pulse_rate = 0.1 if self.current_state_code == 1 else 0.25
            pulse_scale = 1.0 + 0.05 * math.sin(self.frame_count * pulse_rate)
            
            # Walk joint offset using frame count
            walk_swing = math.sin(self.frame_count * 0.15) if self.current_state_code == 2 else 0.0
            
            # Base skeletal height map
            sh_torso = 60
            sh_shoulders = 80
            sh_head = 95
            
            # Core joints
            joint_head = self._to_iso(hx, hy, sh_head)
            joint_neck = self._to_iso(hx, hy, sh_shoulders + 5)
            joint_shoulder_l = self._to_iso(hx - 0.04 * pulse_scale, hy + 0.04 * pulse_scale, sh_shoulders)
            joint_shoulder_r = self._to_iso(hx + 0.04 * pulse_scale, hy - 0.04 * pulse_scale, sh_shoulders)
            joint_spine_base = self._to_iso(hx, hy, sh_torso - 15)
            joint_hand_l = self._to_iso(hx - 0.08, hy + 0.08 + 0.04 * walk_swing, sh_shoulders - 20)
            joint_hand_r = self._to_iso(hx + 0.08, hy - 0.08 - 0.04 * walk_swing, sh_shoulders - 20)
            joint_foot_l = self._to_iso(hx - 0.05, hy + 0.05 + 0.06 * walk_swing, 0)
            joint_foot_r = self._to_iso(hx + 0.05, hy - 0.05 - 0.06 * walk_swing, 0)
            
            # 1. Torso/Body Glow Layer
            theme_color = self.colors["orange"] if self.current_state_code == 1 else self.colors["red"]
            pygame.draw.circle(self.screen, (*theme_color, 40), joint_neck, 25) # holographic head/torso field
            
            # 2. Draw Skeletal bones
            bone_width = 3
            pygame.draw.line(self.screen, theme_color, joint_neck, joint_spine_base, bone_width) # spine
            pygame.draw.line(self.screen, theme_color, joint_shoulder_l, joint_shoulder_r, bone_width) # collarbone
            pygame.draw.line(self.screen, theme_color, joint_shoulder_l, joint_hand_l, bone_width) # left arm
            pygame.draw.line(self.screen, theme_color, joint_shoulder_r, joint_hand_r, bone_width) # right arm
            pygame.draw.line(self.screen, theme_color, joint_spine_base, joint_foot_l, bone_width) # left leg
            pygame.draw.line(self.screen, theme_color, joint_spine_base, joint_foot_r, bone_width) # right leg
            
            # 3. Draw Joint core nodes
            pygame.draw.circle(self.screen, self.colors["text"], joint_head, 7) # head node
            pygame.draw.circle(self.screen, self.colors["text"], joint_shoulder_l, 4)
            pygame.draw.circle(self.screen, self.colors["text"], joint_shoulder_r, 4)
            pygame.draw.circle(self.screen, self.colors["text"], joint_hand_l, 3)
            pygame.draw.circle(self.screen, self.colors["text"], joint_hand_r, 3)
            pygame.draw.circle(self.screen, self.colors["text"], joint_spine_base, 4)
            pygame.draw.circle(self.screen, self.colors["text"], joint_foot_l, 3)
            pygame.draw.circle(self.screen, self.colors["text"], joint_foot_r, 3)
            
            # Label overlay above character
            lbl_user = self.fonts["mono"].render(f"HOLOGRAPHIC USER ({hx:.2f}, {hy:.2f})", True, theme_color)
            self.screen.blit(lbl_user, (joint_head[0] - 80, joint_head[1] - 30))
            
            # Multipath wave scatter collision particles for major motion walking
            if self.current_state_code == 2 and self.frame_count % 3 == 0:
                for _ in range(4):
                    self.particles.append({
                        "x": hx + (np.random.rand() - 0.5) * 0.12,
                        "y": hy + (np.random.rand() - 0.5) * 0.12,
                        "z": np.random.randint(10, 80),
                        "vx": (np.random.rand() - 0.5) * 0.015,
                        "vy": (np.random.rand() - 0.5) * 0.015,
                        "vz": np.random.rand() * 1.5,
                        "life": 1.0,
                        "color": self.colors["red"]
                    })
        else:
            # Empty baseline scan line between RX and TX
            pygame.draw.line(self.screen, (*self.colors["green"], 35), tx_pos, rx_pos, 1)

        # Draw and animate particles
        for p in self.particles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["z"] += p["vz"]
            p["life"] -= 0.02
            if p["life"] <= 0:
                self.particles.remove(p)
                continue
            
            p_scr = self._to_iso(p["x"], p["y"], p["z"])
            color_fade = tuple(int(c * p["life"]) for c in p["color"])
            pygame.draw.circle(self.screen, color_fade, p_scr, int(4 * p["life"]))

        # Status text footer in simulation
        conn_str = "Status: CONNECTED to ESP32" if self.connected else "Status: DISCONNECTED (Emulation Mode)"
        conn_color = self.colors["green"] if self.connected else self.colors["orange"]
        status_surf = self.fonts["mono"].render(conn_str, True, conn_color)
        self.screen.blit(status_surf, (30, 660))

        # --- DRAW 2D TACTICAL RADAR MINIMAP (BOTTOM RIGHT OF SIMULATION PANEL) ---
        cx, cy = 610, 580
        mr = 70
        
        # Scope Background
        pygame.draw.circle(self.screen, (10, 15, 24), (cx, cy), mr)
        pygame.draw.circle(self.screen, self.colors["border"], (cx, cy), mr, width=1)
        
        # Concentric range rings
        pygame.draw.circle(self.screen, (30, 41, 59), (cx, cy), mr // 2, width=1)
        pygame.draw.circle(self.screen, (30, 41, 59), (cx, cy), mr // 4, width=1)
        
        # Radar Crosshairs
        pygame.draw.line(self.screen, (30, 41, 59), (cx - mr, cy), (cx + mr, cy), 1)
        pygame.draw.line(self.screen, (30, 41, 59), (cx, cy - mr), (cx, cy + mr), 1)
        
        # Translate [0, 1] coordinate space to the circular radar minimap
        def to_radar_coords(rx, ry):
            sx = cx + int((rx - 0.5) * 2.0 * (mr - 12))
            sy = cy + int((ry - 0.5) * 2.0 * (mr - 12))
            return sx, sy
            
        # Draw Couch and TV area projection on radar scope
        c_tl = to_radar_coords(0.15, 0.2)
        c_br = to_radar_coords(0.4, 0.6)
        couch_rect = pygame.Rect(c_tl[0], c_tl[1], c_br[0] - c_tl[0], c_br[1] - c_tl[1])
        pygame.draw.rect(self.screen, (34, 25, 48), couch_rect, border_radius=4)
        pygame.draw.rect(self.screen, (139, 92, 246), couch_rect, width=1, border_radius=4)
        
        tv_top = to_radar_coords(0.9, 0.4)
        tv_bot = to_radar_coords(0.9, 0.7)
        pygame.draw.line(self.screen, self.colors["cyan"], tv_top, tv_bot, 2)
        
        # Animate sweeping radar line
        sweep_angle = math.radians(self.frame_count * 2)
        sw_x = cx + int(mr * math.cos(sweep_angle))
        sw_y = cy + int(mr * math.sin(sweep_angle))
        pygame.draw.line(self.screen, (16, 185, 129), (cx, cy), (sw_x, sw_y), 1)
        
        # Draw antenna nodes
        tx_rad = to_radar_coords(0.05, 0.5)
        rx_rad = to_radar_coords(0.95, 0.5)
        pygame.draw.circle(self.screen, self.colors["cyan"], tx_rad, 3)
        pygame.draw.circle(self.screen, self.colors["purple"], rx_rad, 3)
        
        # Plot target pointer
        hx, hy = self.smooth_coords[0], self.smooth_coords[1]
        tx_x, tx_y = to_radar_coords(hx, hy)
        
        if self.current_state_code > 0:
            target_color = self.colors["orange"] if self.current_state_code == 1 else self.colors["red"]
            p_radius = 5 + int(4 * (1.0 + math.sin(self.frame_count * 0.25)))
            pygame.draw.circle(self.screen, target_color, (tx_x, tx_y), p_radius, width=1)
            pygame.draw.circle(self.screen, self.colors["text"], (tx_x, tx_y), 3)
            
            # Position Sector tag
            if hx < 0.45 and hy < 0.45:
                tag = "COUCH"
            elif hx > 0.55 and hy > 0.55:
                tag = "TV ZONE"
            else:
                tag = "CENTER"
            lbl_tr = self.fonts["mono"].render(f"LOCKED: {tag}", True, target_color)
            self.screen.blit(lbl_tr, (cx - mr, cy - mr - 16))
        else:
            pygame.draw.circle(self.screen, self.colors["green"], to_radar_coords(0.5, 0.5), 3)
            
        lbl_radar = self.fonts["mono"].render("2D TACTICAL LOCATOR", True, self.colors["text_muted"])
        self.screen.blit(lbl_radar, (cx - mr, cy + mr + 6))

    def _draw_scientific_dashboard(self):
        """
        Renders the Scientific analysis dashboard, complete with CSI Waterfall Spectrogram,
        real-time subcarriers amplitude curves, and Deep Learning logits.
        """
        # Outer right panel background card
        panel_rect = pygame.Rect(730, 15, 535, 690)
        pygame.draw.rect(self.screen, self.colors["panel"], panel_rect, border_radius=16)
        pygame.draw.rect(self.screen, self.colors["border"], panel_rect, width=1, border_radius=16)
        
        # --- SECTION 1: AI ACTIVITY DEEP INFERENCE ---
        ai_title = self.fonts["header"].render("🧠 DEEP LEARNING MODEL ESTIMATION", True, self.colors["text"])
        self.screen.blit(ai_title, (755, 35))
        
        # State Indicator Card
        state_colors = {0: self.colors["green"], 1: self.colors["orange"], 2: self.colors["red"]}
        cur_color = state_colors.get(self.current_state_code, self.colors["green"])
        
        card_rect = pygame.Rect(755, 65, 485, 80)
        pygame.draw.rect(self.screen, (20, 26, 46), card_rect, border_radius=12)
        pygame.draw.rect(self.screen, cur_color, card_rect, width=2, border_radius=12)
        
        # Determine human-readable region zone name
        hx, hy = self.smooth_coords[0], self.smooth_coords[1]
        if self.current_state_code == 0:
            region_name = "VACANT"
        else:
            if hx < 0.45 and hy < 0.45:
                region_name = "Couch Zone (SE)"
            elif hx > 0.55 and hy < 0.45:
                region_name = "East Entrance"
            elif hx > 0.55 and hy > 0.55:
                region_name = "TV Cabinet (NW)"
            elif hx < 0.45 and hy > 0.55:
                region_name = "West Window"
            else:
                region_name = "Room Center"

        # Display Left Half: Activity Classification
        act_lbl = self.fonts["mono"].render("CLASSIFIED ACTIVITY", True, self.colors["text_muted"])
        self.screen.blit(act_lbl, (775, 75))
        act_val = self.fonts["digital"].render(self.current_state_text.upper(), True, cur_color)
        self.screen.blit(act_val, (775, 95))

        # Display Right Half: Target Position Sector Tracking
        pos_lbl = self.fonts["mono"].render("TARGET ZONE", True, self.colors["text_muted"])
        self.screen.blit(pos_lbl, (1020, 75))
        pos_val = self.fonts["digital"].render(region_name.upper(), True, self.colors["cyan"])
        self.screen.blit(pos_val, (1020, 95))
        
        # Numeric Stats Block
        avg_amp_lbl = self.fonts["mono"].render("AVG AMP", True, self.colors["text_muted"])
        self.screen.blit(avg_amp_lbl, (755, 160))
        avg_amp_val = self.fonts["digital"].render(f"{self.latest_metrics['amplitude']:.2f}", True, self.colors["text"])
        self.screen.blit(avg_amp_val, (755, 175))
        
        var_lbl = self.fonts["mono"].render("MOTION ENERGY", True, self.colors["text_muted"])
        self.screen.blit(var_lbl, (910, 160))
        var_val = self.fonts["digital"].render(f"{self.latest_metrics['variance']:.2f}", True, self.colors["text"])
        self.screen.blit(var_val, (910, 175))
        
        rate_lbl = self.fonts["mono"].render("SAMPLING RATE", True, self.colors["text_muted"])
        self.screen.blit(rate_lbl, (1085, 160))
        rate_val = self.fonts["digital"].render(f"{self.packet_rate} Hz", True, self.colors["cyan"])
        self.screen.blit(rate_val, (1085, 175))

        # --- SECTION 2: CSI REAL-TIME SPECTROGRAM WATERFALL ---
        spect_title = self.fonts["header"].render("⚡ HIGH-DIMENSIONAL CSI WATERFALL SPECTROGRAM", True, self.colors["text"])
        self.screen.blit(spect_title, (755, 235))
        
        # Setup matrix dimensions (height=220, width=485)
        m_x, m_y = 755, 265
        m_w, m_h = 485, 220
        
        # Draw spectrogram image onto surface
        spect_surface = pygame.Surface((self.num_subcarriers, self.spectrogram_history_len))
        
        # Map values to cold-to-hot jet spectrum
        for i in range(self.spectrogram_history_len):
            row_vals = self.spectrogram_matrix[i, :]
            # Normalization scale
            max_val = max(1.0, np.max(row_vals))
            
            for j in range(self.num_subcarriers):
                val = row_vals[j] / max_val
                # Jet colormap formula
                r = int(np.clip(255 * (val - 0.25) * 4 if val > 0.25 else 0, 0, 255))
                g = int(np.clip(255 * (1.0 - abs(val - 0.5) * 4), 0, 255))
                b = int(np.clip(255 * (0.75 - val) * 4 if val < 0.75 else 0, 0, 255))
                spect_surface.set_at((j, i), (r, g, b))
                
        # Scale to fit window screen layout
        spect_scaled = pygame.transform.scale(spect_surface, (m_w, m_h))
        self.screen.blit(spect_scaled, (m_x, m_y))
        pygame.draw.rect(self.screen, self.colors["border"], (m_x, m_y, m_w, m_h), width=1)
        
        # Spectrogram Axes labels
        sc_lbl_0 = self.fonts["mono"].render("Subcarrier 0", True, self.colors["text_muted"])
        self.screen.blit(sc_lbl_0, (m_x, m_y + m_h + 3))
        sc_lbl_max = self.fonts["mono"].render("Subcarrier 63", True, self.colors["text_muted"])
        self.screen.blit(sc_lbl_max, (m_x + m_w - 90, m_y + m_h + 3))
        time_lbl = self.fonts["mono"].render("Time", True, self.colors["text_muted"])
        # Rotate label 90 degrees
        time_lbl_rot = pygame.transform.rotate(time_lbl, 90)
        self.screen.blit(time_lbl_rot, (m_x - 18, m_y + m_h // 2 - 15))

        # --- SECTION 3: SUBCARRIER ENVELOPE PLOT ---
        env_title = self.fonts["header"].render("📈 CURRENT SUBCARRIER ENVELOPE CURVE", True, self.colors["text"])
        self.screen.blit(env_title, (755, 520))
        
        # Line graph of latest CSI packet amplitudes
        g_x, g_y = 755, 550
        g_w, g_h = 485, 120
        pygame.draw.rect(self.screen, (10, 14, 26), (g_x, g_y, g_w, g_h), border_radius=8)
        pygame.draw.rect(self.screen, self.colors["border"], (g_x, g_y, g_w, g_h), width=1, border_radius=8)
        
        # Draw background subgrid
        for k in range(1, 4):
            y_grid = g_y + (g_h // 4) * k
            pygame.draw.line(self.screen, (20, 28, 48), (g_x, y_grid), (g_x + g_w, y_grid), 1)
        for k in range(1, 8):
            x_grid = g_x + (g_w // 8) * k
            pygame.draw.line(self.screen, (20, 28, 48), (x_grid, g_y), (x_grid, g_y + g_h), 1)
            
        latest_amps = self.latest_metrics["subcarriers"]
        if len(latest_amps) > 1:
            points = []
            max_amp = max(10.0, np.max(latest_amps))
            for j in range(self.num_subcarriers):
                px = g_x + int((j / (self.num_subcarriers - 1)) * g_w)
                py = g_y + g_h - int((latest_amps[j] / max_amp) * (g_h - 20)) - 10
                points.append((px, py))
                
            pygame.draw.lines(self.screen, self.colors["cyan"], False, points, width=2)

    def _trigger_training(self):
        """
        Triggers neural network training on a background thread.
        """
        def train_runner():
            try:
                success = self.ai_model.train_on_collected_data(
                    self.calib_samples_x,
                    self.calib_samples_y_class,
                    self.calib_samples_y_coord
                )
                if success:
                    self.calibration_state = 10 # Success
                else:
                    self.calibration_state = 11 # Fail
            except Exception as e:
                print(f"[Training Error] {e}")
                self.calibration_state = 11
                
        t = threading.Thread(target=train_runner, daemon=True)
        t.start()

    def _draw_calibration_hud(self):
        if self.calibration_state == 0:
            return
            
        # Draw a semi-transparent dark frosted overlay over the room panel
        hud_w, hud_h = 520, 360
        hud_x = 15 + (700 - hud_w) // 2
        hud_y = 15 + (690 - hud_h) // 2
        
        overlay = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
        overlay.fill((8, 12, 24, 245)) # deep cyber blue transparent
        self.screen.blit(overlay, (hud_x, hud_y))
        
        # Color states based on current phase
        border_color = self.colors["cyan"]
        if self.calibration_state in [2, 4, 6, 8]:
            border_color = self.colors["orange"] # active recording
        elif self.calibration_state == 9:
            border_color = self.colors["purple"] # training
        elif self.calibration_state == 10:
            border_color = self.colors["green"] # success
        elif self.calibration_state == 11:
            border_color = self.colors["red"] # fail
            
        pygame.draw.rect(self.screen, border_color, (hud_x, hud_y, hud_w, hud_h), width=2, border_radius=16)
        
        # Title Header
        title_surf = self.fonts["title"].render("🛰️ SYSTEM CALIBRATION INTERFACE", True, self.colors["text"])
        self.screen.blit(title_surf, (hud_x + 30, hud_y + 30))
        
        # Step mappings
        steps = {
            1: ("Step 1/4: COUCH ZONE Calibration", "Please walk to or sit on the COUCH (SE). Make natural static or small movements.\n\nPress [SPACE] to start recording 120 calibration frames."),
            2: ("Step 1/4: COUCH ZONE [RECORDING ACTIVE]", "Recording... Please maintain natural posture/movement around the Couch.\n\nDo not walk away until progress reaches 100%."),
            3: ("Step 2/4: TV ZONE Calibration", "Please stand or walk around the TV CABINET area (NW).\n\nPress [SPACE] to start recording 120 calibration frames."),
            4: ("Step 2/4: TV ZONE [RECORDING ACTIVE]", "Recording... Please maintain natural posture/movement around the TV area.\n\nDo not walk away until progress reaches 100%."),
            5: ("Step 3/4: ROOM CENTER Calibration", "Please walk around the CENTER of the room freely.\n\nPress [SPACE] to start recording 120 calibration frames."),
            6: ("Step 3/4: ROOM CENTER [RECORDING ACTIVE]", "Recording... Please walk around the room center freely.\n\nDo not stop until progress reaches 100%."),
            7: ("Step 4/4: VACANT ROOM Calibration", "Please exit the sensing area or sit completely still (No Motion).\n\nPress [SPACE] to start recording 120 calibration frames."),
            8: ("Step 4/4: VACANT ROOM [RECORDING ACTIVE]", "Recording... Please stay still or keep the room completely vacant.\n\nDo not move until progress reaches 100%."),
            9: ("🤖 DEEP LEARNING MODEL TRAINING", "Auto-calibration sequences gathered successfully!\n\nPyTorch is now training the Self-Attention BiGRU model\non your CUDA GPU/CPU in the background.\n\nPlease wait a few seconds..."),
            10: ("🎉 CALIBRATION COMPLETE & SUCCESSFUL", "The Self-Attention BiGRU neural networks have been 100% successfully trained and optimized!\n\nWeights are saved to 'csi_weights.pt'.\nNeural coordinate tracking is now fully active!\n\nPress [ENTER] to return to simulation."),
            11: ("❌ CALIBRATION & TRAINING FAILED", "An unexpected error occurred during training or data gathering.\n\nPlease check the terminal log outputs.\n\nPress [ENTER] to exit calibration.")
        }
        
        step_title, step_desc = steps.get(self.calibration_state, ("Sensing Core", ""))
        
        # Render step title
        st_surf = self.fonts["header"].render(step_title, True, border_color)
        self.screen.blit(st_surf, (hud_x + 30, hud_y + 80))
        
        # Render step lines
        desc_lines = step_desc.split("\n")
        y_offset = hud_y + 120
        for line in desc_lines:
            ln_surf = self.fonts["body"].render(line, True, self.colors["text_muted"])
            self.screen.blit(ln_surf, (hud_x + 30, y_offset))
            y_offset += 24
            
        # Draw progress bar
        if self.calibration_state in [2, 4, 6, 8]:
            pct = self.calib_progress / self.calib_max_samples
            pct_text = f"{int(pct * 100)}%"
            
            pb_w, pb_h = 460, 20
            pb_x, pb_y = hud_x + 30, hud_y + 240
            pygame.draw.rect(self.screen, (20, 28, 48), (pb_x, pb_y, pb_w, pb_h), border_radius=6)
            pygame.draw.rect(self.screen, self.colors["orange"], (pb_x, pb_y, int(pb_w * pct), pb_h), border_radius=6)
            pygame.draw.rect(self.screen, self.colors["border"], (pb_x, pb_y, pb_w, pb_h), width=1, border_radius=6)
            
            p_text = self.fonts["mono"].render(f"Frames: {self.calib_progress}/{self.calib_max_samples}  ({pct_text})", True, self.colors["text"])
            self.screen.blit(p_text, (pb_x, pb_y + 25))
            
        elif self.calibration_state == 9:
            pulse = int(127 + 127 * math.sin(self.frame_count * 0.15))
            pulse_color = (pulse, 92, 246)
            pygame.draw.circle(self.screen, pulse_color, (hud_x + hud_w - 60, hud_y + 50), 10)
            
            lbl_tr = self.fonts["mono"].render("TRAINING ACTIVE IN BACKGROUND THREAD", True, (139, 92, 246))
            self.screen.blit(lbl_tr, (hud_x + 30, hud_y + 260))
            
        elif self.calibration_state == 10:
            lbl_tr = self.fonts["mono"].render("PRESS [ENTER] TO INITIATE LIVE AI TRACKING", True, self.colors["green"])
            self.screen.blit(lbl_tr, (hud_x + 30, hud_y + 280))
            
        elif self.calibration_state == 11:
            lbl_tr = self.fonts["mono"].render("PRESS [ENTER] TO DISCARD AND TRY AGAIN", True, self.colors["red"])
            self.screen.blit(lbl_tr, (hud_x + 30, hud_y + 280))
            
        # Help footer
        help_text = "Press [C] at any time to abort calibration"
        if self.calibration_state not in [10, 11]:
            help_surf = self.fonts["mono"].render(help_text, True, (80, 95, 120))
            self.screen.blit(help_surf, (hud_x + 30, hud_y + hud_h - 30))

if __name__ == "__main__":
    ip_addr = ESP32_IP
    if len(sys.argv) > 1:
        ip_addr = sys.argv[1]
    
    print("=" * 60)
    print("  ESP-CSI Deep Learning Real-World Digital Twin Render Engine")
    print("=" * 60)
    print(f"Connecting websocket target to: ws://{ip_addr}/ws")
    print("Manual Control Emulation Keyboard shortcuts (when offline):")
    print("  Press '0': Emulate NoMotion (Green)")
    print("  Press '1': Emulate MinorMotion/Breathing (Orange)")
    print("  Press '2': Emulate MajorMotion/Walking (Red)")
    print("=" * 60)
    
    renderer = RealWorldRenderer(ip_addr)
    renderer.run()
