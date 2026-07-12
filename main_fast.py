import logging
import json
import os
import requests
from fastapi import FastAPI, Request, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import subprocess
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List

import database_v2 as db_v2
from app_models import DroidSchema, MemberSchema, RunSchema
import broadcast
import audio
from course_manager import CourseSession
from mqtt_manager import MQTTManager

# --- Setup ---

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("R2Fast")

db_v2.init_db()

app = FastAPI(title="R2 Droid Course - FastAPI Edition")

# Static files and Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/sounds", StaticFiles(directory="sounds"), name="sounds")
templates = Jinja2Templates(directory="templates_v2")

@app.get("/favicon.ico")
def favicon():
    return FileResponse("static/favicon.png")

# --- Support Modules ---
broadcaster = broadcast.BroadCaster()
audio_lib = audio.AudioLibrary("sounds", 1)
mqtt = MQTTManager()

# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def emit(self, event: str, data: dict, namespace: str = '/comms'):
        message = json.dumps({"event": event, "data": data})
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# Mock socketio for CourseSession
class SocketIOWrapper:
    def emit(self, event, data, namespace='/comms'):
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(manager.emit(event, data, namespace))
        except RuntimeError:
            pass

session_wrapper = SocketIOWrapper()
course_session = CourseSession(session_wrapper, broadcaster, audio_lib)
mqtt.set_session(course_session)
mqtt.start()

# --- Helper Functions ---
def get_site_config(db: Session):
    return {
        'api_key': db_v2.get_config(db, 'mot_api_key').config_value if db_v2.get_config(db, 'mot_api_key') else None,
        'site_base': db_v2.get_config(db, 'mot_site_base').config_value if db_v2.get_config(db, 'mot_site_base') else None
    }

# --- Special Files ---

@app.get("/sw.js")
async def get_sw():
    return FileResponse("static/sw.js", media_type="application/javascript")

# --- Page Routes ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/diagnostics", response_class=HTMLResponse)
async def read_diagnostics(request: Request):
    return templates.TemplateResponse(request=request, name="diagnostics.html")

@app.get("/scoreboard", response_class=HTMLResponse)
async def read_scoreboard(request: Request):
    return templates.TemplateResponse(request=request, name="scoreboard.html")

@app.get("/results", response_class=HTMLResponse)
async def read_results(request: Request):
    return templates.TemplateResponse(request=request, name="results.html")

@app.get("/today", response_class=HTMLResponse)
async def read_today(request: Request):
    return templates.TemplateResponse(request=request, name="today.html")

@app.get("/admin", response_class=HTMLResponse)
async def read_admin(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html")

@app.get("/contenders", response_class=HTMLResponse)
async def read_contenders(request: Request):
    return templates.TemplateResponse(request=request, name="contenders.html")

# --- API & Action Routes ---

@app.get("/display/list_gates")
def list_gates():
    import database
    return JSONResponse(content=database.list_gates())

@app.get("/display/current_gates")
def current_gates():
    import database
    if course_session.current_run_id == 0:
        all_gates = database.list_gates()
        res = {str(g['id']): "0" for g in all_gates}
        res.update(course_session.practice_gates)
        # Calculate num_penalties for practice
        num = sum(1 for v in res.values() if v == 'FAIL')
        return JSONResponse(content=[res, num])
        
    penalties, num = database.list_penalties(course_session.current_run_id)
    return JSONResponse(content=[penalties, num])

@app.get("/display/members")
def list_members():
    import database
    return JSONResponse(content=json.loads(database.list_members()))

@app.get("/display/droids")
def list_droids():
    import database
    return JSONResponse(content=json.loads(database.list_droids()))

@app.get("/display/{cmd}")
def display(cmd: str, db: Session = Depends(db_v2.get_db)):
    import database
    if cmd == 'results':
        return JSONResponse(content=json.loads(database.list_results()))
    if cmd == 'today':
        return JSONResponse(content=json.loads(database.list_today()))
    if cmd == 'contender':
        return course_session.get_contender_data()
    if cmd == 'current':
        return database.current_run(course_session.current_run_id)
    if cmd == 'mqtt_stats':
        return {
            "sensors": mqtt.get_diagnostics(),
            "broker_connected": mqtt.client.is_connected() if mqtt.client else False,
            "latest_version": "2.0.0"
        }
    return {"status": "ok"}

@app.get("/droid/{did}")
async def register_droid(did: str):
    course_session.register_droid(did)
    await manager.emit('reload_contender', {}, namespace='/comms')
    return {"status": "ok"}

@app.get("/member/{did}")
async def register_member(did: str):
    course_session.register_member(did)
    await manager.emit('reload_contender', {}, namespace='/comms')
    return {"status": "ok"}

@app.get("/gate/{gid}/{value}")
def gate_trigger(gid: int, value: str):
    course_session.handle_gate_trigger(gid, value)
    return {"status": "ok"}

@app.get("/run/{cmd}/{ms}")
def run_command(cmd: str, ms: int):
    course_session.handle_run_command(cmd, ms)
    return {"status": "ok"}

# --- Admin Actions ---

@app.get("/admin/display/{cmd}")
def special_display(cmd: str):
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(manager.emit('special_display', {'data': cmd}))
    except RuntimeError:
        pass
    return {"status": "ok"}

@app.get("/admin/reset")
async def reset_session():
    course_session.handle_run_command('RESET', 0)
    # Broadcast individual reloads for speed
    await manager.emit('reload_contender', {}, namespace='/comms')
    await manager.emit('reload_current', {}, namespace='/comms')
    await manager.emit('reload_gates', {}, namespace='/comms')
    await manager.emit('reload_results', {}, namespace='/comms')
    # Force a full page refresh for total recovery
    await manager.emit('reload_all', {}, namespace='/comms')
    return {"status": "ok"}

@app.get("/admin/refresh/all")
async def refresh_all(db: Session = Depends(db_v2.get_db)):
    import database
    database.clear_db("all")
    config = get_site_config(db)
    if not config['api_key'] or not config['site_base']:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Missing configuration"})
        
    try:
        url = f"{config['site_base']}/api/getalldroids"
        headers = {"Authorization": f"Bearer {config['api_key']}", "Accept": "application/json"}
        r = requests.get(url, headers=headers)
        data = r.json()
        
        for member in data:
            database.add_member(member)
            # Download member image
            img_url = f"{config['site_base']}/api/getmemberimage/{member['id']}?api_token={config['api_key']}"
            try:
                r_img = requests.get(img_url, timeout=5)
                with open(f"static/members/{member['id']}.jpg", 'wb') as f:
                    f.write(r_img.content)
            except:
                pass
                
            for droid in member['droids']:
                droid['new'] = 'no'
                droid['member_uid'] = member['id']
                database.add_droid(droid)
                # Download droid image
                d_img_url = f"{config['site_base']}/api/getdroidimage/{droid['id']}?api_token={config['api_key']}"
                try:
                    r_dimg = requests.get(d_img_url, timeout=5)
                    with open(f"static/droids/{droid['id']}.jpg", 'wb') as f:
                        f.write(r_dimg.content)
                except:
                    pass
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    
    await manager.emit('reload_all', {}, namespace='/comms')
    return {"status": "ok"}

@app.get("/admin/upload/runs")
async def upload_runs(db: Session = Depends(db_v2.get_db)):
    import database
    config = get_site_config(db)
    results = json.loads(database.list_results()) # All historic results
    url = f"{config['site_base']}/api/uploadrun"
    headers = {"Authorization": f"Bearer {config['api_key']}", "Accept": "application/json"}
    
    success_count = 0
    for result in results:
        # Skip guest results for portal upload (UIDs >= 9000)
        if result.get('member_uid', 0) >= 9000:
            database.delete_run(result['id'])
            continue

        try:
            r = requests.post(url, data={"json": json.dumps(result)}, headers=headers, timeout=5)
            if r.status_code == 200:
                database.delete_run(result['id'])
                success_count += 1
        except:
            pass
            
    return {"status": "ok", "uploaded": success_count}

@app.get("/admin/change_course/{course_type}")
async def change_course(course_type: str, db: Session = Depends(db_v2.get_db)):
    db_v2.set_config(db, 'course_type', course_type)
    await manager.emit('reload_all', {}, namespace='/comms')
    return {"status": "ok", "type": course_type}

@app.get("/admin/list_courses")
def list_courses():
    courses = [d for d in os.listdir('course') if os.path.isdir(os.path.join('course', d))]
    return {"courses": courses}

@app.get("/admin/current_course")
def current_course(db: Session = Depends(db_v2.get_db)):
    config = db_v2.get_config(db, 'course_type')
    return {"type": config.config_value if config else "default"}

@app.get("/admin/add_builder")
async def add_builder(name: str):
    import database
    import json
    # Find next guest ID (9000+)
    members = json.loads(database.list_members())
    guest_ids = [m['member_uid'] for m in members if m['member_uid'] >= 9000]
    next_id = max(guest_ids) + 1 if guest_ids else 9000
    
    database.add_member({
        'id': next_id,
        'forename': name,
        'surname': '',
        'email': 'local@example.com',
        'badge_id': 'LOCAL',
        'new': 1
    })
    
    course_session.register_member(str(next_id))
    await manager.emit('reload_contender', {}, namespace='/comms')
    return {"status": "ok", "id": next_id}

@app.get("/admin/add_droid")
async def add_droid(name: str, member_uid: int = None):
    import database
    import json
    # Use provided member_uid or current session one, or generic 9999
    m_uid = member_uid or course_session.member_uid or 9999
    
    # Find next guest droid ID (9000+)
    droids = json.loads(database.list_droids())
    guest_ids = [d['droid_uid'] for d in droids if d['droid_uid'] >= 9000]
    next_id = max(guest_ids) + 1 if guest_ids else 9000

    database.add_droid({
        'id': next_id,
        'name': name,
        'member_uid': m_uid,
        'material': 'Local Build',
        'weight': 'Unknown',
        'transmitter_type': 'Local Remote',
        'new': 1
    })
    
    course_session.register_droid(str(next_id))
    await manager.emit('reload_contender', {}, namespace='/comms')
    return {"status": "ok", "id": next_id}

@app.get("/admin/mqtt_reset")
async def mqtt_reset():
    mqtt_manager.reset_diagnostics()
    return {"status": "ok"}

@app.get("/admin/flush_gates")
async def flush_gates():
    import database
    database.clear_idle_penalties()
    await manager.emit('reload_gates', {}, namespace='/comms')
    return {"status": "ok"}

async def run_ota_upgrade(ip: str, sensor_type: str):
    logger.info(f"Starting OTA Upgrade for IP {ip} (Type: {sensor_type})")
    try:
        # Determine the directory based on type
        project_dir = "Arduino/Bump_Sensor"
        if sensor_type == "timer":
            project_dir = "Arduino/Timer"
            
        logger.info(f"Compiling firmware in {project_dir}...")
        # Compile using platformio
        compile_res = subprocess.run(
            ["platformio", "run", "-d", project_dir],
            capture_output=True, text=True
        )
        if compile_res.returncode != 0:
            logger.error(f"PlatformIO Compilation failed: {compile_res.stderr}")
            return
            
        logger.info(f"Uploading firmware to {ip} via OTA...")
        # Upload using platformio target
        upload_res = subprocess.run(
            ["platformio", "run", "-d", project_dir, "--target", "upload", "--upload-port", ip],
            capture_output=True, text=True
        )
        if upload_res.returncode == 0:
            logger.info(f"OTA Upgrade to {ip} succeeded!")
        else:
            logger.error(f"OTA Upload failed: {upload_res.stderr}")
    except Exception as e:
        logger.error(f"Error during OTA upgrade: {e}")

@app.get("/admin/ota_upgrade")
def ota_upgrade(ip: str, type: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_ota_upgrade, ip, type)
    return {"status": "started", "message": f"Upgrade started for {ip} in the background."}

@app.get("/admin/course_command/{cmd}")
async def run_command(cmd: str, ms: int = 0):
    # Trigger timer phases (START, MIDDLE_WAIT, MIDDLE_START, FINISH)
    val = cmd.upper()
    print(f"DEBUG: Received Simulator Command: {val} with {ms}ms")
    course_session.handle_run_command(val, ms)
    return {"status": "ok", "cmd": val, "ms": ms}

@app.get("/mqtt/simulate/{gate_id}/{value}")
async def simulate_mqtt(gate_id: int, value: int):
    # Map simulator numbers to CourseManager strings
    val_str = "FAIL" if value == 1 else "PASS"
    print(f"DEBUG: Simulating Gate {gate_id} as {val_str}")
    course_session.handle_gate_trigger(gate_id, val_str)
    return {"status": "ok", "gate": gate_id, "state": val_str}

@app.get("/admin/clear_db")
def clear_db():
    import database
    database.clear_db("all")
    return {"status": "ok"}

# --- WebSockets ---

@app.websocket("/ws/comms")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
