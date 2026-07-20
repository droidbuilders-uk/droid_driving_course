# Section 5: Technical Reference - Firmware, OTA & MQTT Protocols

This section is for developers, maintainers, and hardware technicians who need to compile firmware, manage versioning, flash sensors over-the-air (OTA), or integrate new hardware using the MQTT protocol.

---

## 📡 MQTT Architecture & Telemetry Protocols

All track sensors (Bump Sensors, Slalom Gates, Timer Gates, Shock Sensors) connect wirelessly to the central coordinator's Mosquitto MQTT broker on port `1883`.

### 1. Topic Hierarchy

```
droid_course/
├── <sensor_id>/
│   ├── heartbeat       --> Periodic VCC, RSSI & version JSON telemetry (every 10s)
│   ├── gate            --> Immediate trigger payload on hit or beam break
│   └── run             --> Control commands from physical timing hardware
└── broadcast/
    └── <subtopic>      --> Server-to-sensor system commands (e.g. rainbow, reset)
```

### 2. Heartbeat Payload (`droid_course/<sensor_id>/heartbeat`)
Every 10 seconds, each online sensor publishes a JSON status packet to its heartbeat subtopic.

* **Sample Payload**:
  ```json
  {
    "ip": "192.168.43.105",
    "rssi": -62,
    "battery": 3.85,
    "version": "2.0.3",
    "type": "bump"
  }
  ```

* **Field Definitions**:
  * `ip` *(string)*: Device IPv4 address assigned by `r2course` Wi-Fi AP.
  * `rssi` *(integer)*: Wi-Fi signal strength in dBm (e.g., `-50` = Strong, `-85` = Weak).
  * `battery` *(float)*: Calculated operating VCC voltage (measured via internal ADC).
  * `version` *(string)*: Active firmware semantic version.
  * `type` *(string)*: Sensor classification (`bump`, `slalom`, `timer`, `shock`).

### 3. Gate Trigger Payload (`droid_course/<sensor_id>/gate`)
Published immediately when a micro-switch closes or an optical IR beam breaks.

* **Sample Payload**:
  ```json
  {
    "value": "FAIL"
  }
  ```
  * `FAIL`: Boundary hit or slalom fault. Triggers a **+20 second penalty** and failure audio horn.
  * `PASS`: Checkpoint or slalom gate cleared successfully.

### 4. Failover & Redundancy
* **UDP Broadcast (Port 8888)**: Used for low-latency NeoPixel matrix lighting animations (e.g. `rainbow` celebratory lights, `reset`).
* **HTTP API Fallback**: If an MQTT connection drops, sensors automatically attempt an HTTP GET fallback to `http://192.168.43.1:8000/gate/<sensor_id>/<value>`.

---

## 🛠️ Firmware Compilation & Versioning

Firmware projects are located in the `Arduino/` directory and managed using **PlatformIO**.

### Project Directories
* `Arduino/Bump_Sensor/`: ESP8266-based D1 Mini bump sensor firmware.
* `Arduino/Timer/`: ESP32-based WeMos Uno32 timer gate & 5-digit LED matrix driver.
* `Arduino/Slalom_Gate/`: ESP8266-based slalom checkpoint gate firmware.

### Versioning Rules
Binary releases are stored in `firmware_binaries/` using the strict naming convention:
```
firmware_binaries/<sensor_type>_<version>.bin
```
*Example: `firmware_binaries/bump_2.0.3.bin` or `firmware_binaries/timer_1.5.0.bin`*

The central coordinator scans `firmware_binaries/` on startup. If a sensor reports a `version` in its MQTT heartbeat that is lower than the latest binary version for its `type`, an **UPGRADE** button appears on the `/diagnostics` dashboard.

### Compiling via Helper Script
Use the `./build_firmware.sh` script to build and automatically publish binaries:

```bash
# Syntax: ./build_firmware.sh <project_dir> <type> <version>

# Example: Build Bump Sensor v2.0.3
./build_firmware.sh Arduino/Bump_Sensor bump 2.0.3

# Example: Build Timer v1.5.0
./build_firmware.sh Arduino/Timer timer 1.5.0
```

The script runs `platformio run`, extracts `firmware.bin` from `.pio/build/`, and copies it to `firmware_binaries/`.

---

## 🚀 Over-the-Air (OTA) Updates

Sensors can be updated wirelessly over Wi-Fi without needing a USB cable plugged in.

### Method 1: Web Interface (One-Click OTA)
1. Open **`http://192.168.43.1:8000/diagnostics`**.
2. Locate the outdated sensor in the **Connected Nodes** table.
3. Click the amber **UPGRADE** button next to its entry.
4. The coordinator spawns a background thread that invokes `espota.py` to push the binary to the device IP. The status log writes update progress in real time.

### Method 2: CLI OTA (Manual Flash)
You can flash a sensor directly from a terminal on the coordinator Pi or developer laptop:

#### Using PlatformIO CLI:
```bash
# Flash Bump Sensor at IP 192.168.43.105
pio run -d Arduino/Bump_Sensor -t upload --upload-port 192.168.43.105
```

#### Using `espota.py` directly:
```bash
# ESP8266 devices (Bump, Slalom):
python ~/.platformio/packages/framework-arduinoespressif8266/tools/espota.py \
    -i 192.168.43.105 -f firmware_binaries/bump_2.0.3.bin

# ESP32 devices (Timer):
python ~/.platformio/packages/framework-arduinoespressif32/tools/espota.py \
    -i 192.168.43.106 -f firmware_binaries/timer_1.5.0.bin
```
