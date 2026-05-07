import os
import numpy as np

# Try to import torch, fallback to high-fidelity numpy representation if not installed
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torch.optim as optim
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

class CSIDeepLearningModel:
    """
    SOTA Self-Attention Bidirectional GRU (BiGRU) Network for WiFi Sensing.
    Includes Digital Signal Processing (DSP) filters for high-reliability motion classification.
    
    DSP Pipeline:
    1. First-Order Low-Pass EMA Filter: Smooths out high-frequency RF thermal noise and antenna jitter,
       leaving only genuine human physical movement.
    2. Adaptive Calibration & Safe Bound Limits: Prevents static environmental baseline drift from triggering false positives.
    3. Physical Coordinate Estimator: Computes real-time coordinates using Spectral Centroid and Proximity Attenuation,
       providing instant movement feedback before neural network training is completed.
    """
    def __init__(self, num_subcarriers=64, sequence_length=12, num_classes=3):
        self.num_subcarriers = num_subcarriers
        self.sequence_length = sequence_length # Reduced from 20 to 12 for split-second static state responsiveness
        self.num_classes = num_classes
        
        # Buffer to hold rolling sequence for model input
        self.csi_buffer = []
        self.phase_buffer = []
        
        # DSP Filter States
        self.smoothed_amplitudes = None
        self.smoothed_phases = None
        self.ema_alpha = 0.30 # Low pass filter coeff (lower = more smoothing, less high-frequency RF noise)
        
        # Self-calibrating threshold states
        self.noise_floor_buffer = []
        self.adaptive_baseline = 1.0
        
        # SOTA Vital Signs Monitoring Engine
        self.vitals_estimator = CSIVitalSignsEstimator(num_subcarriers=self.num_subcarriers)
        self.latest_vitals = (72.0, 15.0, np.zeros(256, dtype=np.float32), np.zeros(256, dtype=np.float32), "Initializing...")
        
        if HAS_TORCH:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = self._build_pytorch_model().to(self.device)
            
            # Auto-load weights if they exist (indicating model has been trained)
            if os.path.exists("csi_weights.pt"):
                try:
                    self.model.load_state_dict(torch.load("csi_weights.pt", map_location=self.device))
                    self.is_trained = True
                    print("[SOTA AI Model] Pre-trained weights loaded successfully. Neural regression is active.")
                except Exception as e:
                    self.is_trained = False
                    print(f"[SOTA AI Model] Failed to load csi_weights.pt ({e}). Fallback to physical coordinate estimation.")
            else:
                self.is_trained = False
                print("[SOTA AI Model] Model is untrained. Dynamic physical coordinate estimator is active.")
                
            self.model.eval()
        else:
            self.model = None
            self.is_trained = False
            print("[SOTA AI Model] PyTorch not found. Running Self-Calibrating Physical Coordinate Estimator.")

    def _build_pytorch_model(self):
        """
        SOTA Subcarrier-Attention BiGRU Architecture.
        """
        class SubcarrierAttention(nn.Module):
            def __init__(self, channels):
                super().__init__()
                self.query = nn.Linear(channels, channels)
                self.key = nn.Linear(channels, channels)
                self.value = nn.Linear(channels, channels)
                
            def forward(self, x):
                # x shape: (batch_size, seq_len, channels)
                q = self.query(x)
                k = self.key(x)
                v = self.value(x)
                
                # Attention scores
                scores = torch.matmul(q, k.transpose(-2, -1)) / np.sqrt(x.size(-1))
                weights = F.softmax(scores, dim=-1)
                
                # Weighted representations
                return torch.matmul(weights, v)

        class AttentionBiGRUNet(nn.Module):
            def __init__(self, num_subcarriers, seq_len, num_classes):
                super().__init__()
                # 1. Spatial Feature Extraction & Channel Attention
                self.spatial_conv = nn.Conv1d(in_channels=1, out_channels=32, kernel_size=3, padding=1)
                self.conv_relu = nn.ReLU()
                
                # 2. Channel Self-Attention over 32 feature maps
                self.channel_attention = SubcarrierAttention(32)
                
                # 3. Bidirectional GRU (Temporal Sequence Extractor)
                self.gru = nn.GRU(
                    input_size=32 * num_subcarriers, 
                    hidden_size=64, 
                    num_layers=2, 
                    batch_first=True,
                    bidirectional=True
                )
                
                # BiGRU has hidden_size * 2 = 128 dimensions
                # 4. Dense Classifier and Regressor Heads
                self.fc_class = nn.Sequential(
                    nn.Linear(128, 32),
                    nn.ReLU(),
                    nn.Linear(32, num_classes)
                )
                
                self.fc_coord = nn.Sequential(
                    nn.Linear(128, 32),
                    nn.ReLU(),
                    nn.Linear(32, 2)
                )

            def forward(self, x):
                # Input: (batch_size, seq_len, subcarriers)
                batch_size, seq_len, subcarriers = x.size()
                
                # Conv1D feature extraction
                x_reshaped = x.view(batch_size * seq_len, 1, subcarriers)
                feat = self.conv_relu(self.spatial_conv(x_reshaped)) # (B * T, 32, subcarriers)
                
                # Reshape to apply Channel Attention
                feat = feat.transpose(1, 2) # (B * T, subcarriers, 32)
                feat_attn = self.channel_attention(feat) # Self-attention over features
                
                # Reshape back for GRU input
                gru_in = feat_attn.reshape(batch_size, seq_len, -1) # (B, T, subcarriers * 32)
                
                # Forward Bidirectional GRU
                gru_out, _ = self.gru(gru_in) # (B, T, hidden_size * 2)
                
                # Global pooling over temporal dimension (highly sensitive to transient shifts)
                pooled_state = torch.mean(gru_out, dim=1) # (B, 128)
                
                # Outputs
                class_logits = self.fc_class(pooled_state)
                coords = self.fc_coord(pooled_state)
                
                return class_logits, coords
                
        return AttentionBiGRUNet(self.num_subcarriers, self.sequence_length, self.num_classes)

    def _estimate_physical_coords(self):
        """
        Deterministic physical target tracking. 
        Uses subcarrier diffraction patterns (Spectral Centroid) and proximity signal attenuation.
        """
        if self.smoothed_amplitudes is None:
            return 0.5, 0.5
            
        # 1. Calculate Spectral Centroid (reflects diffraction shifts as you move between TX and RX)
        indices = np.arange(self.num_subcarriers)
        sum_amp = np.sum(self.smoothed_amplitudes)
        if sum_amp <= 1e-4:
            return 0.5, 0.5
        centroid = np.sum(indices * self.smoothed_amplitudes) / sum_amp
        
        # Expected room boundary centroid limits mapped to X position in [0.2, 0.8]
        norm_x = (centroid - 26.5) / 11.0
        pred_x = 0.2 + 0.6 * norm_x
        
        # 2. Calculate Proximity Attenuation (reflects distance to the main line-of-sight path)
        avg_amp = np.mean(self.smoothed_amplitudes)
        
        # Expected average amplitude boundary limits mapped to Y position in [0.2, 0.8]
        norm_y = (avg_amp - 6.5) / 13.0
        pred_y = 0.2 + 0.6 * norm_y
        
        pred_x = float(np.clip(pred_x, 0.15, 0.85))
        pred_y = float(np.clip(pred_y, 0.15, 0.85))
        
        return pred_x, pred_y

    def sanitize_phase(self, raw_phase):
        """
        Applies Phase Unwrapping and Linear Phase Calibration (remedies CFO & SFO).
        """
        if raw_phase is None or len(raw_phase) == 0:
            return np.zeros(self.num_subcarriers, dtype=np.float32)
            
        raw_phase = np.array(raw_phase, dtype=np.float32)
        if len(raw_phase) != self.num_subcarriers:
            if len(raw_phase) < self.num_subcarriers:
                raw_phase = np.pad(raw_phase, (0, self.num_subcarriers - len(raw_phase)), 'edge')
            else:
                raw_phase = raw_phase[:self.num_subcarriers]
                
        # 1. Unwrap phase (remove 2pi phase wrap jumps)
        unwrapped = np.unwrap(raw_phase)
        
        # 2. Linear fit correction (SFO & CFO mitigation)
        n = len(unwrapped)
        m = np.arange(n) - (n - 1) / 2.0 # center indices around zero
        
        mean_theta = np.mean(unwrapped)
        mean_m = np.mean(m)
        
        # Slope (a) and Intercept (b) via Least Squares
        num = np.sum((m - mean_m) * (unwrapped - mean_theta))
        den = np.sum((m - mean_m) ** 2)
        if den == 0:
            return unwrapped
            
        a = num / den
        b = mean_theta - a * mean_m
        
        # Sanitized phase: remove the linear CFO/SFO shift component
        sanitized = unwrapped - a * m - b
        return sanitized

    def process_new_packet(self, subcarrier_amplitudes, subcarrier_phases=None):
        """
        Appends packet, runs high-sensitivity BiGRU inference with adaptive self-calibrating thresholds
        and real-time SFO/CFO-corrected SOTA Phase Unwrapping.
        """
        # Ensure correct vector length
        if len(subcarrier_amplitudes) != self.num_subcarriers:
            if len(subcarrier_amplitudes) < self.num_subcarriers:
                subcarrier_amplitudes = np.pad(subcarrier_amplitudes, (0, self.num_subcarriers - len(subcarrier_amplitudes)), 'edge')
            else:
                subcarrier_amplitudes = subcarrier_amplitudes[:self.num_subcarriers]

        raw_vector = np.array(subcarrier_amplitudes, dtype=np.float32)

        # --- DSP 1st-Order Low-Pass EMA Filter ---
        if self.smoothed_amplitudes is None:
            self.smoothed_amplitudes = raw_vector
        else:
            self.smoothed_amplitudes = self.ema_alpha * raw_vector + (1.0 - self.ema_alpha) * self.smoothed_amplitudes

        # Store smoothed signals inside the temporal buffer
        self.csi_buffer.append(self.smoothed_amplitudes)
        if len(self.csi_buffer) > self.sequence_length:
            self.csi_buffer.pop(0)

        # --- PROCESS SOTA PHASE UNWRAPPING ---
        if subcarrier_phases is not None:
            sanitized_p = self.sanitize_phase(subcarrier_phases)
            if self.smoothed_phases is None:
                self.smoothed_phases = sanitized_p
            else:
                self.smoothed_phases = self.ema_alpha * sanitized_p + (1.0 - self.ema_alpha) * self.smoothed_phases
                
            self.phase_buffer.append(self.smoothed_phases)
            if len(self.phase_buffer) > self.sequence_length:
                self.phase_buffer.pop(0)

        # Base fallback check
        if len(self.csi_buffer) < self.sequence_length:
            return 0, (0.5, 0.5), [0.0] * self.num_subcarriers

        sequence_data = np.array(self.csi_buffer, dtype=np.float32) # (seq_len, subcarriers)

        # Compute real-time subcarrier temporal dispersion (variance across the sequence)
        temporal_variance = np.var(sequence_data, axis=0) # variance per subcarrier
        total_dispersion = float(np.sum(temporal_variance))

        # --- ADAPTIVE NOISE FLOOR SELF-CALIBRATION ---
        # Collect baseline empty-room noise values when there's minimal motion
        if len(self.noise_floor_buffer) < 100:
            self.noise_floor_buffer.append(total_dispersion)
            self.adaptive_baseline = np.median(self.noise_floor_buffer)
        else:
            self.noise_floor_buffer.pop(0)
            self.noise_floor_buffer.append(total_dispersion)
            # Faster learning rate (0.95/0.05) to clear lagging motion energy instantly
            self.adaptive_baseline = 0.95 * self.adaptive_baseline + 0.05 * np.median(self.noise_floor_buffer)

        # Clean noise floor limits to prevent extreme drift
        self.adaptive_baseline = np.clip(self.adaptive_baseline, 0.1, 5.0)

        # --- HIGH-SENSITIVITY SAFE DECISION BOUNDARIES ---
        thresh_breathing = max(4.5, self.adaptive_baseline * 2.5)
        thresh_walking = max(45.0, self.adaptive_baseline * 15.0)

        # --- UPDATE VITAL SIGNS ESTIMATION (WITH MOTION SUPPRESSION GATE) ---
        if self.smoothed_phases is not None:
            self.latest_vitals = self.vitals_estimator.update(
                self.smoothed_amplitudes,
                self.smoothed_phases,
                total_dispersion,
                motion_threshold=thresh_walking
            )

        # --- PYTORCH INFERENCE ---
        if HAS_TORCH:
            try:
                tensor_input = torch.tensor(sequence_data).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    logits, coords = self.model(tensor_input)
                    probs = F.softmax(logits, dim=-1).cpu().numpy()[0]
                    
                    # Merge network logits with high-sensitivity adaptive priors
                    net_class = int(np.argmax(probs))
                    
                    # Override class if the adaptive physical variance is extremely low or high
                    if total_dispersion < thresh_breathing:
                        pred_class = 0 # NoMotion
                    elif total_dispersion > thresh_walking:
                        pred_class = 2 # MajorMotion (Walking)
                    else:
                        pred_class = net_class if net_class > 0 else 1
                    
                    # Coordinate Resolver
                    if self.is_trained:
                        pred_coords = coords.cpu().numpy()[0]
                        pred_coords = (
                            float(np.clip(pred_coords[0], 0.1, 0.9)),
                            float(np.clip(pred_coords[1], 0.1, 0.9))
                        )
                    else:
                        # Before model training is complete, output ultra-responsive physical estimation
                        pred_coords = self._estimate_physical_coords()
                        
                return pred_class, pred_coords, self.smoothed_amplitudes
            except Exception as e:
                pass

        # --- SELF-CALIBRATING HIGH-SENSITIVITY NUMPY EMULATION ---
        if total_dispersion > thresh_walking:
            pred_class = 2 # MajorMotion (Walking)
        elif total_dispersion > thresh_breathing:
            pred_class = 1 # MinorMotion (Breathing / Typing)
        else:
            pred_class = 0 # NoMotion (Empty / Static)

        pred_coords = self._estimate_physical_coords()
        return pred_class, pred_coords, self.smoothed_amplitudes

    def train_on_collected_data(self, dataset_x, dataset_y_class, dataset_y_coord):
        """
        Train the Self-Attention BiGRU on collected sequences.
        """
        if not HAS_TORCH:
            print("[AI Model] PyTorch not installed. Training is skipped.")
            return False

        print(f"[AI Model] Starting SOTA Self-Attention BiGRU training on {len(dataset_x)} sequences...")
        self.model.train()
        
        criterion_class = nn.CrossEntropyLoss()
        criterion_coord = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)

        inputs = torch.tensor(np.array(dataset_x, dtype=np.float32)).to(self.device)
        targets_class = torch.tensor(np.array(dataset_y_class, dtype=np.int64)).to(self.device)
        targets_coord = torch.tensor(np.array(dataset_y_coord, dtype=np.float32)).to(self.device)

        # 12 epochs of training
        for epoch in range(12):
            optimizer.zero_grad()
            logits, coords = self.model(inputs)
            
            loss_class = criterion_class(logits, targets_class)
            loss_coord = criterion_coord(coords, targets_coord)
            loss = loss_class + 5.0 * loss_coord
            
            loss.backward()
            optimizer.step()
            
            print(f"Epoch {epoch+1}/12 - SOTA Loss: {loss.item():.4f} (Class Loss: {loss_class.item():.4f}, Coord Loss: {loss_coord.item():.4f})")

        self.model.eval()
        torch.save(self.model.state_dict(), "csi_weights.pt")
        self.is_trained = True # Activate neural coordinates instantly
        print("[AI Model] SOTA model training complete. Weights saved to 'csi_weights.pt'!")
        return True

class CSIVitalSignsEstimator:
    """
    SOTA Non-contact Vital Signs (Breathing & Heart Rate) Estimator.
    Employs sliding windows, static clutter subtraction, FFT brick-wall bandpass filtering,
    dynamic subcarrier selection based on peak power ratios, and motion-gated noise suppression.
    """
    def __init__(self, num_subcarriers=64, fs=30.0, window_len=256):
        self.num_subcarriers = num_subcarriers
        self.fs = fs # 30Hz sampling rate
        self.window_len = window_len
        
        # Hist buffers for raw amplitudes & unwrapped phases
        self.amp_history = []
        self.phase_history = []
        
        # Stable tracking state with EMA
        self.current_bpm = 72.0      # Heart rate (Beats Per Minute)
        self.current_brpm = 15.0     # Breathing rate (Breaths Per Minute)
        self.bpm_ema_alpha = 0.08
        self.brpm_ema_alpha = 0.10
        
        # Vitals Signal Waveforms to be drawn on the GUI
        self.filtered_heart_wave = np.zeros(window_len, dtype=np.float32)
        self.filtered_breath_wave = np.zeros(window_len, dtype=np.float32)
        
        # Health condition & alert text
        self.status_text = "Acquiring..."

    def update(self, raw_amps, sanitized_phases, total_dispersion, motion_threshold=15.0):
        """
        Processes new amplitude and phase vector.
        Returns: estimated_bpm, estimated_brpm, filtered_heartwave, filtered_breathwave, status_text
        """
        # Append vectors
        self.amp_history.append(raw_amps)
        self.phase_history.append(sanitized_phases)
        
        if len(self.amp_history) > self.window_len:
            self.amp_history.pop(0)
            self.phase_history.pop(0)
            
        # If history window is not full yet, return defaults
        if len(self.amp_history) < self.window_len:
            self.status_text = f"Initializing Vitals... {int(len(self.amp_history)/self.window_len*100)}%"
            return self.current_bpm, self.current_brpm, self.filtered_heart_wave, self.filtered_breath_wave, self.status_text

        # --- ENVIRONMENTAL INTERFERENCE GUARD (MOTION SUPPRESSION) ---
        # When large physical motion occurs, mask micro chest motion calculation
        if total_dispersion > motion_threshold:
            self.status_text = "Suppressed (Body Motion)"
            # Glide back slowly to normal resting vitals
            self.current_bpm += (72.0 - self.current_bpm) * 0.01
            self.current_brpm += (15.0 - self.current_brpm) * 0.01
            
            # Smoothly damp down the filtered waves to zero
            self.filtered_heart_wave *= 0.90
            self.filtered_breath_wave *= 0.90
            return self.current_bpm, self.current_brpm, self.filtered_heart_wave, self.filtered_breath_wave, self.status_text

        self.status_text = "Stable Tracking"

        # Convert to numpy arrays of shape (window_len, num_subcarriers)
        amps_arr = np.array(self.amp_history, dtype=np.float32)
        phases_arr = np.array(self.phase_history, dtype=np.float32)

        # 1. STATIC ENVIRONMENTAL CLUTTER SUBTRACTION (DC Removal)
        # Subtract the temporal mean of each subcarrier to eliminate stationary reflections (furniture, walls, etc.)
        amps_detrend = amps_arr - np.mean(amps_arr, axis=0)
        phases_detrend = phases_arr - np.mean(phases_arr, axis=0)

        # 2. SPECTRAL ESTIMATION VIA FFT
        # We will run rfft (real-input fast Fourier transform) along the time axis
        F_phases = np.fft.rfft(phases_detrend, axis=0)
        freqs = np.fft.rfftfreq(self.window_len, d=1.0/self.fs)

        # 3. DEFINE VITAL SIGNS FREQUENCY BANDS
        # Breathing: 0.12Hz - 0.40Hz (7.2 to 24 BrPM)
        # Heartbeat: 0.80Hz - 2.10Hz (48 to 126 BPM)
        breath_band_mask = (freqs >= 0.12) & (freqs <= 0.40)
        heart_band_mask = (freqs >= 0.80) & (freqs <= 2.10)

        # 4. DYNAMIC SUBCARRIER SELECTION (DSS)
        # For both breathing and heart rate, select the subcarrier that has the maximum peak power 
        # in the respective band to combat multi-path fading/nulling.
        F_phases_abs = np.abs(F_phases) # (freqs_len, subcarriers)

        # Breathing Subcarrier Selection
        breath_power = np.sum(F_phases_abs[breath_band_mask, :], axis=0)
        best_breath_idx = int(np.argmax(breath_power))
        
        # Heartbeat Subcarrier Selection
        heart_power = np.sum(F_phases_abs[heart_band_mask, :], axis=0)
        best_heart_idx = int(np.argmax(heart_power))

        # Extract the signals of the best subcarriers
        breath_fft = F_phases[:, best_breath_idx].copy()
        heart_fft = F_phases[:, best_heart_idx].copy()

        # 5. FFT BRICK-WALL BANDPASS FILTERING (Zeroing out of band frequencies)
        breath_filtered_fft = np.zeros_like(breath_fft)
        breath_filtered_fft[breath_band_mask] = breath_fft[breath_band_mask]
        
        heart_filtered_fft = np.zeros_like(heart_fft)
        heart_filtered_fft[heart_band_mask] = heart_fft[heart_band_mask]

        # Convert back to time domain
        self.filtered_breath_wave = np.fft.irfft(breath_filtered_fft, n=self.window_len)
        self.filtered_heart_wave = np.fft.irfft(heart_filtered_fft, n=self.window_len)

        # Normalize waveforms to range [-1.0, 1.0] for Pygame visual scale
        norm_factor_b = np.max(np.abs(self.filtered_breath_wave))
        if norm_factor_b > 1e-5:
            self.filtered_breath_wave /= norm_factor_b
            
        norm_factor_h = np.max(np.abs(self.filtered_heart_wave))
        if norm_factor_h > 1e-5:
            self.filtered_heart_wave /= norm_factor_h

        # 6. ESTIMATE RADAR HEART RATE & BREATHING RATE (BPM / BrPM)
        # Find peak index in the breathing band
        breath_spectrum = np.abs(breath_filtered_fft)
        breath_peak_idx = np.argmax(breath_spectrum)
        est_breath_freq = freqs[breath_peak_idx]
        raw_brpm = est_breath_freq * 60.0

        # Find peak index in the heartbeat band
        heart_spectrum = np.abs(heart_filtered_fft)
        heart_peak_idx = np.argmax(heart_spectrum)
        est_heart_freq = freqs[heart_peak_idx]
        raw_bpm = est_heart_freq * 60.0

        # Apply robust Exponential Moving Average (EMA) to combat random frequency noise hops
        if 48.0 <= raw_bpm <= 126.0:
            self.current_bpm += (raw_bpm - self.current_bpm) * self.bpm_ema_alpha
        if 7.0 <= raw_brpm <= 24.0:
            self.current_brpm += (raw_brpm - self.current_brpm) * self.brpm_ema_alpha

        # Analyze medical conditions for HUD display
        if self.current_bpm < 60.0:
            self.status_text = "Resting (Bradycardia)"
        elif self.current_bpm > 100.0:
            self.status_text = "Elevated Heart Rate"
        else:
            self.status_text = "Stable Tracking"

        # Check for potential sleep apnea (loss of breathing signal over 5s)
        if np.var(amps_detrend[:, best_breath_idx]) < 0.01:
            self.status_text = "⚠️ WARNING: Apnea Alert!"

        return self.current_bpm, self.current_brpm, self.filtered_heart_wave, self.filtered_breath_wave, self.status_text
