# 🌐 ESP-CSI 3D Digital Twin Radar System (无源无线电波三维数字孪生雷达系统)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Rust: 1.75+](https://img.shields.io/badge/Rust-1.75%2B-orange.svg)](https://www.rust-lang.org/)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![PyTorch: SOTA](https://img.shields.io/badge/PyTorch-SOTA%20Attention--BiGRU-red.svg)](https://pytorch.org/)

本系统是一个将 **物理电磁学（CSI 信道状态信息）**、**高并发嵌入式 Rust**、**自适应 DSP 滤波器**、**自注意力循环神经网络（Attention-BiGRU）** 以及 **3D 游戏引擎等距投影** 完美融合的“无源 Wi-Fi 空间三维全息雷达系统”。

通过利用空气中已有的 Wi-Fi 信号作为“电磁照明源”，本系统无需摄像头，即可实现穿墙级人体微动（呼吸/心跳）、剧动（走动）的分类判定与三维绝对空间坐标 $[X, Y]$ 的实时动态追踪锁定。

---

## 🚀 核心架构与黑科技演进 (Architectural Features)

### 1. 蟹钳级安全：嵌入式 Rust 边缘计算网关 (`/src`)
* **原子级 CAS 30Hz 限流器**：基于 32 位 `AtomicI32` 比较并交换（Compare-and-Swap）无锁技术。在高浓度电磁环境下，零延迟截断并发超速包，**杜绝高频网络包挤爆堆内存（OOM）**。
* **高富裕度 HTTP/WS 栈区防护**：将底层的 FreeRTOS HTTP 守护线程栈深度由默认的 6KB 拓宽至 **16KB**，彻底消除了 Rust 格式化 64 维浮点数（Float-to-String）时触发的栈溢出崩溃。
* **抗拥堵 4-Attempt 自动退避重连**：对连接信道进行 4 次退避握手，一旦握手或 DHCP 超时，**自动断开重置网卡状态机**，保证在拥挤的企业级办公网也能秒级穿透握手队列。
* **Mesh 漫游动态同步网卡**：主循环以 3 秒为周期高频监控网关。当 ESP32-S3 在房间移动并静默漫游（Roaming）到不同的 Mesh AP 路由器时，**毫秒级热更新过滤锁**，实现零断流、零冻结的无感切换。

### 2. 时空注意力脑：PyTorch 自注意力双向 GRU 推理内核 (`/pc_client`)
* **空间特征一维卷积 (Conv1D)**：提取频域相邻子载波之间的空间交叉波动指纹。
* **子载波自注意力机制 (Subcarrier Attention)**：动态调节 64 个子载波的感知比重。**自动过滤被承重墙完全挡死的“僵尸载波”，将 100% 算力强力聚焦在被人体扰动的“黄金高敏感载波段”**。
* **双向门控循环单元 (BiGRU)**：双向捕捉 12 帧时序规律。完美从杂乱的电磁扰动中分辨出“胸腔吸气（微弱振荡）”与“行走位移（单向序列偏移）”。

### 3. 一键式实时全息自标定与自主训练 UI (Interactive Calibration)
* 按下键盘 **`C` 键**，瞬间在 3D 数字孪生卧室中开启磨砂玻璃般的“电磁全息自标定控制台”。
* 系统分 4 步指引您走入 **沙发区**、**电视区**、**大厅中央** 及 **清空房间**，每步只需按 **`SPACE`（空格键）** 即可高速录制 120 帧高纯度电磁指纹。
* 录制完成后，PC 端在**不影响 60 FPS 顺滑渲染的后台守护线程**中，自动唤醒 PyTorch 基于您家独特的空间和物理轮廓进行极速拟合训练，保存并实时热加载权重，将定位精度推升至**绝对厘米级**！

---

## 📂 项目文件系统 (Project Directory)

```text
├── src/
│   ├── main.rs            # 工业级高安全 Rust 固件 (CSI 中断过滤、无锁限流、漫游同步、WebSockets 广播)
│   └── index.html         # ESP32 备用本地数据观测 Web 端
├── pc_client/
│   ├── requirements.txt   # PC 端第三方依赖 (Pygame, PyTorch, numpy, websocket-client)
│   ├── deep_learning_model.py # Attention-BiGRU 神经网络定义、数据集加载、后台极速训练模块
│   ├── realworld_renderer.py  # 3D 卧室数字孪生渲染大屏、自标定控制台、WebSocket 接收器
│   └── README.md          # 渲染客户端说明手册
└── NEXT_GEN_IMPROVEMENTS.md # 下一代商业化/硬件级进阶升级蓝图
```

---

## 🔌 硬件与环境准备 (Prerequisites)

1. **开发板**：ESP32-S3 (推荐带有双 USB 口的开发板，如 ESP32-S3-DevKitC-1)。
2. **连接宿主机**：Windows 操作系统，使用 MicroUSB 连接 ESP32-S3 的 `UART` 或 `USB` 调试串口（默认映射为 `COM7` 等）。
3. **Python 环境**：Anaconda 或 Miniconda 虚拟环境（推荐命名为 `pytorch`，Python 3.8+）。

---

## 🛠️ 快速安装与部署指南 (Installation & Run)

### 🦀 固件编译与刷写 (Flasher)
确保您的计算机上已安装 Rust 交叉编译链 `espflash`。

1. 进入项目根目录：
   ```powershell
   cargo run --release
   ```
   *(如果连接超时，拔插一下 ESP32 开发板的 USB 连接线，或者按住 BOOT 键单击 RST 键使开发板进入 ROM 下载模式后再运行)*。
2. 烧录成功后，固件会自动在串口中输出获取到的 IP 地址（如 `192.168.237.13`），并稳定等待 WebSocket 客户端接入。

### 🐍 运行 PyTorch 3D 孪生大屏 (PC Client)
1. 切换到 Conda 环境并安装依赖：
   ```powershell
   conda activate pytorch
   pip install -r pc_client/requirements.txt
   ```
2. 启动数字孪生雷达大屏（将 IP 地址替换为您 ESP32 打印出的真实 IP）：
   ```powershell
   conda run -n pytorch python pc_client/realworld_renderer.py 192.168.237.13
   ```

---

## 🎮 交互控制快捷键 (Control Shortcuts)

### 🛰️ 空控标定模式（连接状态下）
* **`C`**：**呼出 / 退出** 实时空间电磁标定控制台。
* **`SPACE`（空格键）**：在对应的步骤下，**启动 / 确认** 收集当前区域的 120 帧电磁特征。
* **`ENTER`（回车键）**：训练成功后，**激活并应用新权重** 返回数字孪生雷达视窗。

### 🕹️ 离线仿真模式（未连线状态下）
* **`0`**：模拟 **无人在场 (NoMotion)** —— 画面变绿，人体小人隐形，电磁余波丝滑荡漾。
* **`1`**：模拟 **小幅微动 / 呼吸 (MinorMotion)** —— 画面变橙，全息小人坐在沙发上规律呼吸。
* **`2`**：模拟 **剧烈走动 / 位移 (MajorMotion)** —— 画面变红，小人在房间自由走动并挥舞双臂，电磁波谱剧烈颤抖。
* **`ESC`**：退出渲染大屏。

---

## 📜 许可证 (License)

本软件基于 **MIT License** 开放协议，免费用于个人研究、极客折腾和商业拓展。欢迎提交 PR 和 Issue 共同拓展电磁无线感知的无限可能！
