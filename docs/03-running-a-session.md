# Section 3: Running a Session - Driving Operations

This section explains how course operators manage droids on the track, handle walk-in contenders, record run times, and apply penalties during an event.

---

## Step 1: Contender & Droid Selection

Before a droid enters the course, assign the driver using either the **Admin Console** (`/admin`) or **Contender Registration** (`/contenders`).

![Contender Registration](images/contender_registration.png)

### Option A: Registered Builders (Pre-existing Database)
1. Open `/contenders` on an iPad, tablet, or laptop connected to `r2course` Wi-Fi.
2. Type the builder's name or droid name into the search bar.
3. Click **SELECT CONTENDER** next to their profile. This sets them as the **Active Driver** on the Scoreboard HUD.

### Option B: Walk-in / Neutral Contenders (Manual Entry)
If a walk-in builder or visitor wants to drive without a pre-registered account:
1. On `/contenders` or `/admin`, click **ADD MANUAL CONTENDER**.
2. Enter their name and Droid model/type.
3. Click **ASSIGN TO RUN**. This registers them safely for the session without cluttering the master database.

---

## Step 2: Operating the Admin Console

The **Admin Console** (`/admin`) is the primary control center for track staff.

![Admin Console](images/admin_console.png)

### 1. Starting a Run
1. Instruct the driver to position their droid behind the Start Line.
2. Click the green **START RUN** button (or let the droid trip the optical Start Gate).
3. The live timer will start ticking on the Scoreboard screens and start audio will play.

### 2. Handling Obstacle Hits & Penalties
* **Automatic Hits**: If a droid hits a **Bump Sensor**, the system automatically registers the hit, plays an audio failure sound, and adds **+20 seconds** to the final run score.
* **Manual Penalties**: If a droid touches a non-sensored boundary or an operator needs to intervene, click **+1 PENALTY** on the Admin Console.

### 3. Completing a Run
1. When the droid crosses the Finish Line, click **FINISH RUN** (or let the Finish Gate trip).
2. The system automatically calculates:
   $$\text{Final Time} = \text{Clock Time} + (\text{Penalties} \times 20\text{s})$$
3. The final result is saved to the SQLite database and updated live on the **Podium Leaderboard**.
4. If the run qualifies as a top score, fanfare sound effects will play automatically!

---

## Step 3: Special Admin Actions

* **Reset Run**: Click **RESET RUN** if a driver has a false start or wants to abort their attempt. This clears the active clock without saving a score.
* **Course Profile Switching**: Click **SWITCH COURSE PROFILE** to toggle between course layouts (e.g., `default`, `figure8`, `shock`). The system will automatically reload the gate positions and sensor maps.
* **Practice Runs**: If a droid is driving without a selected contender, the system runs in **In-Memory Practice Mode**. Timers and sounds work normally, but no data is written to disk.
