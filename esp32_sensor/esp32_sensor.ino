// =============================================================
//  ESP32 - Sensor de Humedad de Suelo Capacitivo v3.0 + DS18B20
//  + Teclado Matricial 4x4 + Menú Interactivo en LCD
//
//  Pines teclado:
//    Filas    → GPIO 13, 12, 14, 27
//    Columnas → GPIO 26, 25, 33, 32
//
//  Envía lecturas cada 20 s a la API FastAPI via HTTP POST.
//  El teclado permite navegar un menú de consultas analíticas.
// =============================================================

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Keypad.h>

// ─── Credenciales WiFi ───────────────────────────────────────
const char* ssid     = "Gato";
const char* password = "Ermelinda58";

// ─── API ─────────────────────────────────────────────────────
const char* API_BASE   = "http://192.168.101.16:8000/api/v1";
const char* API_URL    = "http://192.168.101.16:8000/api/v1/lecturas";
const char* API_KEY    = "1UmaEZRqgtvfpNQx4zcYsVwn";
const char* MAC_ESP32  = "20:43:a8:66:81:5c";

// ─── LCD I2C ─────────────────────────────────────────────────
#define SDA_PIN 22
#define SCL_PIN 23
LiquidCrystal_I2C lcd(0x27, 16, 2);

// ─── DS18B20 ─────────────────────────────────────────────────
#define PIN_DATOS_DS18B20 4
OneWire oneWire(PIN_DATOS_DS18B20);
DallasTemperature sensorTemp(&oneWire);

// ─── Sensor de humedad capacitivo ────────────────────────────
#define PIN_HUMEDAD 34
const int valorSeco   = 3400;
const int valorHumedo = 1600;

// ─── Temporización ───────────────────────────────────────────
unsigned long tiempoAnterior = 0;
const long INTERVALO = 20000;   // 20 segundos (requisito del proyecto)

// ─── Últimas lecturas en memoria ─────────────────────────────
float temperaturaC      = 0;
int   humedadPorcentaje = 0;

// ─── Teclado Matricial 4x4 ───────────────────────────────────
const byte FILAS    = 4;
const byte COLUMNAS = 4;

// Layout estándar de teclado 4x4
char teclas[FILAS][COLUMNAS] = {
  {'1', '2', '3', 'A'},
  {'4', '5', '6', 'B'},
  {'7', '8', '9', 'C'},
  {'*', '0', '#', 'D'}
};

// Pines según conexión física verificada
byte pinesFilas[FILAS]       = {13, 12, 14, 27};
byte pinesColumnas[COLUMNAS] = {26, 25, 33, 32};

Keypad teclado = Keypad(makeKeymap(teclas), pinesFilas, pinesColumnas, FILAS, COLUMNAS);

// ─── Estados del sistema ─────────────────────────────────────
enum Estado {
  MODO_NORMAL,   // Muestra sensores y envía datos
  MODO_MENU,     // Menú principal visible
  MODO_RESULTADO // Mostrando resultado de una consulta
};

Estado estadoActual = MODO_NORMAL;

// Tiempo que se muestra un resultado antes de volver al menú
unsigned long tiempoResultado   = 0;
const long    DURACION_RESULTADO = 5000;  // 5 segundos

// =============================================================
//  FUNCIONES DE DISPLAY
// =============================================================

// Limpia el LCD y escribe dos líneas (máx 16 chars cada una)
void mostrarLCD(const char* linea1, const char* linea2 = "") {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(linea1);
  lcd.setCursor(0, 1);
  lcd.print(linea2);
}

// Muestra el menú principal en el LCD
void mostrarMenu() {
  mostrarLCD("=== MENU ===", "1-7 / * salir");
}

// =============================================================
//  ENVÍO DE DATOS A LA API (POST)
// =============================================================
void enviarAAPI(float temp, int hum) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[HTTP] Sin WiFi, no se envía.");
    mostrarLCD("T:", "Sin WiFi");
    return;
  }

  HTTPClient http;
  http.begin(API_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);

  // Schema PayloadESP32: { mac_address, lecturas:[{tipo_sensor, valor}] }
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
  } else {
    Serial.print("[HTTP] Error: ");
    Serial.println(httpCode);
    Serial.println(http.getString());
  }

  http.end();
}

// =============================================================
//  CONSULTAS A LA API (GET) - Menú interactivo
// =============================================================

// Hace un GET a la URL indicada y devuelve el JSON como String.
// Retorna "" si falla.
String consultarAPI(const char* endpoint) {
  if (WiFi.status() != WL_CONNECTED) return "";

  HTTPClient http;
  String url = String(API_BASE) + endpoint;
  http.begin(url);
  http.addHeader("X-API-Key", API_KEY);

  int code = http.GET();
  String respuesta = "";
  if (code == 200) {
    respuesta = http.getString();
  } else {
    Serial.print("[GET] Error ");
    Serial.print(code);
    Serial.print(" → ");
    Serial.println(url);
  }
  http.end();
  return respuesta;
}

// ── Opción 1: Valor actual de cada sensor (tiempo real) ──────
void opcion1_valorActual() {
  // Los valores ya están en memoria, no necesita API
  char buf[17];

  // Línea 1: temperatura
  snprintf(buf, sizeof(buf), "T:%.1fC H:%d%%", temperaturaC, humedadPorcentaje);
  mostrarLCD("Sensores actual:", buf);

  Serial.print("[MENU 1] T: ");
  Serial.print(temperaturaC);
  Serial.print(" C | H: ");
  Serial.print(humedadPorcentaje);
  Serial.println(" %");
}

// ── Opción 2: Promedio de la última hora ─────────────────────
void opcion2_promedioHora() {
  mostrarLCD("Consultando...", "Prom. 1h");

  // Endpoint esperado: GET /api/v1/lecturas/estadisticas/promedio-hora?mac=...
  String url = "/lecturas/estadisticas/promedio-hora?mac=" + String(MAC_ESP32);
  String json = consultarAPI(url.c_str());

  if (json == "") {
    mostrarLCD("Prom 1h:", "Sin datos/error");
    return;
  }

  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, json);
  if (err) { mostrarLCD("Prom 1h:", "Error JSON"); return; }

  float promTemp = doc["promedio_temperatura"] | -999.0f;
  float promHum  = doc["promedio_humedad"]     | -999.0f;

  char buf[17];
  snprintf(buf, sizeof(buf), "T:%.1fC H:%.0f%%", promTemp, promHum);
  mostrarLCD("Prom ultima hora:", buf);

  Serial.print("[MENU 2] Prom T: ");
  Serial.print(promTemp);
  Serial.print(" | Prom H: ");
  Serial.println(promHum);
}

// ── Opción 3: Máximo y mínimo del día ───────────────────────
void opcion3_maxMinDia() {
  mostrarLCD("Consultando...", "Max/Min hoy");

  String url = "/lecturas/estadisticas/max-min-dia?mac=" + String(MAC_ESP32);
  String json = consultarAPI(url.c_str());

  if (json == "") {
    mostrarLCD("Max/Min dia:", "Sin datos/error");
    return;
  }

  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, json);
  if (err) { mostrarLCD("Max/Min dia:", "Error JSON"); return; }

  float maxTemp = doc["max_temperatura"] | -999.0f;
  float minTemp = doc["min_temperatura"] | -999.0f;

  char buf[17];
  snprintf(buf, sizeof(buf), "Mx:%.1f Mn:%.1f", maxTemp, minTemp);
  mostrarLCD("Max/Min temp hoy:", buf);

  Serial.print("[MENU 3] Max T: ");
  Serial.print(maxTemp);
  Serial.print(" | Min T: ");
  Serial.println(minTemp);
}

// ── Opción 4: Desviación estándar y tendencia ────────────────
void opcion4_desviacionTendencia() {
  mostrarLCD("Consultando...", "Desv / Tendencia");

  String url = "/lecturas/estadisticas/desviacion-tendencia?mac=" + String(MAC_ESP32);
  String json = consultarAPI(url.c_str());

  if (json == "") {
    mostrarLCD("Desv/Tend:", "Sin datos/error");
    return;
  }

  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, json);
  if (err) { mostrarLCD("Desv/Tend:", "Error JSON"); return; }

  float desv     = doc["desviacion_std"]  | -999.0f;
  const char* tendencia = doc["tendencia"] | "N/A";

  char buf[17];
  snprintf(buf, sizeof(buf), "s:%.2f %s", desv, tendencia);
  mostrarLCD("Desv/Tendencia:", buf);

  Serial.print("[MENU 4] Desv: ");
  Serial.print(desv);
  Serial.print(" | Tend: ");
  Serial.println(tendencia);
}

// ── Opción 5: Detección de outliers ──────────────────────────
void opcion5_outliers() {
  mostrarLCD("Consultando...", "Outliers...");

  String url = "/lecturas/estadisticas/outliers?mac=" + String(MAC_ESP32);
  String json = consultarAPI(url.c_str());

  if (json == "") {
    mostrarLCD("Outliers:", "Sin datos/error");
    return;
  }

  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, json);
  if (err) { mostrarLCD("Outliers:", "Error JSON"); return; }

  int cantidad = doc["cantidad_outliers"] | 0;

  char buf[17];
  snprintf(buf, sizeof(buf), "Detectados: %d", cantidad);
  mostrarLCD("Outliers hoy:", buf);

  Serial.print("[MENU 5] Outliers: ");
  Serial.println(cantidad);
}

// ── Opción 6: Conteo de alertas activas ──────────────────────
void opcion6_alertas() {
  mostrarLCD("Consultando...", "Alertas...");

  String url = "/lecturas/alertas/activas?mac=" + String(MAC_ESP32);
  String json = consultarAPI(url.c_str());

  if (json == "") {
    mostrarLCD("Alertas activas:", "Sin datos/error");
    return;
  }

  StaticJsonDocument<128> doc;
  DeserializationError err = deserializeJson(doc, json);
  if (err) { mostrarLCD("Alertas:", "Error JSON"); return; }

  int alertas = doc["total_alertas"] | 0;

  char buf[17];
  snprintf(buf, sizeof(buf), "Activas: %d", alertas);
  mostrarLCD("Alertas activas:", buf);

  Serial.print("[MENU 6] Alertas: ");
  Serial.println(alertas);
}

// ── Opción 7: Estado de conexión a la nube ───────────────────
void opcion7_estadoConexion() {
  bool wifiOk = (WiFi.status() == WL_CONNECTED);

  if (!wifiOk) {
    mostrarLCD("WiFi: OFFLINE", "API: sin acceso");
    Serial.println("[MENU 7] Sin WiFi");
    return;
  }

  // Hace un ping liviano a la API
  String url = "/health";   // Endpoint de health check de la API
  String json = consultarAPI(url.c_str());

  bool apiOk = (json != "");

  char linea2[17];
  snprintf(linea2, sizeof(linea2), "API: %s", apiOk ? "OK" : "ERROR");

  char linea1[17];
  snprintf(linea1, sizeof(linea1), "WiFi: %s", WiFi.localIP().toString().c_str());

  mostrarLCD(linea1, linea2);

  Serial.print("[MENU 7] WiFi OK | API: ");
  Serial.println(apiOk ? "OK" : "ERROR");
}

// =============================================================
//  PROCESAMIENTO DE TECLA PRESIONADA
// =============================================================
void procesarTecla(char tecla) {
  Serial.print("[TECLADO] Tecla: ");
  Serial.println(tecla);

  // ── Desde MODO_NORMAL: cualquier tecla abre el menú ────────
  if (estadoActual == MODO_NORMAL) {
    estadoActual = MODO_MENU;
    mostrarMenu();
    return;
  }

  // ── Desde MODO_RESULTADO: * vuelve al menú ─────────────────
  if (estadoActual == MODO_RESULTADO) {
    estadoActual = MODO_MENU;
    mostrarMenu();
    return;
  }

  // ── Desde MODO_MENU ────────────────────────────────────────
  if (estadoActual == MODO_MENU) {
    switch (tecla) {
      case '1':
        opcion1_valorActual();
        estadoActual    = MODO_RESULTADO;
        tiempoResultado = millis();
        break;
      case '2':
        opcion2_promedioHora();
        estadoActual    = MODO_RESULTADO;
        tiempoResultado = millis();
        break;
      case '3':
        opcion3_maxMinDia();
        estadoActual    = MODO_RESULTADO;
        tiempoResultado = millis();
        break;
      case '4':
        opcion4_desviacionTendencia();
        estadoActual    = MODO_RESULTADO;
        tiempoResultado = millis();
        break;
      case '5':
        opcion5_outliers();
        estadoActual    = MODO_RESULTADO;
        tiempoResultado = millis();
        break;
      case '6':
        opcion6_alertas();
        estadoActual    = MODO_RESULTADO;
        tiempoResultado = millis();
        break;
      case '7':
        opcion7_estadoConexion();
        estadoActual    = MODO_RESULTADO;
        tiempoResultado = millis();
        break;
      case '*':
        // Volver al modo normal
        estadoActual = MODO_NORMAL;
        lcd.clear();
        break;
      case '#':
        // Confirmar / refrescar menú
        mostrarMenu();
        break;
      default:
        // Tecla no asignada: recordar opciones
        mostrarLCD("Opciones: 1-7", "* salir  # ok");
        break;
    }
  }
}

// =============================================================
//  SETUP
// =============================================================
void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN);

  lcd.init();
  lcd.backlight();
  lcd.clear();

  sensorTemp.begin();
  pinMode(PIN_HUMEDAD, INPUT);

  Serial.print("MAC Address: ");
  Serial.println(WiFi.macAddress());

  // Mostrar MAC en LCD brevemente
  lcd.setCursor(0, 0);
  lcd.print("MAC:");
  lcd.setCursor(0, 1);
  lcd.print(WiFi.macAddress());
  delay(2000);

  // Conectar WiFi
  mostrarLCD("Conectando WiFi", "Espere...");
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

  char ipStr[17];
  WiFi.localIP().toString().toCharArray(ipStr, sizeof(ipStr));
  mostrarLCD("WiFi Conectado!", ipStr);
  delay(3000);

  mostrarLCD("Lista. Presiona", "tecla = menu");
  delay(2000);
  lcd.clear();
}

// =============================================================
//  LOOP PRINCIPAL
// =============================================================
void loop() {
  unsigned long tiempoActual = millis();

  // ── 1. Leer teclado (no bloqueante) ──────────────────────
  char tecla = teclado.getKey();
  if (tecla) {
    procesarTecla(tecla);
  }

  // ── 2. Auto-volver al menú tras mostrar resultado ─────────
  if (estadoActual == MODO_RESULTADO &&
      (tiempoActual - tiempoResultado >= DURACION_RESULTADO)) {
    estadoActual = MODO_MENU;
    mostrarMenu();
  }

  // ── 3. Ciclo de lectura y envío (cada 20s) ────────────────
  //    Solo envía cuando el usuario NO está en el menú,
  //    para no interrumpir la pantalla con datos del sensor.
  if (tiempoActual - tiempoAnterior >= INTERVALO) {
    tiempoAnterior = tiempoActual;

    // Leer temperatura
    sensorTemp.requestTemperatures();
    temperaturaC = sensorTemp.getTempCByIndex(0);

    // Leer humedad
    int lecturaHumedad = analogRead(PIN_HUMEDAD);
    Serial.print("RAW humedad: ");
    Serial.println(lecturaHumedad);
    humedadPorcentaje = map(lecturaHumedad, valorSeco, valorHumedo, 0, 100);
    humedadPorcentaje = constrain(humedadPorcentaje, 0, 100);

    Serial.print("Temp: ");
    Serial.print(temperaturaC);
    Serial.print(" C | Humedad: ");
    Serial.print(humedadPorcentaje);
    Serial.println(" %");

    // Enviar a la API siempre (independiente del estado del menú)
    enviarAAPI(temperaturaC, humedadPorcentaje);

    // Solo actualizar el LCD si estamos en modo normal
    if (estadoActual == MODO_NORMAL) {
      char buf[17];
      snprintf(buf, sizeof(buf), "T:%.1fC H:%d%%", temperaturaC, humedadPorcentaje);
      mostrarLCD("Sensores:", buf);
    }
  }
}
