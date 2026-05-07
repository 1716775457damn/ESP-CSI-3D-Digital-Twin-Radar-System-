import os

smoothie_path = r'f:\rust-esp32-wifi\smoothie.min.js'
html_path = r'f:\rust-esp32-wifi\src\index.html'

if os.path.exists(smoothie_path):
    smoothie_js = open(smoothie_path, 'r', encoding='utf-8').read()
else:
    smoothie_js = '// smoothie minified placeholder'

html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP-CSI Human Motion Monitor</title>
    <style>
        :root {
            --bg-color: #070a13;
            --card-bg: #0d1222;
            --text-color: #f1f5f9;
            --text-secondary: #94a3b8;
            --accent-green: #10b981;
            --accent-orange: #f59e0b;
            --accent-red: #ef4444;
            --accent-blue: #3b82f6;
            --glow-green: rgba(16, 185, 129, 0.25);
            --glow-orange: rgba(245, 158, 11, 0.25);
            --glow-red: rgba(239, 68, 68, 0.3);
            --glow-blue: rgba(59, 130, 246, 0.15);
            --border-color: #1e293b;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        header {
            background-color: var(--card-bg);
            border-bottom: 1px solid var(--border-color);
            padding: 1.2rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        }

        .logo-container {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .logo-icon {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, var(--accent-blue), #8b5cf6);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: white;
            font-size: 1.1rem;
            box-shadow: 0 0 15px rgba(59, 130, 246, 0.5);
        }

        header h1 {
            font-size: 1.4rem;
            font-weight: 700;
            letter-spacing: -0.025em;
            background: linear-gradient(to right, #ffffff, var(--text-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .conn-status {
            display: flex;
            align-items: center;
            gap: 8px;
            background-color: rgba(15, 23, 42, 0.6);
            padding: 6px 12px;
            border-radius: 20px;
            border: 1px solid var(--border-color);
            font-size: 0.85rem;
            font-weight: 600;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background-color: var(--accent-red);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--accent-red);
        }

        .status-dot.connected {
            background-color: var(--accent-green);
            box-shadow: 0 0 8px var(--accent-green);
        }

        main {
            flex: 1;
            padding: 2rem;
            max-width: 1400px;
            margin: 0 auto;
            width: 100%;
            display: grid;
            grid-template-columns: 350px 1fr;
            gap: 1.5rem;
        }

        @media (max-width: 1024px) {
            main {
                grid-template-columns: 1fr;
            }
        }

        .panel {
            background-color: var(--card-bg);
            border-radius: 16px;
            border: 1px solid var(--border-color);
            padding: 1.5rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .panel-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* State Indicator */
        .state-card {
            background: rgba(15, 23, 42, 0.4);
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 1.5rem;
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 160px;
            position: relative;
            overflow: hidden;
            transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .state-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 0;
            opacity: 0.05;
            transition: all 0.5s ease;
        }

        .state-label {
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-secondary);
            z-index: 1;
            font-weight: 600;
        }

        .state-value {
            font-size: 2.2rem;
            font-weight: 800;
            margin-top: 0.5rem;
            z-index: 1;
            letter-spacing: -0.02em;
            text-shadow: 0 0 20px rgba(255, 255, 255, 0.1);
            transition: all 0.5s ease;
        }

        /* Motion States Styling */
        .state-nomotion {
            border-color: var(--accent-green);
            box-shadow: 0 0 25px var(--glow-green);
        }
        .state-nomotion .state-value {
            color: var(--accent-green);
            text-shadow: 0 0 20px rgba(16, 185, 129, 0.4);
        }
        .state-nomotion::before {
            background-color: var(--accent-green);
            opacity: 0.08;
        }

        .state-minormotion {
            border-color: var(--accent-orange);
            box-shadow: 0 0 25px var(--glow-orange);
        }
        .state-minormotion .state-value {
            color: var(--accent-orange);
            text-shadow: 0 0 20px rgba(245, 158, 11, 0.4);
        }
        .state-minormotion::before {
            background-color: var(--accent-orange);
            opacity: 0.08;
        }

        .state-majormotion {
            border-color: var(--accent-red);
            box-shadow: 0 0 30px var(--glow-red);
            animation: pulse-red 2s infinite;
        }
        .state-majormotion .state-value {
            color: var(--accent-red);
            text-shadow: 0 0 25px rgba(239, 68, 68, 0.5);
        }
        .state-majormotion::before {
            background-color: var(--accent-red);
            opacity: 0.12;
        }

        @keyframes pulse-red {
            0% { box-shadow: 0 0 15px var(--glow-red); }
            50% { box-shadow: 0 0 35px rgba(239, 68, 68, 0.45); }
            100% { box-shadow: 0 0 15px var(--glow-red); }
        }

        /* Metric Rows */
        .metrics-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 1rem;
        }

        .metric-tile {
            background-color: rgba(15, 23, 42, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            padding: 1rem 1.25rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .metric-title-sub {
            font-size: 0.85rem;
            color: var(--text-secondary);
            font-weight: 500;
        }

        .metric-val {
            font-size: 1.3rem;
            font-weight: 700;
            font-family: 'Courier New', Courier, monospace;
        }

        /* Tuning Controls */
        .controls-group {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .control-item {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }

        .control-header {
            display: flex;
            justify-content: space-between;
            font-size: 0.82rem;
            color: var(--text-secondary);
            font-weight: 600;
        }

        .control-input {
            width: 100%;
            accent-color: var(--accent-blue);
            height: 6px;
            border-radius: 3px;
            background: rgba(255, 255, 255, 0.1);
            outline: none;
            -webkit-appearance: none;
        }

        .control-input::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: var(--text-color);
            cursor: pointer;
            box-shadow: 0 0 8px rgba(0,0,0,0.5);
            transition: transform 0.1s ease;
        }

        .control-input::-webkit-slider-thumb:hover {
            transform: scale(1.2);
            background: var(--accent-blue);
        }

        /* Right Dashboard Panel */
        .dashboard-main {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .chart-card {
            background-color: var(--card-bg);
            border-radius: 16px;
            border: 1px solid var(--border-color);
            padding: 1.5rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .chart-legend {
            display: flex;
            gap: 15px;
            font-size: 0.8rem;
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 5px;
            color: var(--text-secondary);
        }

        .legend-color {
            width: 12px;
            height: 4px;
            border-radius: 2px;
        }

        .canvas-container {
            position: relative;
            width: 100%;
            height: 220px;
            background-color: #080c16;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            overflow: hidden;
        }

        .physics-container {
            position: relative;
            width: 100%;
            height: 280px;
            background-color: #050810;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            overflow: hidden;
            box-shadow: inset 0 0 30px rgba(0, 0, 0, 0.8);
        }

        canvas {
            display: block;
            width: 100%;
            height: 100%;
        }

        footer {
            text-align: center;
            padding: 1.5rem;
            font-size: 0.8rem;
            color: var(--text-secondary);
            border-top: 1px solid var(--border-color);
            background-color: var(--card-bg);
            margin-top: auto;
        }
    </style>
</head>
<body>

    <header>
        <div class="logo-container">
            <div class="logo-icon">📶</div>
            <h1>ESP-CSI Human Motion Monitor</h1>
        </div>
        <div class="conn-status">
            <div id="status-dot" class="status-dot"></div>
            <span id="status-text">Disconnected</span>
        </div>
    </header>

    <main>
        <!-- Sidebar Controls & Overview -->
        <div class="panel">
            <div class="panel-title">
                <span>📊 Monitor Overview</span>
            </div>

            <!-- Glowing State Card -->
            <div id="state-card" class="state-card state-nomotion">
                <span class="state-label">Current State</span>
                <span id="state-val" class="state-value">NoMotion</span>
            </div>

            <!-- Numeric Info Rows -->
            <div class="metrics-grid">
                <div class="metric-tile">
                    <span class="metric-title-sub">Avg Amplitude</span>
                    <span id="val-amplitude" class="metric-val">0.00</span>
                </div>
                <div class="metric-tile">
                    <span class="metric-title-sub">Signal Variance</span>
                    <span id="val-variance" class="metric-val">0.00</span>
                </div>
                <div class="metric-tile">
                    <span class="metric-title-sub">Packet Rate</span>
                    <span id="val-pkts" class="metric-val">0</span>
                </div>
            </div>

            <div class="panel-title" style="margin-top: 0.5rem;">
                <span>⚙️ Sensitivity Tuning</span>
            </div>

            <!-- Sensitivity Sliders -->
            <div class="controls-group">
                <div class="control-item">
                    <div class="control-header">
                        <span>Minor Motion Threshold</span>
                        <span id="val-thresh-minor">2.0</span>
                    </div>
                    <input type="range" id="slider-minor" class="control-input" min="0.5" max="10" step="0.1" value="2.0">
                </div>
                <div class="control-item">
                    <div class="control-header">
                        <span>Major Motion Threshold</span>
                        <span id="val-thresh-major">12.0</span>
                    </div>
                    <input type="range" id="slider-major" class="control-input" min="5" max="30" step="0.5" value="12.0">
                </div>
                <div class="control-item">
                    <div class="control-header">
                        <span>EMA Filter Alpha</span>
                        <span id="val-ema">0.10</span>
                    </div>
                    <input type="range" id="slider-ema" class="control-input" min="0.01" max="0.5" step="0.01" value="0.10">
                </div>
            </div>
        </div>

        <!-- Dashboard Charts Area -->
        <div class="dashboard-main">
            <!-- 2D Physical Field Digital Twin Simulation Panel -->
            <div class="chart-card">
                <div class="chart-header">
                    <div class="panel-title" style="border: none; padding: 0;">
                        <span>🌐 WiFi Electromagnetic Field Digital Twin (2D Room Simulation)</span>
                    </div>
                </div>
                <div class="physics-container">
                    <canvas id="canvas-physics"></canvas>
                </div>
            </div>

            <!-- Amplitude Real-time Chart -->
            <div class="chart-card">
                <div class="chart-header">
                    <div class="panel-title" style="border: none; padding: 0;">
                        <span>📈 Real-time CSI Amplitude (Industrial Oscilloscope)</span>
                    </div>
                    <div class="chart-legend">
                        <div class="legend-item">
                            <div class="legend-color" style="background-color: var(--accent-blue);"></div>
                            <span>CSI Average Amplitude</span>
                        </div>
                    </div>
                </div>
                <div class="canvas-container">
                    <canvas id="canvas-amplitude"></canvas>
                </div>
            </div>

            <!-- Variance Real-time Chart -->
            <div class="chart-card">
                <div class="chart-header">
                    <div class="panel-title" style="border: none; padding: 0;">
                        <span>⚡ Human Motion Energy (Signal Variance)</span>
                    </div>
                    <div class="chart-legend">
                        <div class="legend-item">
                            <div class="legend-color" style="background-color: var(--accent-orange);"></div>
                            <span>Variance</span>
                        </div>
                    </div>
                </div>
                <div class="canvas-container">
                    <canvas id="canvas-variance"></canvas>
                </div>
            </div>
        </div>
    </main>

    <footer>
        ESP-CSI-Rust-Monitor © 2026 Powered by esp-idf-hal & Rust-lang
    </footer>

    <!-- SmoothieCharts.js Inlined -->
    <script>
        {smoothie_js}
    </script>

    <!-- Application Controller -->
    <script>
        (function() {
            // DOM Elements
            const statusDot = document.getElementById('status-dot');
            const statusText = document.getElementById('status-text');
            const stateCard = document.getElementById('state-card');
            const stateVal = document.getElementById('state-val');
            const valAmplitude = document.getElementById('val-amplitude');
            const valVariance = document.getElementById('val-variance');
            const valPkts = document.getElementById('val-pkts');

            // Parameter Sliders
            const sliderMinor = document.getElementById('slider-minor');
            const sliderMajor = document.getElementById('slider-major');
            const sliderEma = document.getElementById('slider-ema');
            const valThreshMinor = document.getElementById('val-thresh-minor');
            const valThreshMajor = document.getElementById('val-thresh-major');
            const valEma = document.getElementById('val-ema');

            // Sliders values update
            sliderMinor.addEventListener('input', () => { valThreshMinor.innerText = Number(sliderMinor.value).toFixed(1); });
            sliderMajor.addEventListener('input', () => { valThreshMajor.innerText = Number(sliderMajor.value).toFixed(1); });
            sliderEma.addEventListener('input', () => { valEma.innerText = Number(sliderEma.value).toFixed(2); });

            // Initialize SmoothieCharts for Amplitude
            const lineAmp = new TimeSeries();
            const smoothieAmp = new SmoothieChart({
                grid: { fillStyle: '#080c16', strokeStyle: 'rgba(255, 255, 255, 0.05)', lineWidth: 1, millisPerLine: 1000, verticalSections: 4, borderVisible: false },
                labels: { fillStyle: '#94a3b8', fontSize: 11, fontFamily: 'monospace', precision: 2 },
                tooltip: false,
                maxValueScale: 1.15,
                minValueScale: 1.15,
                interpolation: 'bezier'
            });
            smoothieAmp.addTimeSeries(lineAmp, { strokeStyle: '#3b82f6', fillStyle: 'rgba(59, 130, 246, 0.08)', lineWidth: 2 });
            smoothieAmp.streamTo(document.getElementById('canvas-amplitude'), 1000);

            // Initialize SmoothieCharts for Variance
            const lineVar = new TimeSeries();
            const smoothieVar = new SmoothieChart({
                grid: { fillStyle: '#080c16', strokeStyle: 'rgba(255, 255, 255, 0.05)', lineWidth: 1, millisPerLine: 1000, verticalSections: 4, borderVisible: false },
                labels: { fillStyle: '#94a3b8', fontSize: 11, fontFamily: 'monospace', precision: 2 },
                tooltip: false,
                maxValueScale: 1.15,
                minValueScale: 1.15,
                interpolation: 'bezier'
            });
            smoothieVar.addTimeSeries(lineVar, { strokeStyle: '#f59e0b', fillStyle: 'rgba(245, 158, 11, 0.08)', lineWidth: 2 });
            smoothieVar.streamTo(document.getElementById('canvas-variance'), 1000);

            // --- 2D PHYSICAL FIELD SIMULATION ---
            const canvasPhysics = document.getElementById('canvas-physics');
            const ctxPhysics = canvasPhysics.getContext('2d');
            
            let statusCode = 0; // 0: NoMotion, 1: MinorMotion, 2: MajorMotion
            let statusTextVal = "NoMotion";
            let curAmplitude = 0;
            let curVariance = 0;
            
            // Wave animation config
            const waves = [];
            let lastWaveTime = 0;
            let time = 0;
            let humanX = 0; // Target X coordinate (for easing movement)
            let humanY = 0;
            let targetHumanX = 0;

            function resizePhysicsCanvas() {
                const rect = canvasPhysics.parentElement.getBoundingClientRect();
                canvasPhysics.width = rect.width * window.devicePixelRatio;
                canvasPhysics.height = rect.height * window.devicePixelRatio;
                ctxPhysics.scale(window.devicePixelRatio, window.devicePixelRatio);
            }
            
            resizePhysicsCanvas();
            window.addEventListener('resize', resizePhysicsCanvas);
            
            // Core animation loop for digital twin physical field
            function renderPhysics() {
                const w = canvasPhysics.width / window.devicePixelRatio;
                const h = canvasPhysics.height / window.devicePixelRatio;
                
                ctxPhysics.clearRect(0, 0, w, h);
                time += 1;
                
                const tx = 60; // TX Antenna X
                const ty = h / 2; // TX Antenna Y
                const rx = w - 60; // RX Antenna X
                const ry = h / 2; // RX Antenna Y
                const centerX = (tx + rx) / 2;
                const centerY = (ty + ry) / 2;
                
                // Easing for human position (walk displacement)
                if (statusCode === 2) {
                    targetHumanX = centerX + Math.sin(time * 0.03) * (w * 0.15);
                } else {
                    targetHumanX = centerX;
                }
                humanX += (targetHumanX - humanX) * 0.05;
                humanY = centerY;
                
                // --- 1. Draw glowing background network grid ---
                ctxPhysics.strokeStyle = 'rgba(255, 255, 255, 0.01)';
                ctxPhysics.lineWidth = 1;
                const cellSize = 20;
                for (let x = 0; x < w; x += cellSize) {
                    ctxPhysics.beginPath();
                    ctxPhysics.moveTo(x, 0);
                    ctxPhysics.lineTo(x, h);
                    ctxPhysics.stroke();
                }
                for (let y = 0; y < h; y += cellSize) {
                    ctxPhysics.beginPath();
                    ctxPhysics.moveTo(0, y);
                    ctxPhysics.lineTo(w, y);
                    ctxPhysics.stroke();
                }
                
                // --- 2. Emit waves ---
                const waveInterval = statusCode === 2 ? 15 : (statusCode === 1 ? 25 : 35);
                if (time - lastWaveTime > waveInterval) {
                    waves.push({
                        r: 0,
                        maxR: Math.sqrt((rx-tx)*(rx-tx) + (ry-ty)*(ry-ty)) + 80,
                        opacity: 0.6,
                        speed: statusCode === 2 ? 3.5 : (statusCode === 1 ? 2.5 : 2.0)
                    });
                    lastWaveTime = time;
                }
                
                // --- 3. Draw and animate wave ripples ---
                for (let i = waves.length - 1; i >= 0; i--) {
                    const wave = waves[i];
                    wave.r += wave.speed;
                    
                    if (wave.r > wave.maxR) {
                        waves.splice(i, 1);
                        continue;
                    }
                    
                    // Draw wave arc
                    ctxPhysics.beginPath();
                    
                    // Customize wave stroke based on state
                    let strokeColor = 'rgba(59, 130, 246, 0.15)'; // Faint blue default
                    if (statusCode === 1) {
                        strokeColor = 'rgba(245, 158, 11, 0.22)'; // Amber for minor
                    } else if (statusCode === 2) {
                        strokeColor = 'rgba(239, 68, 68, 0.28)'; // Crimson for major
                    }
                    
                    ctxPhysics.strokeStyle = strokeColor;
                    ctxPhysics.lineWidth = statusCode === 2 ? 2.0 : 1.5;
                    
                    const startAngle = -Math.PI / 2.5;
                    const endAngle = Math.PI / 2.5;
                    const steps = 60;
                    
                    for (let s = 0; s <= steps; s++) {
                        const theta = startAngle + (endAngle - startAngle) * (s / steps);
                        
                        // Base arc calculation
                        let r_mod = wave.r;
                        let px = tx + r_mod * Math.cos(theta);
                        let py = ty + r_mod * Math.sin(theta);
                        
                        // Add physical multipath distortion/scattering based on proximity to human target
                        const distToHuman = Math.sqrt((px - humanX)*(px - humanX) + (py - humanY)*(py - humanY));
                        
                        if (distToHuman < 80) {
                            const factor = (80 - distToHuman) / 80;
                            if (statusCode === 1) {
                                // Minor breathing disturbance: high frequency noise
                                r_mod += Math.sin(theta * 20 + time * 0.2) * (3 * factor);
                            } else if (statusCode === 2) {
                                // Severe scattering: wave fracturing & massive phasing distortion
                                r_mod += Math.sin(theta * 10 + time * 0.4) * (18 * factor) + Math.cos(wave.r * 0.1) * (10 * factor);
                            }
                        }
                        
                        // Recompute px, py with modified radius
                        px = tx + r_mod * Math.cos(theta);
                        py = ty + r_mod * Math.sin(theta);
                        
                        // Don't draw past the receiver boundary
                        if (px < rx + 40) {
                            if (s === 0) {
                                ctxPhysics.moveTo(px, py);
                            } else {
                                ctxPhysics.lineTo(px, py);
                            }
                        }
                    }
                    ctxPhysics.stroke();
                }
                
                // --- 4. Draw Transmitter (Router TX) ---
                ctxPhysics.save();
                ctxPhysics.shadowBlur = 15;
                ctxPhysics.shadowColor = '#3b82f6';
                ctxPhysics.fillStyle = '#3b82f6';
                ctxPhysics.beginPath();
                ctxPhysics.arc(tx, ty, 6, 0, Math.PI * 2);
                ctxPhysics.fill();
                ctxPhysics.restore();
                
                // Router tower structure
                ctxPhysics.strokeStyle = '#3b82f6';
                ctxPhysics.lineWidth = 2;
                ctxPhysics.beginPath();
                ctxPhysics.moveTo(tx, ty);
                ctxPhysics.lineTo(tx - 15, ty + 20);
                ctxPhysics.moveTo(tx, ty);
                ctxPhysics.lineTo(tx + 15, ty + 20);
                ctxPhysics.moveTo(tx - 8, ty + 10);
                ctxPhysics.lineTo(tx + 8, ty + 10);
                ctxPhysics.stroke();
                
                ctxPhysics.fillStyle = '#94a3b8';
                ctxPhysics.font = '10px monospace';
                ctxPhysics.textAlign = 'center';
                ctxPhysics.fillText("TX (Router)", tx, ty - 15);
                
                // --- 5. Draw Receiver (ESP32 RX) ---
                ctxPhysics.save();
                ctxPhysics.shadowBlur = 15;
                ctxPhysics.shadowColor = '#8b5cf6';
                ctxPhysics.fillStyle = '#8b5cf6';
                ctxPhysics.beginPath();
                ctxPhysics.arc(rx, ry, 6, 0, Math.PI * 2);
                ctxPhysics.fill();
                ctxPhysics.restore();
                
                // ESP32 chip drawing outline
                ctxPhysics.strokeStyle = '#8b5cf6';
                ctxPhysics.lineWidth = 1.5;
                ctxPhysics.strokeRect(rx - 12, ry - 12, 24, 24);
                // Antenna grid inside ESP32
                ctxPhysics.beginPath();
                ctxPhysics.moveTo(rx - 12, ry - 6);
                ctxPhysics.lineTo(rx - 4, ry - 6);
                ctxPhysics.moveTo(rx - 12, ry + 2);
                ctxPhysics.lineTo(rx - 4, ry + 2);
                ctxPhysics.stroke();
                
                // Blink LED on receiver
                if (time % 10 < 3) {
                    ctxPhysics.fillStyle = '#10b981';
                    ctxPhysics.beginPath();
                    ctxPhysics.arc(rx + 6, ry + 6, 2.5, 0, Math.PI * 2);
                    ctxPhysics.fill();
                }
                
                ctxPhysics.fillStyle = '#94a3b8';
                ctxPhysics.font = '10px monospace';
                ctxPhysics.textAlign = 'center';
                ctxPhysics.fillText("RX (ESP32)", rx, ry - 15);
                
                // --- 6. Draw Virtual Human Avatar (Digital Twin target) ---
                if (statusCode > 0) {
                    ctxPhysics.save();
                    
                    // Holographic breathing pulse
                    const scale = statusCode === 1 ? (1.0 + Math.sin(time * 0.08) * 0.03) : (1.0 + Math.sin(time * 0.15) * 0.06);
                    const avatarColor = statusCode === 1 ? '#f59e0b' : '#ef4444';
                    ctxPhysics.shadowBlur = statusCode === 1 ? 12 : 25;
                    ctxPhysics.shadowColor = avatarColor;
                    
                    ctxPhysics.strokeStyle = avatarColor;
                    ctxPhysics.fillStyle = avatarColor + "22"; // Translucent body fill
                    ctxPhysics.lineWidth = 2;
                    
                    // Draw abstract physical field target: glowing circular field with inner matrix rings
                    ctxPhysics.beginPath();
                    ctxPhysics.arc(humanX, humanY, 20 * scale, 0, Math.PI * 2);
                    ctxPhysics.fill();
                    ctxPhysics.stroke();
                    
                    // Inner matrix/radar concentric rings
                    ctxPhysics.strokeStyle = avatarColor + "44";
                    ctxPhysics.beginPath();
                    ctxPhysics.arc(humanX, humanY, 12 * scale, 0, Math.PI * 2);
                    ctxPhysics.stroke();
                    
                    // Glowing core
                    ctxPhysics.fillStyle = avatarColor;
                    ctxPhysics.beginPath();
                    ctxPhysics.arc(humanX, humanY, 4, 0, Math.PI * 2);
                    ctxPhysics.fill();
                    
                    // Animated upward particles for walking state (statusCode == 2)
                    if (statusCode === 2 && time % 3 === 0) {
                        // We draw small particles fading upward
                        for (let k = 0; k < 3; k++) {
                            const px = humanX + (Math.random() - 0.5) * 20;
                            const py = humanY + (Math.random() - 0.5) * 20 - (time % 20);
                            ctxPhysics.fillStyle = 'rgba(239, 68, 68, 0.6)';
                            ctxPhysics.beginPath();
                            ctxPhysics.arc(px, py, 2, 0, Math.PI * 2);
                            ctxPhysics.fill();
                        }
                    }
                    
                    // Render Label
                    ctxPhysics.fillStyle = avatarColor;
                    ctxPhysics.font = 'bold 9px monospace';
                    ctxPhysics.textAlign = 'center';
                    ctxPhysics.fillText(statusCode === 1 ? "BREATHING" : "WALKING", humanX, humanY + 34);
                    
                    ctxPhysics.restore();
                } else {
                    // NoMotion: Draw faint blue digital scanning baseline
                    ctxPhysics.strokeStyle = 'rgba(16, 185, 129, 0.08)';
                    ctxPhysics.lineWidth = 1;
                    ctxPhysics.beginPath();
                    ctxPhysics.moveTo(tx, ty);
                    ctxPhysics.lineTo(rx, ry);
                    ctxPhysics.stroke();
                }
                
                requestAnimationFrame(renderPhysics);
            }
            
            // Start physics canvas loop
            requestAnimationFrame(renderPhysics);

            // --- WEBSOCKETS CONNECTION ---
            let ws;
            let csiCount = 0;
            let lastCsiCount = 0;
            let pktRate = 0;

            // Calc packet rate per second
            setInterval(() => {
                pktRate = csiCount - lastCsiCount;
                lastCsiCount = csiCount;
                valPkts.innerText = pktRate + " Pkt/s";
            }, 1000);

            function connectWebSocket() {
                const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const host = window.location.host;
                const wsUrl = `${proto}//${host}/ws`;

                statusText.innerText = "Connecting...";
                statusDot.className = "status-dot";

                ws = new WebSocket(wsUrl);

                ws.onopen = () => {
                    statusText.innerText = "Connected";
                    statusDot.className = "status-dot connected";
                    console.log("WebSocket connection established.");

                    // Request loop at 20Hz (every 50ms)
                    wsTimer = setInterval(() => {
                        if (ws.readyState === WebSocket.OPEN) {
                            ws.send("get");
                        }
                    }, 50);
                };

                let wsTimer;

                ws.onmessage = (event) => {
                    try {
                        const metrics = JSON.parse(event.data);
                        csiCount = metrics.packet_count;

                        const minorThresh = parseFloat(sliderMinor.value);
                        const majorThresh = parseFloat(sliderMajor.value);
                        
                        // Override status code on client-side based on slider values
                        let calculatedState = "NoMotion";
                        let calcStatusCode = 0;
                        
                        const variance = metrics.variance;
                        
                        if (variance > majorThresh) {
                            calculatedState = "MajorMotion";
                            calcStatusCode = 2;
                        } else if (variance > minorThresh) {
                            calculatedState = "MinorMotion";
                            calcStatusCode = 1;
                        }
                        
                        // Bind to global simulator states
                        statusCode = calcStatusCode;
                        statusTextVal = calculatedState;
                        curAmplitude = metrics.amplitude;
                        curVariance = variance;

                        // Render metrics elements
                        valAmplitude.innerText = Number(metrics.amplitude).toFixed(2);
                        valVariance.innerText = Number(variance).toFixed(2);
                        
                        stateVal.innerText = calculatedState === "NoMotion" ? "NoMotion" : (calculatedState === "MinorMotion" ? "MinorMotion" : "MajorMotion");
                        stateCard.className = `state-card state-${calculatedState.toLowerCase()}`;

                        // Push into Smoothie charts
                        const timeStamp = new Date().getTime();
                        lineAmp.append(timeStamp, metrics.amplitude);
                        lineVar.append(timeStamp, variance);

                    } catch (e) {
                        console.error("Failed to parse WebSocket JSON", e);
                    }
                };

                ws.onclose = () => {
                    statusText.innerText = "Disconnected";
                    statusDot.className = "status-dot";
                    clearInterval(wsTimer);
                    console.log("WebSocket connection closed. Reconnecting in 3 seconds...");
                    setTimeout(connectWebSocket, 3000);
                };

                ws.onerror = (err) => {
                    console.error("WebSocket error, closing socket: ", err);
                    ws.close();
                };
            }

            // Start WS
            window.onload = connectWebSocket;
        })();
    </script>
</body>
</html>
"""

open(html_path, 'w', encoding='utf-8').write(html_template.replace("{smoothie_js}", smoothie_js))
print("Successfully generated fully standalone cyber-neon index.html with inlined SmoothieCharts!")
