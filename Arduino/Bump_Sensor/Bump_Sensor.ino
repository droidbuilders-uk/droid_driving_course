#include "DFRobotDFPlayerMini.h"

#include <SoftwareSerial.h>
SoftwareSerial softSerial(/*rx =*/10, /*tx =*/4);
#define FPSerial softSerial

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

const char firmware_version[] = "2.0.0";
const char sensor_type[] = "bump";

DFRobotDFPlayerMini myDFPlayer;
void printDetail(uint8_t type, int value);


const byte address_bits[] =  { 13,12,14,16 };
const int lighttime = 10000;
unsigned int address;
unsigned int localPort = 8888;
char packetBuffer[64]; //buffer to hold incoming packet,
char  ReplyBuffer[] = "acknowledged\r\n";       // a string to send back

#define INPUT_PASS_PIN D4
#define INPUT_FAIL_PIN D3
#define LED_PIN D1
#define CELEBRATION 10

WiFiUDP Udp;
ESP8266WiFiMulti WiFiMulti;

Adafruit_NeoMatrix matrix = Adafruit_NeoMatrix(3, 3, LED_PIN,
  NEO_MATRIX_TOP     + NEO_MATRIX_LEFT +
  NEO_MATRIX_ROWS + NEO_MATRIX_ZIGZAG,
  NEO_GRB            + NEO_KHZ800);

const uint16_t colors[] = {
  matrix.Color(255, 0, 0), matrix.Color(0, 255, 0), matrix.Color(0, 0, 255) };

void setup() {
  // put your setup code here, to run once
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
    Serial.print("Bit: ");
    Serial.print(x);
    Serial.print(" Value: ");
    Serial.println(value);
    address = address + (value << x);
  }
  // Make the address 1-16 rather than 0-15

  Serial.print("Address: ");
  Serial.println(address);

  FPSerial.begin(9600);
  myDFPlayer.begin(FPSerial);
  Serial.println(F("DFPlayer Mini online."));
  myDFPlayer.volume(20);  //Set volume value. From 0 to 30
  myDFPlayer.play(1);  //Play the first mp3
  
  pinMode(INPUT_PASS_PIN, INPUT);
  pinMode(INPUT_FAIL_PIN, INPUT);

  matrix.begin();
  matrix.setBrightness(70);
  matrix.fillScreen(matrix.Color(0, 0, 0));
  matrix.show();

  char sensor_name[20];
  sprintf(sensor_name, "bump_sensor%02d", address);
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
     myDFPlayer.play(2);
     startupLights();
     matrix.fillScreen(matrix.Color(0, 0, 0));
     matrix.show();
  } else {
     Serial.println("TIMEOUT!");
     myDFPlayer.play(3);
     flashLights(10, 100);
     matrix.fillScreen(matrix.Color(0, 0, 0));
     matrix.show();
  }
  Udp.begin(localPort);
  client_mqtt.setServer(mqtt_server, 1883);

  ArduinoOTA.setHostname(sensor_name);
  ArduinoOTA.onStart([]() {
    Serial.println("Start");
  });
  ArduinoOTA.onEnd([]() {
    Serial.println("\nEnd");
  });
  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    Serial.printf("Progress: %u%%\r", (progress / (total / 100)));
  });
  ArduinoOTA.onError([](ota_error_t error) {
    Serial.printf("Error[%u]: ", error);
    if (error == OTA_AUTH_ERROR) Serial.println("Auth Failed");
    else if (error == OTA_BEGIN_ERROR) Serial.println("Begin Failed");
    else if (error == OTA_CONNECT_ERROR) Serial.println("Connect Failed");
    else if (error == OTA_RECEIVE_ERROR) Serial.println("Receive Failed");
    else if (error == OTA_END_ERROR) Serial.println("End Failed");
  });
  ArduinoOTA.begin();
}

void flashLights(int count, int wait) {
  int i;
  for(i=0; i<count; i++) {
     matrix.fillScreen(matrix.Color(255,0,0));
     matrix.show();
     delay(wait);
     matrix.fillScreen(matrix.Color(0,0,0));
     matrix.show();
     delay(wait);
  }
}

void passLights() {
  matrix.fillScreen(matrix.Color(0,255,0));
  matrix.show();
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

WiFiClient client;
HTTPClient http;
PubSubClient client_mqtt(client);

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

  int pass = digitalRead(INPUT_PASS_PIN);
  int fail = digitalRead(INPUT_FAIL_PIN);
  
  if (pass == LOW) {
     Serial.println("Pass hit");
     myDFPlayer.play(2);
     passLights();
     
     if (client_mqtt.connected()) {
        char topic[50];
        sprintf(topic, "droid_course/%d/gate", address);
        client_mqtt.publish(topic, "{\"value\":\"PASS\"}");
     }
     
     delay(lighttime);
     offLights();
  } 

  int packetSize = Udp.parsePacket();
  if (packetSize) {
    // read the packet into packetBufffer
    Udp.read(packetBuffer, 64);
    Serial.println("UDP Broadcast received. Contents:");
    Serial.println(packetBuffer);
    if (strcmp(packetBuffer, "rainbow") == 0) {
      for (int c = 0; c < CELEBRATION; c++) {
        startupLights();
        matrix.fillScreen(matrix.Color(0, 0, 0));
        matrix.show();
      }
    }
  }

  if (packetSize == 8 && strncmp(packetBuffer, "volume", 6) == 0) {
    // Check if the 7th and 8th characters are digits
    if (isdigit(packetBuffer[6]) && isdigit(packetBuffer[7])) {
      char numStr[3];
      numStr[0] = packetBuffer[6];
      numStr[1] = packetBuffer[7];
      numStr[2] = '\0';
      
      int volume = atoi(numStr);
      
      Serial.print("Received volume command: ");
      Serial.println(volume);
      myDFPlayer.volume(volume);
    }
  }

  if (fail == LOW) {
     Serial.println("Fail hit");
     myDFPlayer.play(3);
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
