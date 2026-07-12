#!/usr/bin/python3
""" R2 Builder Obstacle Course - Refactored """
import os
import time
import json
import logging
import serial
import requests
from flask import Flask, request, render_template, jsonify
from flask_socketio import SocketIO
from pathlib import Path

import database
import broadcast
import audio
from course_manager import CourseSession
from mqtt_manager import MQTTManager

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("course.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("R2Course")

# Initialize Database
database.db_init()

app = Flask(__name__, template_folder='templates')
app.config['key'] = database.get_config('app_key')
socketio = SocketIO(app, cors_allowed_origins="*")

# Hardware & Support Modules
try:
    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
except Exception as e:
    logger.warning(f"No serial device found on /dev/ttyUSB0: {e}")
    ser = None

broadcaster = broadcast.BroadCaster()
audio_lib = audio.AudioLibrary("sounds", 1)
mqtt = MQTTManager()

# Session Management
session = CourseSession(socketio, broadcaster, audio_lib)
mqtt.set_session(session)
mqtt.start()

# Helper Functions
def get_site_config():
    return {
        'api_key': database.get_config('mot_api_key'),
        'site_base': database.get_config('mot_site_base')
    }

# Routes
@app.route('/sounds/<path:filename>')
def serve_sound(filename):
    from flask import send_from_directory
    return send_from_directory('sounds', filename)

@app.route('/')
def index():
    """GET to generate a list of endpoints and their docstrings"""
    urls = {r.rule: app.view_functions.get(r.endpoint).__doc__
            for r in app.url_map.iter_rules()
            if not r.rule.startswith('/static')}
    return render_template('index.html', urls=urls)

@app.route('/scoreboard')
def scoreboard():
    return render_template('scoreboard.html', async_mode=socketio.async_mode)

@app.route('/results')
def results():
    return render_template('results.html', async_mode=socketio.async_mode)

@app.route('/today')
def today():
    return render_template('today.html', async_mode=socketio.async_mode)

@app.route('/contenders')
def contenders():
    return render_template('contenders.html', async_mode=socketio.async_mode)

@app.route('/diagnostics')
def diagnostics():
    return render_template('diagnostics.html', async_mode=socketio.async_mode)

@app.route('/display/<cmd>')
def display(cmd):
    if cmd == 'results':
        return database.list_results()
    if cmd == 'today':
        return database.list_today()
    if cmd == 'contender':
        return json.dumps(session.get_contender_data())
    if cmd == 'current':
        return json.dumps(database.current_run(session.current_run_id))
    if cmd == 'list_gates':
        return json.dumps(database.list_gates())
    if cmd == 'current_gates':
        return json.dumps(database.list_penalties(session.current_run_id)[0])
    if cmd == 'droids':
        return database.list_droids()
    if cmd == 'members':
        return database.list_members()
    if cmd == 'course_types':
        subdirs = os.listdir("course")
        return json.dumps(subdirs)
    if cmd == 'mqtt_stats':
        return jsonify(mqtt.get_diagnostics())
    return "Ok"

@app.route('/droid/<did>')
def droid_register(did):
    session.register_droid(did)
    return "Ok"

@app.route('/member/<did>')
def member_register(did):
    session.register_member(did)
    return "Ok"

@app.route('/gate/<gid>/<value>')
def gate_trigger(gid, value):
    session.handle_gate_trigger(gid, value)
    return "Ok"

@app.route('/run/<cmd>/<milliseconds>')
def run_cmd(cmd, milliseconds):
    session.handle_run_command(cmd, int(milliseconds))
    return "Ok"

@app.route('/admin')
def admin():
    return render_template('admin.html', async_mode=socketio.async_mode)

@app.route('/admin/display/<cmd>')
def special_display(cmd):
    socketio.emit('special_display', {'data': cmd}, namespace='/comms')
    return "Ok"

@app.route('/admin/clear_db')
def clear_db():
    database.clear_db("all")
    socketio.emit('reload_results', {'data': 'reload results'}, namespace='/comms')
    return "Ok"

@app.route('/admin/change_course/<course>')
def change_course(course):
    database.set_config("course_type", course)
    database.load_gates()
    socketio.emit('reload_results', {'data': 'reload results'}, namespace='/comms')
    socketio.emit('reload_gates', {'data': 'reload current'}, namespace='/comms')
    socketio.emit('course_change', {'data': 'course change'}, namespace='/comms')
    return "Ok"

@app.route('/admin/refresh/all')
def refresh_all():
    config = get_site_config()
    database.clear_db("members")
    database.clear_db("droids")
    
    url = f"{config['site_base']}/api/getmembers?api_token={config['api_key']}"
    try:
        r = requests.get(url)
        data = r.json()
        for member in data:
            member['new'] = 'no'
            database.add_member(member)
            
            # Download member image
            img_url = f"{config['site_base']}/api/getmemberimage/{member['id']}?api_token={config['api_key']}"
            r_img = requests.get(img_url)
            with open(f"static/members/{member['id']}.jpg", 'wb') as f:
                f.write(r_img.content)
                
            for droid in member['droids']:
                droid['new'] = 'no'
                droid['member_uid'] = member['id']
                database.add_droid(droid)
                
                # Download droid image
                d_img_url = f"{config['site_base']}/api/getdroidimage/{droid['id']}?api_token={config['api_key']}"
                r_dimg = requests.get(d_img_url)
                with open(f"static/droids/{droid['id']}.jpg", 'wb') as f:
                    f.write(r_dimg.content)
    except Exception as e:
        logger.error(f"Failed to refresh data: {e}")
        return str(e), 500
    return "Ok"

@app.route('/admin/upload/runs')
def upload_runs():
    config = get_site_config()
    results = json.loads(database.list_runs())
    url = f"{config['site_base']}/api/uploadrun"
    headers = {"Authorization": f"Bearer {config['api_key']}", "Accept": "application/json"}
    
    for result in results:
        try:
            r = requests.post(url, data={"json": json.dumps(result)}, headers=headers)
            if r.status_code == 200:
                database.delete_run(result['id'])
            else:
                logger.error(f"Failed to upload run {result['id']}: {r.status_code}")
        except Exception as e:
            logger.error(f"Error uploading run {result['id']}: {e}")
            
    return "Ok"

@app.route('/admin/writecard/<member_uid>/<droid_uid>')
def write_card(member_uid, droid_uid):
    if not ser:
        return "No serial device", 500
    member = database.get_member(member_uid)
    droid = database.get_droid(droid_uid)
    output = f"{droid['name']},{droid_uid},{member['name']},{member_uid},{member['badge_id']}"
    ser.write(output.encode())
    return "Ok"

if __name__ == '__main__':
    logger.info("Starting R2 Course Server")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
