# Section 1: Overview - What It All Is

The **UK R2-D2 Builders Droid Driving Course Controller** is an event-ready automated timing, penalty tracking, sound effects, and scoreboard display system. 

It is designed to give event spectators a high-tech, real-time tactical display while making run timing easy for course operators.

---

## System Overview

![Dashboard Menu](images/dashboard_menu.png)

The system consists of three main hardware layers communicating wirelessly over a dedicated Wi-Fi network:

```
+-----------------------------------------------------------------------+
|                       Central "Pi Brain"                              |
|   (FastAPI Coordinator, Wi-Fi AP: r2course, MQTT Broker, Audio)        |
+-----------------------------------+-----------------------------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+-----------------------+                       +-----------------------+
|  Wireless Track       |                       |  Display Screens      |
|  Sensors              |                       |  (Raspberry Pi Zeros) |
|  - Bump Sensors       |                       |  - Scoreboard HUDs    |
|  - Timer Gates        |                       |  - Spectator TVs      |
+-----------------------+                       +-----------------------+
```

---

## Component Hardware Breakdown

### 1. Central Coordinator ("Pi Brain")
* **Hardware**: Raspberry Pi 4, 5, or 3B+.
* **Role**: Acts as the central brain. Runs the web server, Wi-Fi Access Point (`r2course`), MQTT telemetry broker, sound synthesis engine, and SQLite database.
* **Location**: Usually placed at the operator desk near audio speakers.

### 2. Display Screens (Raspberry Pi Zeros)
* **Hardware**: Raspberry Pi Zero W / Zero 2 W connected to monitors or projectors via HDMI.
* **Role**: Boots directly into Chromium kiosk mode to display the **Tactical Scoreboard HUD** (`/scoreboard`) in full screen.
* **Location**: Positioned around the course for spectators and drivers.

### 3. Wireless Bump & Slalom Sensors
* **Hardware**: ESP8266 D1 Mini microcontrollers housed in 3D-printed bumper blocks with micro-switches.
* **Power Source**: Powered by individual external USB power banks.
* **Role**: Detects droids bumping into course walls or obstacle boundaries, transmitting instant penalty triggers (+20 sec) to the Pi Brain.

### 4. Timer Display Board & Timer Gates
* **Hardware**: ESP32 / ESP8266 microcontrollers with optical IR beam break sensors and a 5-digit LED matrix.
* **Power Source**: Powered by a dedicated 5V 5A mains power supply.
* **Role**: Triggers precise start, mid-course split times, and finish line stop times as droids cross the beam, displaying live timing on the 5-digit LED display.

---

## Software Interfaces Summary

| Page Route | Interface Name | Operator Purpose |
| :--- | :--- | :--- |
| `/` | **Main Dashboard** | Hub with quick links to all system tools and documentation. |
| `/scoreboard` | **Tactical Scoreboard** | Fullscreen HUD showing live Stopwatch, Active Driver, Penalties, and Podium Leaderboard. |
| `/admin` | **Admin Console** | Used by event staff to start/finish runs, assign penalties, and switch course profiles. |
| `/diagnostics` | **Diagnostics Panel** | Live monitor for sensor battery voltages, signal strength, and hardware logs. |
| `/contenders` | **Registration** | Quick lookup to assign registered builders/droids or register walk-in contenders. |

---

> For deep technical documentation on hardware MQTT payloads, versioning, and building/flashing firmware, see **[Section 5: Technical Reference](05-technical-firmware-mqtt.md)**.
