# Raspberry Pi Installation Guide - Droid Driving Course Controller

This guide explains how to configure a Raspberry Pi (Pi 4, Pi 5, or Pi 3B+) running **Raspberry Pi OS (Bookworm)** to act as the central Wi-Fi access point, MQTT broker, and web server for the driving course.

---

## 📶 Step 1: Configure the Pi as a Wi-Fi Access Point
The track sensors expect a local Wi-Fi hotspot with:
*   **SSID:** `r2course`
*   **Password:** `r2builders`
*   **Gateway IP:** `192.168.43.1` (or matching coordinator subnet)

### The NetworkManager Way (Bookworm Default)
Raspberry Pi OS Bookworm uses **NetworkManager** by default. Setting up a persistent hotspot is very simple:

```bash
# Create and start the Wi-Fi hotspot
sudo nmcli device wifi hotspot ssid r2course password r2builders ifname wlan0

# Verify the connection profile details
sudo nmcli connection show Hotspot
```

By default, this will set the gateway IP to `10.42.0.1`. If you want to force it to match your sensor subnet (e.g. `192.168.43.1` as defined in `config.h`):

```bash
# Modify connection gateway address
sudo nmcli connection modify Hotspot ipv4.addresses 192.168.43.1/24
sudo nmcli connection modify Hotspot ipv4.method shared

# Restart the connection to apply changes
sudo nmcli connection down Hotspot
sudo nmcli connection up Hotspot
```

---

## 📡 Step 2: Install and Configure MQTT Broker
Install **Mosquitto** to receive sensor heartbeats and triggers:

```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
```

### ⚠️ Critical Configuration (Mosquitto 2.0+)
By default, Mosquitto blocks external device traffic. You **must** allow anonymous connections on port `1883` so wireless sensors can publish to it.

Edit the configuration file:
```bash
sudo nano /etc/mosquitto/conf.d/local.conf
```

Add the following lines:
```ini
listener 1883 0.0.0.0
allow_anonymous true
```

Save, exit (`Ctrl+O`, `Enter`, `Ctrl+X`), and restart the Mosquitto service:
```bash
sudo systemctl restart mosquitto
sudo systemctl enable mosquitto
```

---

## 💾 Step 3: Install the App & Virtual Environment

1.  **Clone the Repository:**
    Place the directory in `/home/pi/`:
    ```bash
    cd /home/pi
    git clone https://github.com/uk-r2-builders-club/droid_driving_course.git
    cd droid_driving_course
    ```

2.  **Initialize Environment:**
    Build the virtual environment and install dependencies:
    ```bash
    chmod +x setup_env.sh
    ./setup_env.sh
    ```

3.  **Install PlatformIO (For OTA web updates):**
    Install PlatformIO CLI inside the virtual environment:
    ```bash
    source venv/bin/activate
    pip install platformio
    ```

---

## ⚙️ Step 4: Configure systemd Background Service
To make the application start automatically at boot:

1.  **Edit the systemd service file:**
    Check or edit `r2course.service` to match your directory and use the virtual environment interpreter running `main_fast.py`:
    ```bash
    nano r2course.service
    ```

    Ensure it matches the following:
    ```ini
    [Unit]
    Description=R2Course FastAPI Controller Service
    After=network-online.target
    Wants=network-online.target

    [Service]
    User=pi
    WorkingDirectory=/home/pi/droid_driving_course
    ExecStart=/home/pi/droid_driving_course/venv/bin/python3 /home/pi/droid_driving_course/main_fast.py
    Restart=always
    RestartSec=5

    [Install]
    WantedBy=multi-user.target
    ```

2.  **Symlink and Enable the Service:**
    ```bash
    sudo cp r2course.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable r2course.service
    sudo systemctl start r2course.service
    ```

3.  **Inspect Logs:**
    To verify the background app started successfully:
    ```bash
    sudo journalctl -u r2course.service -f -n 50
    ```

---

## 🖥️ Step 5: Autostart Scoreboard in Fullscreen Kiosk Mode
If your Pi is connected to a projector or screen on-site, you can configure the desktop UI to open Chromium in kiosk mode on boot:

1.  **Create local autostart directory:**
    ```bash
    mkdir -p ~/.config/autostart
    ```

2.  **Create a desktop entry file:**
    ```bash
    nano ~/.config/autostart/scoreboard.desktop
    ```

    Add the following configuration:
    ```ini
    [Desktop Entry]
    Type=Application
    Name=Scoreboard Kiosk
    Exec=chromium-browser --noerrdialogs --disable-infobars --kiosk http://localhost:8000/scoreboard
    StartupNotify=false
    Terminal=false
    ```

3.  **Configure Desktop Login:**
    Run `sudo raspi-config` and navigate to **System Options -> Boot / Auto Login**, and set it to **Desktop Autologin** (automatic login as user `pi`).
