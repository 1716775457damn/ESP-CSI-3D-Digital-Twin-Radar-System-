use std::sync::{Arc, RwLock};
use std::sync::mpsc::{channel, Sender};
use std::time::Duration;

use anyhow::Result;
use serde::Serialize;

use esp_idf_svc::wifi::{EspWifi, BlockingWifi, Configuration, ClientConfiguration, AuthMethod};
use esp_idf_svc::eventloop::EspSystemEventLoop;
use esp_idf_svc::nvs::EspDefaultNvsPartition;
use esp_idf_svc::http::server::{EspHttpServer, Configuration as HttpConfig, Method};
use esp_idf_svc::http::server::ws::EspHttpWsConnection;
use embedded_svc::ws::FrameType;

use esp_idf_sys::{
    wifi_csi_config_t, wifi_csi_info_t, esp_wifi_set_csi_config,
    esp_wifi_set_csi_rx_cb, esp_wifi_set_csi, esp_wifi_set_promiscuous,
    ESP_OK
};
use esp_idf_hal::peripherals::Peripherals;

// --- CONFIGURATION ---
const WIFI_NETWORKS: &[(&str, &str)] = &[
    ("ZHXJ-1H-SMT", "jlc_smt@jlc.123"),
    ("ovo", "twx20051"),
];

// --- CSI METRICS STRUCTURE ---
#[derive(Serialize, Clone, Debug)]
struct CsiMetrics {
    timestamp: u64,
    amplitude: f32,
    variance: f32,
    status_code: u8,
    status_text: String,
    packet_count: u64,
    subcarriers: Vec<f32>,
    subcarriers_phase: Vec<f32>,
}

// --- C-FFI CALLBACK WITH CONCURRENCY RATE LIMITER & BSSID FILTER ---
static LAST_SENT_TIME: std::sync::atomic::AtomicI32 = std::sync::atomic::AtomicI32::new(0);
static mut TARGET_BSSID: [u8; 6] = [0; 6];
static mut BSSID_LOCKED: bool = false;

unsafe extern "C" fn csi_rx_cb(ctx: *mut core::ffi::c_void, info: *mut wifi_csi_info_t) {
    if info.is_null() || ctx.is_null() {
        return;
    }
    
    let info_ref = &*info;
    let mac = info_ref.mac;

    // Filter packets: only accept packets originating from our connected AP BSSID.
    if BSSID_LOCKED {
        if mac != TARGET_BSSID {
            return;
        }
    }
    
    // Rate limit check (30Hz cap = 33,333 microseconds interval)
    let now = (esp_idf_sys::esp_timer_get_time() & 0x7FFFFFFF) as i32;
    let last = LAST_SENT_TIME.load(std::sync::atomic::Ordering::Relaxed);
    if now - last < 33_333 && now >= last {
        return;
    }

    let buf = info_ref.buf;
    let len = info_ref.len as isize;
    
    if buf.is_null() || len <= 0 {
        return;
    }

    // Try updating timestamp (atomic CAS to prevent concurrent overlaps)
    if LAST_SENT_TIME.compare_exchange(
        last, 
        now, 
        std::sync::atomic::Ordering::Relaxed, 
        std::sync::atomic::Ordering::Relaxed
    ).is_err() {
        return;
    }

    let mut subcarriers_amp = Vec::with_capacity(len as usize / 2);
    let mut subcarriers_phase = Vec::with_capacity(len as usize / 2);

    // Each subcarrier uses 2 bytes: Real part (I) and Imaginary part (Q)
    for i in (0..len).step_by(2) {
        if i + 1 >= len {
            break;
        }
        let r_val = *buf.offset(i) as f32;
        let i_val = *buf.offset(i + 1) as f32;
        
        // Calculate Amplitude = sqrt(I^2 + Q^2)
        let amp = (r_val * r_val + i_val * i_val).sqrt();
        // Calculate Phase = atan2(Q, I)
        let phase = i_val.atan2(r_val);
        
        subcarriers_amp.push(amp);
        subcarriers_phase.push(phase);
    }

    if !subcarriers_amp.is_empty() {
        let tx_mutex = &*(ctx as *const std::sync::Mutex<Sender<(Vec<f32>, Vec<f32>)>>);
        if let Ok(tx) = tx_mutex.lock() {
            let _ = tx.send((subcarriers_amp, subcarriers_phase));
        }
    }
}

fn main() -> Result<()> {
    // Link patches
    esp_idf_svc::sys::link_patches();
    esp_idf_svc::log::EspLogger::initialize_default();

    log::info!("Starting ESP-CSI Human Motion Monitor firmware...");

    let peripherals = Peripherals::take()?;
    let sys_loop = EspSystemEventLoop::take()?;
    let nvs = EspDefaultNvsPartition::take()?;

    // --- SHARED METRICS STATE ---
    let shared_state = Arc::new(RwLock::new(CsiMetrics {
        timestamp: 0,
        amplitude: 0.0,
        variance: 0.0,
        status_code: 0,
        status_text: "NoMotion".to_string(),
        packet_count: 0,
        subcarriers: Vec::new(),
        subcarriers_phase: Vec::new(),
    }));

    // --- WIFI STA CONNECTION (DHCP) ---
    let mut wifi = BlockingWifi::wrap(
        EspWifi::new(peripherals.modem, sys_loop.clone(), Some(nvs))?,
        sys_loop,
    )?;

    wifi.start()?;
    log::info!("Scanning for available Wi-Fi access points...");
    
    let mut prioritized_networks = WIFI_NETWORKS.to_vec();
    
    match wifi.scan() {
        Ok(aps) => {
            let mut scanned_ssids = Vec::new();
            for ap in aps {
                let ssid_str = ap.ssid.to_string();
                scanned_ssids.push(ssid_str);
            }
            
            log::info!("Scanned SSIDs in range: {:?}", scanned_ssids);
            
            // Re-order prioritized_networks: put the scanned ones first
            prioritized_networks.sort_by_key(|&(ssid, _)| {
                let found = scanned_ssids.iter().any(|s| s == ssid);
                if found {
                    0 // Lower key = higher priority (scanned APs come first)
                } else {
                    1
                }
            });
        }
        Err(e) => {
            log::warn!("Wi-Fi scan failed: {:?}. Proceeding with default priority list.", e);
        }
    }

    let mut connected = false;
    for (ssid, password) in prioritized_networks {
        log::info!("Attempting to connect to Wi-Fi SSID: {}...", ssid);
        
        let wifi_config = Configuration::Client(ClientConfiguration {
            ssid: ssid.try_into().unwrap(),
            password: password.try_into().unwrap(),
            auth_method: AuthMethod::WPA2Personal,
            ..Default::default()
        });
        
        if let Err(e) = wifi.set_configuration(&wifi_config) {
            log::warn!("Failed to set Wi-Fi configuration for SSID {}: {:?}", ssid, e);
            continue;
        }
        
        // Multi-attempt robust retry loop (up to 4 attempts per SSID with 2s interval)
        let mut success = false;
        for attempt in 1..=4 {
            log::info!("Connection attempt {}/4 for SSID {}...", attempt, ssid);
            
            // Try connecting
            if let Err(e) = wifi.connect() {
                log::warn!("Connection failed on attempt {}/4 for {}: {:?}", attempt, ssid, e);
                std::thread::sleep(Duration::from_secs(2));
                continue;
            }
            
            // Try obtaining IP via DHCP
            log::info!("Connected to SSID {}, waiting for IP from DHCP...", ssid);
            match wifi.wait_netif_up() {
                Ok(_) => {
                    let ip_info = wifi.wifi().sta_netif().get_ip_info()?;
                    log::info!("Wi-Fi connected successfully to {}! Assigned IP: {}", ssid, ip_info.ip);
                    
                    // Query connected AP BSSID directly from ESP-IDF driver
                    let mut ap_rec: esp_idf_sys::wifi_ap_record_t = unsafe { std::mem::zeroed() };
                    if unsafe { esp_idf_sys::esp_wifi_sta_get_ap_info(&mut ap_rec) } == 0 {
                        unsafe {
                            TARGET_BSSID = ap_rec.bssid;
                            BSSID_LOCKED = true;
                            log::info!("CSI Sniffer deterministically locked connected AP BSSID: {:02x}:{:02x}:{:02x}:{:02x}:{:02x}:{:02x}",
                                TARGET_BSSID[0], TARGET_BSSID[1], TARGET_BSSID[2], TARGET_BSSID[3], TARGET_BSSID[4], TARGET_BSSID[5]);
                        }
                    } else {
                        log::warn!("esp_wifi_sta_get_ap_info failed. AP BSSID dynamic locking is inactive.");
                    }

                    success = true;
                    break;
                }
                Err(e) => {
                    log::warn!("DHCP IP lease failed on attempt {}/4 for SSID {}: {:?}", attempt, ssid, e);
                    // Disconnect to clean up the state machine for the next attempt
                    let _ = wifi.disconnect();
                    std::thread::sleep(Duration::from_secs(2));
                }
            }
        }
        
        if success {
            connected = true;
            break;
        }
    }

    if !connected {
        return Err(anyhow::anyhow!("Failed to connect to any configured Wi-Fi networks."));
    }

    // --- CHANNEL-BASED SIGNAL PIPELINE ---
    let (tx, rx) = channel::<(Vec<f32>, Vec<f32>)>();
    let tx_mutex = std::sync::Mutex::new(tx);
    let tx_boxed = Box::new(tx_mutex);
    let tx_ptr = Box::into_raw(tx_boxed) as *mut core::ffi::c_void;

    // --- BACKGROUND ANALYSIS THREAD ---
    let shared_analysis = shared_state.clone();
    std::thread::spawn(move || {
        log::info!("Background CSI Analysis pipeline thread started.");
        
        let mut window = Vec::new();
        let window_size = 50; // Rolling window of 50 samples (~2.5s at 20Hz)
        let alpha = 0.1;      // EMA filter coefficient
        let mut ema_val: Option<f32> = None;

        while let Ok((subcarriers_amp, subcarriers_phase)) = rx.recv() {
            let count = subcarriers_amp.len();
            if count == 0 {
                continue;
            }
            let sum: f32 = subcarriers_amp.iter().sum();
            let amp = sum / count as f32;

            // 1. Exponential Moving Average smoothing
            let smoothed = match ema_val {
                Some(prev) => {
                    let current = alpha * amp + (1.0 - alpha) * prev;
                    ema_val = Some(current);
                    current
                }
                None => {
                    ema_val = Some(amp);
                    amp
                }
            };

            // 2. Add to rolling window
            window.push(smoothed);
            if window.len() > window_size {
                window.remove(0);
            }

            // 3. Compute running variance over sliding window
            let len = window.len();
            if len >= 10 {
                let sum: f32 = window.iter().sum();
                let mean = sum / len as f32;
                let sq_sum_diff: f32 = window.iter().map(|&x| (x - mean) * (x - mean)).sum();
                let variance = sq_sum_diff / len as f32;

                // 4. Update the state machine inside the RwLock
                let (status_code, status_text) = if variance > 12.0 {
                    (2, "MajorMotion")
                } else if variance > 2.0 {
                    (1, "MinorMotion")
                } else {
                    (0, "NoMotion")
                };

                let timestamp = unsafe { esp_idf_sys::esp_timer_get_time() } as u64;

                let mut s = shared_analysis.write().unwrap();
                s.timestamp = timestamp;
                s.amplitude = smoothed;
                s.variance = variance;
                s.status_code = status_code;
                s.status_text = status_text.to_string();
                s.packet_count += 1;
                s.subcarriers = subcarriers_amp;
                s.subcarriers_phase = subcarriers_phase;
            }
        }
    });

    // --- START CSI CAPTURE ---
    log::info!("Configuring Wi-Fi CSI Capture...");
    unsafe {
        let csi_config = wifi_csi_config_t {
            lltf_en: true,
            htltf_en: true,
            stbc_htltf2_en: true,
            ltf_merge_en: true,
            channel_filter_en: true,
            manu_scale: false,
            shift: 0,
            dump_ack_en: true,
        };

        let err = esp_wifi_set_csi_config(&csi_config);
        if err != ESP_OK {
            log::error!("esp_wifi_set_csi_config failed: {}", err);
        }

        let err = esp_wifi_set_csi_rx_cb(Some(csi_rx_cb), tx_ptr);
        if err != ESP_OK {
            log::error!("esp_wifi_set_csi_rx_cb failed: {}", err);
        }

        let err = esp_wifi_set_csi(true);
        if err != ESP_OK {
            log::error!("esp_wifi_set_csi failed: {}", err);
        }

        // Enable promiscuous mode to capture CSI packets from all devices on the channel
        let err = esp_wifi_set_promiscuous(true);
        if err != ESP_OK {
            log::error!("esp_wifi_set_promiscuous failed: {}", err);
        }
    }

    // --- HTTP & WEBSOCKETS SERVER ---
    log::info!("Starting HTTP and WebSockets Server on port 80...");
    let http_config = HttpConfig {
        stack_size: 16384, // 16KB stack size prevents float-formatting stack overflow
        ..Default::default()
    };
    let mut server = EspHttpServer::new(&http_config)?;

    // HTTP Endpoint: Serve Local Dashboard
    server.fn_handler("/", Method::Get, move |req| {
        let html_content = include_str!("index.html");
        let mut response = req.into_response(
            200, 
            Some("OK"), 
            &[("Content-Type", "text/html; charset=utf-8")]
        )?;
        response.write(html_content.as_bytes())?;
        Ok::<(), esp_idf_svc::io::EspIOError>(())
    })?;

    // WebSocket Endpoint: Stream CSI Metrics
    let shared_ws = shared_state.clone();
    server.ws_handler("/ws", None, move |ws: &mut EspHttpWsConnection| {
        if ws.is_new() {
            log::info!("New WebSocket client connected. Session ID: {}", ws.session());
            return Ok(());
        } else if ws.is_closed() {
            log::info!("WebSocket client disconnected. Session ID: {}", ws.session());
            return Ok(());
        }

        // Receive any incoming frame
        let mut buf = [0; 64];
        let (_frame_type, len) = match ws.recv(&mut []) {
            Ok(frame) => frame,
            Err(e) => return Err(e),
        };

        if len > 0 {
            ws.recv(buf.as_mut())?;
            
            // Format metrics into a JSON frame
            let reply = {
                let metrics = shared_ws.read().unwrap();
                serde_json::to_string(&*metrics).unwrap()
            };

            ws.send(FrameType::Text(false), reply.as_bytes())?;
        }

        Ok::<(), esp_idf_svc::sys::EspError>(())
    })?;

    // Keep the main thread alive and monitor for mesh network roaming
    log::info!("ESP32 CSI human motion monitor is up and running!");
    loop {
        std::thread::sleep(Duration::from_secs(3));
        
        // Dynamic Mesh Roaming Synchronizer: Periodically query the active AP's BSSID
        // and update the sniffer filter in-place if the client roams to another mesh AP.
        let mut ap_rec: esp_idf_sys::wifi_ap_record_t = unsafe { std::mem::zeroed() };
        if unsafe { esp_idf_sys::esp_wifi_sta_get_ap_info(&mut ap_rec) } == 0 {
            let current_bssid = ap_rec.bssid;
            unsafe {
                if BSSID_LOCKED && current_bssid != TARGET_BSSID {
                    log::info!("Mesh network roaming detected! AP BSSID shifted from {:02x}:{:02x}:{:02x}:{:02x}:{:02x}:{:02x} to {:02x}:{:02x}:{:02x}:{:02x}:{:02x}:{:02x}",
                        TARGET_BSSID[0], TARGET_BSSID[1], TARGET_BSSID[2], TARGET_BSSID[3], TARGET_BSSID[4], TARGET_BSSID[5],
                        current_bssid[0], current_bssid[1], current_bssid[2], current_bssid[3], current_bssid[4], current_bssid[5]);
                    TARGET_BSSID = current_bssid;
                }
            }
        }
    }
}
