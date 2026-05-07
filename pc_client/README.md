# 🧠 ESP-CSI Deep Learning Real-World Digital Twin Render Client

This is the PC-side client for the **ESP32-S3 Channel State Information (CSI) Human Motion Monitor**. 

It connects to the ESP32-S3 over real-time high-speed WebSockets, extracts high-dimensional raw CSI subcarrier amplitudes (64 features per packet), feeds them into a **CNN-LSTM Deep Learning Neural Network** for activity classification and $(x, y)$ coordinate joint localization, and renders a **realistic 3D isometric digital twin** of a living room in real-time.

---

## 🛠️ Main Features

1. **Realistic 3D Isometric Digital Twin Room**:
   - High-fidelity isometric projection of a furnished living room (wooden floors, couch, wall-mounted TV, router nodes).
   - A **Holographic Human Avatar** with a fully-rendered skeletal joints bone overlay (Head, Collarbone, Arms, Spine, Legs).
   - **Rhythmic Chest Expansion** simulating breathing rates under `MinorMotion` state.
   - **Leg & Arm Swing Animations** with velocity displacement during `MajorMotion` walking.
   - Real-time scattering particles representing wireless multi-path reflections colliding with the human body.
2. **Industrial waterfall CSI Spectrogram**:
   - A scrolling rolling heatmap representing historical subcarrier indexes against amplitude time steps, behaving like professional radar signal visualization tools.
3. **Subcarrier Envelope Curve**:
   - Live wave graph overlay plotting the shape of the current 64 subcarriers.
4. **CNN-LSTM AI Engine (`deep_learning_model.py`)**:
   - Implements a 1D Convolutional Neural Network (Conv1D spatial extractor) + Long Short-Term Memory (LSTM sequence model) architecture in **PyTorch**.
   - Includes an intelligent NumPy/Sklearn mathematical fallback layer to guarantee 100% immediate running capabilities even if PyTorch is not configured locally.

---

## 📂 Project Structure

* `requirements.txt`: Python pip package dependencies.
* `deep_learning_model.py`: PyTorch Deep Learning sequence model structure, training loop, and inference logic.
* `realworld_renderer.py`: Main Pygame isometric rendering, event loop, and WebSocket client receiver.

---

## 🚀 Installation & Running Guide

### 1. Install Dependencies
Ensure you have Python 3.8+ installed, then open your PC shell inside the `pc_client` directory and install the packages:
```bash
pip install -r requirements.txt
```

### 2. Connect and Run
Once your ESP32-S3 is flashed and outputting its assigned IP address (e.g. `192.168.4.1`), run the client pointing to your ESP32's IP:
```bash
python realworld_renderer.py 192.168.4.1
```

### 3. Keyboard Simulation Shortcuts (Offline Debugging)
If your ESP32-S3 is offline or you are testing without physical hardware, the PC renderer includes a built-in emulator. Simply press these keys on your keyboard:
* **`0`**: Emulate **Empty Room (NoMotion)** - *Status turns green, human avatar sits invisibly, waves propagate smoothly.*
* **`1`**: Emulate **Breathing / Typing (MinorMotion)** - *Status turns orange, the green holographic human silhouette appears on the couch, chest pulses rhythmically, waves distort mildly.*
* **`2`**: Emulate **Walking (MajorMotion)** - *Status turns red, the human avatar stands up and walks around, legs swing, waves violently shatter and fracture into disjoint multipath lines, emitting red embers.*
* **`ESC`**: Exit the application.
