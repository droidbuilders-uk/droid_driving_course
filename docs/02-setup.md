# Section 2: Setup - Assembly, Boot Order & Sensor Testing

Follow this section step-by-step when setting up the driving course at the start of an event day.

---

## ⚡ Critical Boot Order

> [!CAUTION]
> **ALWAYS boot the Central Pi Brain FIRST!**
> The wireless sensors and Pi Zero display monitors rely on the Pi Brain's `r2course` Wi-Fi hotspot to operate. If you turn on sensors before the Pi Brain is ready, they will fail to connect.

```
┌─────────────────────────────────────────┐
│ STEP 1: Power ON Central Pi Brain       │ (Wait 2 mins for Wi-Fi AP)
└────────────────────┬────────────────────┘
                     │
┌────────────────────┴────────────────────┐
│ STEP 2: Power ON Pi Zero Monitors       │ (Displays load /scoreboard)
└────────────────────┬────────────────────┘
                     │
┌────────────────────┴────────────────────┐
│ STEP 3: Power ON Track Sensors          │ (Sensors join Wi-Fi)
└────────────────────┬────────────────────┘
                     │
┌────────────────────┴────────────────────┐
│ STEP 4: Run Sensor Diagnostics Test     │ (Verify on /diagnostics)
└─────────────────────────────────────────┘
```

---

## Step 1: Powering On the Central Pi Brain

1. Connect the Central Raspberry Pi Coordinator to its USB-C power supply and plug it into wall power.
2. The Pi will power up automatically. Wait **2 minutes** for its systemd background services to start.
3. Verify on your phone or laptop that the Wi-Fi network named **`r2course`** is active.

---

## Step 2: Connecting & Powering Display Monitors

The system includes Raspberry Pi Zero devices designed to drive spectator displays.

1. Connect an HDMI cable from each Pi Zero to a TV, monitor, or projector.
2. Turn on the TV/Monitor and set its input to HDMI.
3. Plug power (Micro-USB or USB-C depending on model) into the Pi Zero.
4. The Pi Zero will boot directly into Chromium Kiosk mode and display the **Tactical Scoreboard HUD**:

![Scoreboard HUD](images/scoreboard_hud.png)

*Note: If the monitor displays "Connection Refused" or a blank page, wait 30 seconds and refresh, as the Pi Zero may have booted faster than the web server.*

---

## Step 3: Powering Track Sensors & Timer Display

Power is supplied via USB power banks for sensors and a dedicated 5V 5A power supply for the timing hardware:

1. **Bump & Slalom Sensors**:
   * Connect a charged USB power bank to the micro-USB / USB-C power input port on each sensor module.
   * Check the power bank's indicator LEDs to ensure it is outputting power.
2. **Timer Display Board & Timer Gates**:
   * Plug the 5V 5A power supply into a wall power outlet.
   * Connect the 5V 5A power jack to the main Timer Board. This powers both the 5-digit LED matrix display and the connected optical Timer Gates.
3. **Observe Wi-Fi Connection Patterns**:
   * **Connecting**: While searching for the `r2course` Wi-Fi network, sensor lights pulse red.
   * **Connected (Rainbow Sequence)**: As soon as a device connects to Wi-Fi successfully, **all sensors (Bump, Slalom) and the big 5-digit Timer Clock flash a vibrant rainbow light pattern**!
   * **Timer Matrix Wi-Fi Status**: The LED matrix under the main timer board displays visual Wi-Fi connection status.

---

## Step 4: Testing & Verifying Telemetry

Before opening the track to droids, perform a full sensor check using the **Diagnostics Panel**:

1. Connect a phone, tablet, or laptop to the `r2course` Wi-Fi hotspot.
2. Open a browser and navigate to **`http://192.168.43.1:8000/diagnostics`**:

![Diagnostics Dashboard](images/diagnostics_dashboard.png)

3. **Verify Sensor Health**:
   * Ensure all physical sensors on the track appear with a green **ONLINE** status tag.
   * Check battery voltage / VCC telemetry reported on the panel. If a sensor shows degraded voltage, replace or recharge its USB power bank.
4. **Trigger Testing**:
   * **Bump Sensors**: Press each micro-switch bumper by hand. Verify that the server plays an audio fail alert and records a hit entry in the **Live Event Logger** on the Diagnostics screen.
   * **Timer Gates**: Walk through the optical beam of the Start and Finish gates. Confirm the trigger event appears in the log and digits update on the physical 5-digit LED timer display.
