import sqlite3
import csv
import json
import logging
from datetime import datetime
from contextlib import contextmanager

db_location = "db/r2_course.db"
logger = logging.getLogger(__name__)

# SQL Schema Definitions
SCHEMA = {
    "droids": """ CREATE TABLE IF NOT EXISTS droids (
        droid_uid INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        member_uid INTEGER NOT NULL,
        material TEXT,
        weight TEXT,
        transmitter_type TEXT,
        new BOOLEAN DEFAULT 0
    ); """,
    "members": """ CREATE TABLE IF NOT EXISTS members (
        member_uid INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT,
        badge_id TEXT NOT NULL,
        new BOOLEAN DEFAULT 0
    ); """,
    "gates": """ CREATE TABLE IF NOT EXISTS gates (
        id INTEGER PRIMARY KEY,
        type TEXT NOT NULL,
        name TEXT NOT NULL,
        penalty INTEGER NOT NULL
    ); """,
    "runs": """ CREATE TABLE IF NOT EXISTS runs (
        id INTEGER PRIMARY KEY,
        start DATETIME DEFAULT CURRENT_TIMESTAMP,
        middle_start DATETIME,
        droid_uid INTEGER NOT NULL,
        member_uid INTEGER NOT NULL,
        first_half_time INTEGER,
        second_half_time INTEGER,
        clock_time INTEGER,
        final_time INTEGER,
        type TEXT
    ); """,
    "penalties": """ CREATE TABLE IF NOT EXISTS penalties (
        id INTEGER PRIMARY KEY,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        run_id INTEGER NOT NULL,
        gate_id INTEGER NOT NULL,
        status TEXT DEFAULT 'FAIL'
    ); """,
    "course": """ CREATE TABLE IF NOT EXISTS course (
        config_name TEXT PRIMARY KEY,
        config_value TEXT
    ); """
}

@contextmanager
def get_db():
    conn = sqlite3.connect(db_location)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def db_init():
    with get_db() as conn:
        cursor = conn.cursor()
        for table_sql in SCHEMA.values():
            cursor.execute(table_sql)
        
        # Check for initial config
        cursor.execute("SELECT COUNT(*) FROM course")
        if cursor.fetchone()[0] == 0:
            logger.info("Loading initial config values to course table")
            try:
                with open('db/config.csv', 'rt') as fin:
                    dr = csv.DictReader(fin)
                    to_db = [(i['config_name'], i['config_value']) for i in dr]
                    cursor.executemany("INSERT INTO course (config_name, config_value) VALUES (?, ?);", to_db)
            except FileNotFoundError:
                logger.warning("db/config.csv not found during initialization")
        
        conn.commit()
    load_gates()

def get_config(setting):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT config_value FROM course WHERE config_name = ?", (setting,))
        row = cursor.fetchone()
        return row['config_value'] if row else None

def set_config(setting, value):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO course (config_name, config_value) VALUES (?, ?)", (setting, str(value)))
        conn.commit()

def load_gates():
    course_type = get_config('course_type')
    if not course_type:
        logger.error("No course_type configured")
        return

    gates_csv = f"course/{course_type}/sensors.csv"
    try:
        with open(gates_csv, 'rt') as fin:
            dr = csv.DictReader(fin)
            to_db = [(i['id'], i['type'], i['name'], i['penalty']) for i in dr]
    except FileNotFoundError:
        logger.error(f"Gate config file not found: {gates_csv}")
        return

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS gates")
        cursor.execute(SCHEMA["gates"])
        cursor.executemany("INSERT INTO gates (id, type, name, penalty) VALUES (?, ?, ?, ?);", to_db)
        conn.commit()

def clear_db(table):
    with get_db() as conn:
        cursor = conn.cursor()
        if table == "all":
            cursor.execute("DELETE FROM runs")
            cursor.execute("DELETE FROM penalties")
        elif table in SCHEMA:
            cursor.execute(f"DELETE FROM {table}")
        conn.commit()

def run(current, cmd, member_id, droid_id, milliseconds):
    with get_db() as conn:
        cursor = conn.cursor()
        if cmd == 'START':
            cursor.execute("INSERT INTO runs (droid_uid, member_uid) VALUES (?, ?)", (droid_id, member_id))
            run_id = cursor.lastrowid
            cursor.execute("DELETE FROM penalties WHERE run_id = ?", (run_id,))
            conn.commit()
            return run_id
        
        if cmd == 'MIDDLE_WAIT':
            cursor.execute("UPDATE runs SET first_half_time = ? WHERE id = ?", (milliseconds, current))
            
        if cmd == 'MIDDLE_START':
            cursor.execute("UPDATE runs SET middle_start = CURRENT_TIMESTAMP WHERE id = ?", (current,))
            
        if cmd == 'FINISH':
            cursor.execute("SELECT first_half_time FROM runs WHERE id = ?", (current,))
            row = cursor.fetchone()
            first_half = int(row['first_half_time']) if row else 0
            clock_time = int(milliseconds)
            second_half = clock_time - first_half
            
            # Calculate penalties
            cursor.execute("""
                SELECT SUM(g.penalty) as total_penalty 
                FROM penalties p 
                JOIN gates g ON p.gate_id = g.id 
                WHERE p.run_id = ?
            """, (current,))
            penalty_row = cursor.fetchone()
            penalty_seconds = penalty_row['total_penalty'] if penalty_row['total_penalty'] else 0
            
            final_time = clock_time + (penalty_seconds * 1000)
            cursor.execute("""
                UPDATE runs SET 
                second_half_time = ?, 
                clock_time = ?, 
                final_time = ? 
                WHERE id = ?
            """, (second_half, clock_time, final_time, current))
            
        conn.commit()

def current_run(run_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        result = cursor.fetchone()
        if result:
            run_dict = dict(result)
            penalties, num_penalties = list_penalties(run_id)
            run_dict['penalties'] = penalties
            run_dict['num_penalties'] = num_penalties
            return run_dict
        return {'id': 0, 'start': None, 'middle_stop': None, 'middle_start': None, 'end': None, 'droid_uid': 0, 'member_uid': 0, 'first_half_time': None, 'second_half_time': None, 'clock_time': None, 'final_time': None, 'num_penalties': 0}

def is_top(run_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM runs WHERE final_time IS NOT NULL ORDER BY final_time ASC LIMIT 1")
        result = cursor.fetchone()
        return "yes" if result and result['id'] == run_id else "no"

def log_penalty(gate_id, run_id, status='FAIL'):
    with get_db() as conn:
        cursor = conn.cursor()
        # Remove any existing record for this gate/run to prevent duplicates
        cursor.execute("DELETE FROM penalties WHERE gate_id = ? AND run_id = ?", (gate_id, run_id))
        cursor.execute("INSERT INTO penalties (gate_id, run_id, status) VALUES (?, ?, ?)", (gate_id, run_id, status))
        conn.commit()

def clear_idle_penalties():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM penalties WHERE run_id = 0")
        conn.commit()

def get_member(did):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM members WHERE member_uid = ?", (did,))
        row = cursor.fetchone()
        return dict(row) if row else None

def add_member(data):
    with get_db() as conn:
        cursor = conn.cursor()
        name = f"{data['forename']} {data['surname']}"
        cursor.execute("""
            INSERT OR REPLACE INTO members(member_uid, name, email, badge_id, new) 
            VALUES(?, ?, ?, ?, ?)
        """, (data['id'], name, data['email'], data['badge_id'], data['new']))
        conn.commit()

def get_droid(did):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM droids WHERE droid_uid = ?", (did,))
        row = cursor.fetchone()
        return dict(row) if row else None

def add_droid(data):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO droids(droid_uid, name, member_uid, material, weight, transmitter_type, new) 
            VALUES(?, ?, ?, ?, ?, ?, ?)
        """, (data['id'], data['name'], data['member_uid'], data['material'], data['weight'], data['transmitter_type'], data['new']))
        conn.commit()

def list_gates():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM gates")
        return [dict(row) for row in cursor.fetchall()]

def list_penalties(run_id):
    with get_db() as conn:
        cursor = conn.cursor()
        gates = list_gates()
        penalties = {}
        num_penalties = 0
        for gate in gates:
            cursor.execute("SELECT status, gate_id FROM penalties WHERE gate_id = ? AND run_id = ?", (gate['id'], run_id))
            row = cursor.fetchone()
            if row:
                penalties[gate['id']] = row['status']
                if row['status'] == 'FAIL':
                    num_penalties += 1
            else:
                penalties[gate['id']] = "0"
        return penalties, num_penalties

def list_results(today_only=False):
    sql = """
        SELECT r.id, r.start, r.droid_uid, r.member_uid, r.first_half_time, 
               r.second_half_time, r.clock_time, r.final_time,
               d.name as droid_name, m.name as member_name
        FROM runs r
        LEFT JOIN droids d ON r.droid_uid = d.droid_uid
        LEFT JOIN members m ON r.member_uid = m.member_uid
        WHERE r.final_time IS NOT NULL
    """
    if today_only:
        sql += " AND r.start > datetime('now', '-12 hours')"
    sql += " ORDER BY r.final_time ASC"

    results = []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        runs = cursor.fetchall()
        for run_row in runs:
            data = dict(run_row)
            # rename for compatibility
            data['member'] = data.pop('member_name') or "Unknown Builder"
            data['droid'] = data.pop('droid_name') or "Unknown Droid"
            data['penalties'], data['num_penalties'] = list_penalties(run_row['id'])
            results.append(data)
    return json.dumps(results)

def list_today():
    return list_results(today_only=True)

def list_runs():
    results = []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM runs WHERE final_time IS NOT NULL ORDER BY final_time ASC")
        runs = cursor.fetchall()
        for run_row in runs:
            data = dict(run_row)
            data['penalties'], data['num_penalties'] = list_penalties(run_row['id'])
            results.append(data)
    return json.dumps(results)

def list_members():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT member_uid, name FROM members")
        return json.dumps([dict(row) for row in cursor.fetchall()])

def list_droids():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.droid_uid, d.name as droid_name, m.name as member_name 
            FROM droids d 
            JOIN members m ON d.member_uid = m.member_uid
        """)
        return json.dumps([dict(row) for row in cursor.fetchall()])

def delete_run(run_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        cursor.execute("DELETE FROM penalties WHERE run_id = ?", (run_id,))
        conn.commit()
    return "Ok"
