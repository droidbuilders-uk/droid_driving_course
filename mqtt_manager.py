import paho.mqtt.client as mqtt
import json
import logging
import time
import threading

class MQTTManager:
    def __init__(self, broker="localhost", port=1883, topic_prefix="droid_course"):
        self.broker = broker
        self.port = port
        self.topic_prefix = topic_prefix
        self.logger = logging.getLogger(__name__)
        self.client = mqtt.Client()
        
        self.diagnostics = {} # {sensor_id: {last_seen: timestamp, ip: ip, rssi: rssi}}
        self.session = None # Will be set by main.py
        
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
    def set_session(self, session):
        self.session = session

    def start(self):
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            self.logger.info(f"MQTT connected to {self.broker}")
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {e}")

    def on_connect(self, client, userdata, flags, rc):
        self.logger.info(f"MQTT Connected with result code {rc}")
        client.subscribe(f"{self.topic_prefix}/#")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            topic = msg.topic
            
            # Diagnostic heartbeat
            if "/heartbeat" in topic:
                sensor_id = topic.split('/')[-2]
                self.diagnostics[sensor_id] = {
                    "last_seen": time.time(),
                    "ip": payload.get("ip"),
                    "rssi": payload.get("rssi"),
                    "battery": payload.get("battery"),
                    "version": payload.get("version", "---"),
                    "type": payload.get("type", "---")
                }
                
            # Gate trigger via MQTT
            elif "/gate" in topic:
                sensor_id = topic.split('/')[-2]
                value = payload.get("value")
                if self.session:
                    self.session.handle_gate_trigger(sensor_id, value)
                    
            # Run command via MQTT (e.g. from timer)
            elif "/run" in topic:
                cmd = payload.get("cmd")
                ms = payload.get("ms", 0)
                if self.session:
                    self.session.handle_run_command(cmd, ms)
                    
        except Exception as e:
            self.logger.error(f"Error processing MQTT message: {e}")

    def broadcast(self, subtopic, message):
        full_topic = f"{self.topic_prefix}/broadcast/{subtopic}"
        self.client.publish(full_topic, message)
        self.logger.debug(f"MQTT Broadcast: {full_topic} -> {message}")

    def get_diagnostics(self):
        return self.diagnostics

    def reset_diagnostics(self):
        self.diagnostics = {}
        self.logger.info("MQTT Diagnostics cleared")
