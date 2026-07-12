import logging
import json
from collections import namedtuple
import database

Droid = namedtuple('Droid', 'droid_uid, member_uid, name, material, weight, transmitter_type')
Driver = namedtuple('Driver', 'member_uid, name, email')

class CourseSession:
    def __init__(self, socketio, broadcast, audio):
        self.socketio = socketio
        self.broadcast = broadcast
        self.audio = audio
        self.logger = logging.getLogger(__name__)
        self.last_reset_time = 0
        self.reset_session()
        
    def reset_session(self):
        import time
        self.last_reset_time = time.time()
        database.clear_idle_penalties()
        self.practice_gates = {}
        self.current_droid = Droid(droid_uid=0, member_uid=0, name="none", material="none", weight="none", transmitter_type="none")
        self.current_member = Driver(member_uid=0, name="none", email="none")
        self.current_run_id = 0
        self.current_state = 0 # 0: Ready, 1: Started, 2: Middle Wait, 3: Resumed, 4: Finished
        
        self.logger.info("Session reset")
        self.update_matrix_display()

    def clear_run_state(self):
        import time
        self.last_reset_time = time.time()
        database.clear_idle_penalties()
        self.practice_gates = {}
        self.current_run_id = 0
        self.current_state = 0
        self.logger.info("Run state cleared (preserving contender selection)")

    def play_sound(self, name):
        self.audio.TriggerSound(name)
        self.socketio.emit('play_sound', {'sound': name}, namespace='/comms')

    def update_matrix_display(self):
        if self.current_member.member_uid != 0 and self.current_droid.droid_uid != 0:
            first_name = self.current_member.name.split(' ')[0]
            display_msg = f"msg:{first_name} & {self.current_droid.name}"
        else:
            display_msg = "msg:Practice Run"
        
        self.logger.info(f"Updating matrix display: {display_msg}")
        self.broadcast.broadcast_message(display_msg.encode('utf-8'))
        
    def register_droid(self, droid_id):
        self.clear_run_state()
        data = database.get_droid(droid_id)
        if isinstance(data, str):
            data = json.loads(data)
            
        self.current_droid = Droid(
            droid_uid=data.get('droid_uid', 0),
            member_uid=data.get('member_uid', 0),
            name=data.get('name', 'none'),
            material=data.get('material', 'none'),
            weight=data.get('weight', 'none'),
            transmitter_type=data.get('transmitter_type', 'none')
        )
        self.logger.info(f"Droid Registered: {droid_id} ({self.current_droid.name})")
        self.update_matrix_display()
        
        self._emit_reload(['contender', 'results', 'current', 'gates'])
        self.socketio.emit('my_response', {'data': 'Droid Registered'}, namespace='/comms')

    def register_member(self, member_id):
        self.clear_run_state()
        data = database.get_member(member_id)
        if isinstance(data, str):
            data = json.loads(data)
            
        self.current_member = Driver(
            member_uid=data.get('member_uid', 0),
            name=data.get('name', 'none'),
            email=data.get('email', 'none')
        )
        self.logger.info(f"Driver Registered: {member_id} ({self.current_member.name})")
        self.update_matrix_display()
        
        self._emit_reload(['contender', 'results', 'current', 'gates'])
        self.socketio.emit('my_response', {'data': 'Driver Registered'}, namespace='/comms')

    def handle_gate_trigger(self, gate_id, value):
        import time
        if time.time() - self.last_reset_time < 1.0:
            self.logger.info(f"Ignoring gate {gate_id} during reset buffer")
            return
            
        if self.current_run_id == 0:
            self.logger.info(f"Practice Gate {gate_id} triggered ({value})")
            self.practice_gates[str(gate_id)] = value
            self._emit_reload(['gates'])
            return

        if value == 'FAIL':
            if self.current_run_id != 0 and self.current_state != 4:
                self.play_sound("woop_woop")
                database.log_penalty(gate_id, self.current_run_id)
                self.logger.warning(f"PENALTY at gate {gate_id} for run {self.current_run_id}")
                
                self.socketio.emit('my_response', {'data': 'PENALTY!!!'}, namespace='/comms')
                self._emit_reload(['gates', 'current'])
        else:
            self.logger.info(f"Gate {gate_id} passed ({value})")
            # Log the pass state if needed, but definitely reload the UI
            database.log_penalty(gate_id, self.current_run_id, value) # Assuming DB can handle 'PASS'
            self._emit_reload(['gates'])

    def handle_run_command(self, cmd, milliseconds):
        self.logger.info(f"Run command: {cmd} with {milliseconds}ms. State: {self.current_state}")
        
        if cmd == 'START' and self.current_member.member_uid != 0 and self.current_state == 0:
            self.current_run_id = database.run(0, cmd, self.current_member.member_uid, self.current_droid.droid_uid, 0)
            self.play_sound("air_horn")
            self.current_state = 1
            self.socketio.emit('my_response', {'data': 'Start Run'}, namespace='/comms')
            
        elif cmd == 'MIDDLE_WAIT' and self.current_state == 1:
            database.run(self.current_run_id, cmd, self.current_member.member_uid, self.current_droid.droid_uid, milliseconds)
            self.current_state = 2
            self.socketio.emit('my_response', {'data': 'Halfway Rest'}, namespace='/comms')
            
        elif cmd == 'MIDDLE_START' and self.current_state == 2:
            database.run(self.current_run_id, cmd, self.current_member.member_uid, self.current_droid.droid_uid, 0)
            self.current_state = 3
            self.socketio.emit('my_response', {'data': 'Continuing Run'}, namespace='/comms')
            
        elif cmd == 'FINISH' and self.current_state == 3:
            database.run(self.current_run_id, cmd, self.current_member.member_uid, self.current_droid.droid_uid, milliseconds)
            self.current_state = 4
            self.socketio.emit('my_response', {'data': 'Finish!'}, namespace='/comms')
            self._handle_finish()
            
        elif cmd == 'RESET':
            self.reset_session()
            self.broadcast.broadcast_message(b'reset')
            self.socketio.emit('my_response', {'data': 'Resetting'}, namespace='/comms')
            self._emit_reload(['results', 'contender', 'current', 'gates'])
            
        self._emit_reload(['current'])

    def _handle_finish(self):
        run_details = database.current_run(self.current_run_id)
        self.logger.info(f"Run Finished: {run_details}")
        
        special_msg = None
        if database.is_top(self.current_run_id) == "yes":
            self.broadcast.broadcast_message(b'rainbow')
            self.socketio.emit('special_display', {'data': 'toprun'}, namespace='/comms')
            self.socketio.emit('my_response', {'data': '**** TOP RUN ****'}, namespace='/comms')
            special_msg = "TOP RUN!"
            self.play_sound("siren")
            
        if run_details.get("final_time", 0) > 120000:
            self.socketio.emit('special_display', {'data': 'slow'}, namespace='/comms')
            self.socketio.emit('my_response', {'data': '**** SLOOOOOOOOOOW ****'}, namespace='/comms')
            special_msg = "SLOW RUN"
            
        if run_details.get("num_penalties", 0) > 6:
            self.socketio.emit('special_display', {'data': 'pinball'}, namespace='/comms')
            self.socketio.emit('my_response', {'data': '**** PINBALL DROID ****'}, namespace='/comms')
            special_msg = "PINBALL DROID"
            
        if special_msg:
            self.broadcast.broadcast_message(f"msg:{special_msg}".encode('utf-8'))
            
        self._emit_reload(['results'])

    def _emit_reload(self, targets):
        for target in targets:
            self.socketio.emit(f'reload_{target}', {'data': f'reload {target}'}, namespace='/comms')

    def get_contender_data(self):
        return {
            'member_uid': self.current_member.member_uid,
            'member': self.current_member.name,
            'droid_uid': self.current_droid.droid_uid,
            'droid': self.current_droid.name,
            'material': self.current_droid.material,
            'weight': self.current_droid.weight,
            'transmitter_type': self.current_droid.transmitter_type
        }
