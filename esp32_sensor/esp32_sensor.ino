// =============================================================
//  ESP32 - Sensor de Humedad de Suelo Capacitivo v2.0 + DS18B20
//  Envía lecturas cada 10s a la API FastAPI via HTTP POST
// =============================================================

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// --- Credenciales WiFi ---
// Debe ser la misma red donde está la PC que corre uvicorn
const char* ssid     = "Gato";
const char* password = "Ermelinda58";

// --- API ---
// Reemplaza con la IP local de tu PC donde corre uvicorn
const char* API_URL    = "http://192.168.101.16:8000/api/v1/lecturas";
const char* API_KEY    = "1UmaEZRqgtvfpNQx4zcYsVwn";
const char* MAC_ESP32  = "20:43:a8:66:81:5c";  // MAC real del ESP32

// --- LCD I2C ---
#define SDA_PIN 22
#define SCL_PIN 23
LiquidCrystal_I2C lcd(0x27, 16, 2);

// --- DS18B20 ---
#define PIN_DATOS_DS18B20 4
OneWire oneWire(PIN_DATOS_DS18B20);
DallasTemperature sensorTemp(&oneWire);

// --- Sensor de humedad capacitivo ---
#define PIN_HUMEDAD 34
int valorSeco   = 3400;
int valorHumedo = 1600;

// --- Temporización ---
unsigned long tiempoAnterior = 0;
const long intervalo = 10000;  // 10 segundos

float temperaturaC      = 0;
int   humedadPorcentaje = 0;

// =============================================================
void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN);

  lcd.init();
  lcd.backlight();
  lcd.clear();

  sensorTemp.begin();
  pinMode(PIN_HUMEDAD, INPUT);

  // Mostrar MAC real en Serial para que puedas copiarla
  Serial.print("MAC Address: ");
  Serial.println(WiFi.macAddress());

  // Conectar WiFi
  lcd.setCursor(0, 0);
  lcd.print("Conectando WiFi");
  lcd.setCursor(0, 1);
  lcd.print("Espere...");

  Serial.print("Conectando a ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi conectado.");
  Serial.print("IP asignada: ");
  Serial.println(WiFi.localIP());

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("WiFi Conectado!");
  lcd.setCursor(0, 1);
  lcd.print(WiFi.localIP());
  delay(3000);
  lcd.clear();
}

// =============================================================
void enviarAAPI(float temp, int hum) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[HTTP] Sin WiFi, no se envía.");
    return;
  }

  HTTPClient http;
  http.begin(API_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);

  // Construir JSON según el schema PayloadESP32 de la API:
  // { "mac_address": "...", "lecturas": [
  //     {"tipo_sensor": "temperatura_ds18b20", "valor": 24.6},
  //     {"tipo_sensor": "humedad_suelo_capacitivo", "valor": 63.2}
  // ]}
  StaticJsonDocument<256> doc;
  doc["mac_address"] = MAC_ESP32;

  JsonArray lecturas = doc.createNestedArray("lecturas");

  JsonObject lecTemp = lecturas.createNestedObject();
  lecTemp["tipo_sensor"] = "temperatura_ds18b20";
  lecTemp["valor"]       = temp;

  JsonObject lecHum = lecturas.createNestedObject();
  lecHum["tipo_sensor"] = "humedad_suelo_capacitivo";
  lecHum["valor"]       = hum;

  String body;
  serializeJson(doc, body);

  Serial.print("[HTTP] POST → ");
  Serial.println(body);

  int httpCode = http.POST(body);

  if (httpCode == 201) {
    Serial.println("[HTTP] Lecturas guardadas OK (201)");
    lcd.setCursor(0, 1);
    lcd.print("API: OK         ");
  } else {
    Serial.print("[HTTP] Error: ");
    Serial.println(httpCode);
    Serial.println(http.getString());
    lcd.setCursor(0, 1);
    lcd.print("API: ERROR      ");
  }

  http.end();
}

// =============================================================
void loop() {
  unsigned long tiempoActual = millis();

  if (tiempoActual - tiempoAnterior >= intervalo) {
    tiempoAnterior = tiempoActual;

    // 1. Leer temperatura
    sensorTemp.requestTemperatures();
    temperaturaC = sensorTemp.getTempCByIndex(0);

    // 2. Leer humedad
    int lecturaHumedad = analogRead(PIN_HUMEDAD);
    Serial.print("RAW humedad: ");
    Serial.println(lecturaHumedad);
    humedadPorcentaje  = map(lecturaHumedad, valorSeco, valorHumedo, 0, 100);
    humedadPorcentaje  = constrain(humedadPorcentaje, 0, 100);

    // 3. Mostrar en LCD
    lcd.setCursor(0, 0);
    lcd.print("T:");
    lcd.print(temperaturaC, 1);
    lcd.print("C H:");
    lcd.print(humedadPorcentaje);
    lcd.print("%  ");

    // 4. Debug Serial
    Serial.print("Temp: ");
    Serial.print(temperaturaC);
    Serial.print(" C | Humedad: ");
    Serial.print(humedadPorcentaje);
    Serial.println(" %");

    // 5. Enviar a la API
    enviarAAPI(temperaturaC, humedadPorcentaje);
  }
}
