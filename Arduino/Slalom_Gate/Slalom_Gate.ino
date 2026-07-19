#include <Adafruit_NeoPixel.h>
#include <Adafruit_NeoMatrix.h>

#include "config.h"
#include <ESP8266WiFi.h>
#include <ESP8266WiFiMulti.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include <PubSubClient.h>

ADC_MODE(ADC_VCC);

const char firmware_version[] = "1.0.2";
const char sensor_type[] = "slalom";

const byte address_bits[] =  { 13,12,14,16 };
const int lighttime = 10000;
unsigned int address;
unsigned int localPort = 8888;
char packetBuffer[64];
char ReplyBuffer[] = "acknowledged\r\n";

#define INPUT_FAIL_PIN D3
#define LED_PIN D4
#define CELEBRATION 10

WiFiUDP Udp;
ESP8266WiFiMulti WiFiMulti;
WiFiClient client;
HTTPClient http;
PubSubClient client_mqtt(client);

Adafruit_NeoMatrix matrix = Adafruit_NeoMatrix(3, 3, LED_PIN,
  NEO_MATRIX_TOP     + NEO_MATRIX_LEFT +
  NEO_MATRIX_ROWS + NEO_MATRIX_ZIGZAG,
  NEO_GRB            + NEO_KHZ800);

void setup() {
  Serial.begin(115200);
  Serial.println("Startup");
  for (byte x = 0 ; x < 4 ; x ++ ) {
    Serial.print("Configuring Pin: ");
    Serial.println(address_bits[x]);
    pinMode(address_bits[x], INPUT);
  }

  Serial.println("Read in address");
  for (byte x = 0 ; x < 4 ; x ++ ) {
    byte value = !digitalRead(address_bits[x]);
    address = address + (value << x);
  }

  Serial.print("Address: ");
  Serial.println(address);

  pinMode(INPUT_FAIL_PIN, INPUT);

  matrix.begin();
  matrix.setBrightness(70);
  matrix.fillScreen(matrix.Color(0, 0, 0));
  matrix.show();

  char sensor_name[20];
  sprintf(sensor_name, "slalom_gate%02d", address);
  WiFi.mode(WIFI_STA);
  WiFi.hostname(sensor_name);
  WiFiMulti.addAP(ssid, pass);

  int timeout = 0;
  while (WiFiMulti.run() != WL_CONNECTED) {
     Serial.print("(");
     Serial.print(timeout);
     Serial.println(")Connecting..");
     pulseLights();
     timeout ++;
     if (timeout > 10) {
        break;
     }
  }
  
  if ((WiFiMulti.run() == WL_CONNECTED)) {
     Serial.println("Connected!");
     startupLights();
     matrix.fillScreen(matrix.Color(0, 0, 0));
     matrix.show();
  } else {
     Serial.println("TIMEOUT!");
     flashLights(10, 100);
     matrix.fillScreen(matrix.Color(0, 0, 0));
     matrix.show();
  }
  
  Udp.begin(localPort);
  client_mqtt.setServer(mqtt_server, 1883);

  ArduinoOTA.setHostname(sensor_name);
  ArduinoOTA.onStart([]() { Serial.println("Start"); });
  ArduinoOTA.onEnd([]() { Serial.println("\nEnd"); });
  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    Serial.printf("Progress: %u%%\r", (progress / (total / 100)));
  });
  ArduinoOTA.onError([](ota_error_t error) {
    Serial.printf("Error[%u]: ", error);
  });
  ArduinoOTA.begin();
}

void flashLights(int count, int wait) {
  for(int i=0; i<count; i++) {
     matrix.fillScreen(matrix.Color(255,0,0));
     matrix.show();
     delay(wait);
     matrix.fillScreen(matrix.Color(0,0,0));
     matrix.show();
     delay(wait);
  }
}

void failLights() {
  matrix.fillScreen(matrix.Color(255,0,0));
  matrix.show();
}

void offLights() {
  matrix.fillScreen(matrix.Color(0, 0, 0));
  matrix.show();
}

void startupLights() {
  uint16_t i, j;
  for(j=0; j<256; j++) {
    for(i=0; i<9; i++) {
      matrix.fillScreen(Wheel((i+j) & 255));
    }
    matrix.show();
    delay(5);
  }
}

uint32_t Wheel(byte WheelPos) {
  WheelPos = 255 - WheelPos;
  if(WheelPos < 85) {
    return matrix.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  }
  if(WheelPos < 170) {
    WheelPos -= 85;
    return matrix.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
  WheelPos -= 170;
  return matrix.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
}

void pulseLights() {
  uint16_t i, j;
  for(i=0; i<50; i++) {
    matrix.fillScreen(matrix.Color(i*5,0,0));
    matrix.show();
    delay(5);
  }
  for(j=50; j>0; j--) {
    matrix.fillScreen(matrix.Color(j*5,0,0));
    matrix.show();
    delay(5);
  }
}

unsigned long lastReconnectAttempt = 0;
unsigned long lastHeartbeat = 0;

boolean reconnect() {
  char clientId[30];
  sprintf(clientId, "ESP8266Client-%02d", address);
  if (client_mqtt.connect(clientId)) {
    Serial.println("MQTT Connected");
  }
  return client_mqtt.connected();
}

void send_heartbeat() {
  if (!client_mqtt.connected()) return;
  
  char topic[50];
  sprintf(topic, "droid_course/%d/heartbeat", address);
  
  float vcc = ESP.getVcc() / 1024.0;
  long rssi = WiFi.RSSI();
  
  char payload[160];
  sprintf(payload, "{\"ip\":\"%s\",\"rssi\":%ld,\"battery\":%.2f,\"version\":\"%s\",\"type\":\"%s\"}", WiFi.localIP().toString().c_str(), rssi, vcc, firmware_version, sensor_type);
  
  client_mqtt.publish(topic, payload);
  Serial.print("MQTT Heartbeat: ");
  Serial.println(payload);
}

void loop() {
  ArduinoOTA.handle();

  if (!client_mqtt.connected()) {
    unsigned long now = millis();
    if (now - lastReconnectAttempt > 5000) {
      lastReconnectAttempt = now;
      if (reconnect()) {
        lastReconnectAttempt = 0;
      }
    }
  } else {
    client_mqtt.loop();
  }

  unsigned long now = millis();
  if (now - lastHeartbeat > 10000) {
    lastHeartbeat = now;
    send_heartbeat();
  }

  int fail = digitalRead(INPUT_FAIL_PIN);
  
  int packetSize = Udp.parsePacket();
  if (packetSize) {
    int len = Udp.read(packetBuffer, 63);
    if (len > 0) {
      packetBuffer[len] = '\0';
    }
    Serial.println("UDP Broadcast received.");
    if (strcmp(packetBuffer, "rainbow") == 0) {
      for (int c = 0; c < CELEBRATION; c++) {
        startupLights();
        matrix.fillScreen(matrix.Color(0, 0, 0));
        matrix.show();
      }
    }
  }

  if (fail == LOW) {
     Serial.println("Fail hit");
     failLights();
     
     bool sent_mqtt = false;
     if (client_mqtt.connected()) {
        char topic[50];
        sprintf(topic, "droid_course/%d/gate", address);
        sent_mqtt = client_mqtt.publish(topic, "{\"value\":\"FAIL\"}");
     }
     
     if (!sent_mqtt) {
        String api_call = String((char*)api) + "gate/" + address + "/FAIL";
        Serial.print("API Fallback Call: ");
        Serial.println(api_call);
        http.begin(client, api_call);
        int httpCode = http.GET();
        http.end();
     }
     
     delay(lighttime);
     offLights();
  }
  delay(10);
}
