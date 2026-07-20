# Section 4: Overnight - Shutdown, Battery Management & Charging

At the conclusion of each event day, follow these procedures to safely power down electronics and prepare batteries for the next day.

---

## ⚡ Equipment Shutdown Sequence

To prevent SD card corruption on the Raspberry Pis, always follow the proper shutdown sequence:

```
┌─────────────────────────────────────────┐
│ STEP 1: Power OFF Track Sensors         │ (Toggle switches to OFF)
└────────────────────┬────────────────────┘
                     │
┌────────────────────┴────────────────────┐
│ STEP 2: Shutdown Raspberry Pi Zeros     │ (Unplug micro-USB power)
└────────────────────┬────────────────────┘
                     │
┌────────────────────┴────────────────────┐
│ STEP 3: Gracefully Shutdown Pi Brain   │ (Via Admin /admin interface)
└─────────────────────────────────────────┘
```

### Shutting Down the Central Pi Brain
1. On your phone/tablet/laptop, open the **Admin Console** (`/admin`).
2. Scroll to the system options and click **SHUTDOWN SERVER**.
3. Alternatively, if logged into terminal, execute:
   ```bash
   sudo shutdown -h now
   ```
4. Wait for the green activity LED on the Raspberry Pi Brain to stop blinking completely before unplugging main power.

---

## 🔋 Power Bank Care & Nightly Charging

All Bump Sensors and Slalom Sensors are powered by individual external USB power banks. The main Timer Board and Timer Gates are powered by the 5V 5A wall power supply.

### 1. Power Disconnection
1. Unplug the USB power banks from each Bump Sensor and Slalom Sensor module.
2. Unplug the 5V 5A power supply adapter from the wall outlet and disconnect its power jack from the main Timer Board.

### 2. Charging USB Power Banks
1. Plug all USB power banks into multi-port USB chargers provided in the event kit.
2. Verify that the charging indicator LEDs on the power banks light up (showing active charging).
3. Leave power banks charging in a safe, well-ventilated location overnight so they are fully charged for the next event day.

---

## 📦 Equipment Storage & Pack-Up

1. Place sensor modules and power banks into dedicated padded storage totes.
2. Coil HDMI cables, micro-USB power cables, and the 5V 5A power supply neatly in the cabling bag.
