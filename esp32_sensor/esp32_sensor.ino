/*
 * ============================================================
 *  SISTEMA DE MONITOREO AGRÍCOLA - ESP32
 *  TALLER 1 - CORTE 2 - MINERÍA DE DATOS
 *
 *  Fusión: envío HTTP a API (FastAPI/PostgreSQL+TimescaleDB)
 *  + teclado matricial + analítica local en LCD
 *
 *  Mapa de teclas exigido por el taller:
 *   1 -> Valor actual de cada sensor (tiempo real)
 *   2 -> Promedio de la última hora
 *   3 -> Máximo y mínimo del día
 *   4 -> Desviación estándar y tendencia
 *   5 -> Detección de valores atípicos (outliers)
 *   6 -> Conteo de alertas activas
 *   7 -> Estado de conexión a la nube
 *   # -> Volver al inicio
 *   * -> Confirmar / volver (equivalente a #)
 * ============================================================
 */

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Keypad.h>
#include <math.h>

// ============================================================
//  CONFIGURACIÓN DE RED
// ============================================================
const char* ssid     = "Gato";
const char* password = "Ermelinda58";

// ============================================================
//  CONFIGURACIÓN API
// ============================================================
const char* API_URL   = "https://parcial-bryan.onrender.com/api/v1/lecturas";
const char* API_KEY   = "1UmaEZRqgtvfpNQx4zcYsVwn";
const char* MAC_ESP32 = "20:43:a8:66:81:5c";

// ============================================================
//  CONFIGURACIÓN LCD I2C
// ============================================================
#define SDA_PIN    22
#define SCL_PIN    23
#define ANCHO_LCD  16
#define ALTO_LCD    2
LiquidCrystal_I2C lcd(0x27, ANCHO_LCD, ALTO_LCD);

// ============================================================
//  CONFIGURACIÓN DS18B20
// ============================================================
#define PIN_DATOS_DS18B20 4
OneWire oneWire(PIN_DATOS_DS18B20);
DallasTemperature sensorTemp(&oneWire);

// ============================================================
//  CONFIGURACIÓN SENSOR DE HUMEDAD CAPACITIVO
// ============================================================
#define PIN_HUMEDAD 34
int valorSeco   = 3400;
int valorHumedo = 1600;

// ============================================================
//  UMBRAL DE ALARMA / ALERTA
// ============================================================
const float UMBRAL_ALTA_TEMP = 30.0; // °C

// ============================================================
//  CONFIGURACIÓN TECLADO MATRICIAL 4x4
// ============================================================
const byte FILAS     = 4;
const byte COLUMNAS  = 4;
char teclas[FILAS][COLUMNAS] = {
  {'1','2','3','A'},
  {'4','5','6','B'},
  {'7','8','9','C'},
  {'*','0','#','D'}
};
byte pinesFilas[FILAS]       = {13, 12, 14, 27}; // Filas: D13, D12, D14, D27
byte pinesColumnas[COLUMNAS] = {26, 25, 33, 32};
Keypad teclado = Keypad(makeKeymap(teclas), pinesFilas, pinesColumnas, FILAS, COLUMNAS);

// ============================================================
//  MÁQUINA DE ESTADOS DE PANTALLA
// ============================================================
enum EstadoPantalla {
  PANTALLA_INICIO,           // pantalla de reposo
  PANTALLA_TIEMPO_REAL,      // tecla 1
  PANTALLA_PROMEDIO_HORA,    // tecla 2
  PANTALLA_MAX_MIN_DIA,      // tecla 3
  PANTALLA_DESV_TENDENCIA,   // tecla 4
  PANTALLA_OUTLIERS,         // tecla 5
  PANTALLA_ALERTAS,          // tecla 6
  PANTALLA_CONEXION_NUBE     // tecla 7
};
EstadoPantalla estadoActual = PANTALLA_INICIO;

// ============================================================
//  VARIABLES DE LECTURA
// ============================================================
float temperaturaC        = 0;
int   lecturaHumedadCruda = 0;
int   humedadPorcentaje   = 0;

float temperaturaMin = 999.0;   // Min/Max desde el encendido
float temperaturaMax = -999.0;
bool  primeraLectura = true;

// Buffer circular: 180 muestras × 20 s = 1 hora exacta
#define TAM_BUFFER 180
float bufferTemp[TAM_BUFFER];
float bufferHum[TAM_BUFFER];
int   indiceBuffer    = 0;
int   muestrasGuardadas = 0;

// ============================================================
//  TEMPORIZADORES NO BLOQUEANTES
// ============================================================
unsigned long tiempoAnteriorCaptura   = 0;
const long    intervaloCaptura        = 20000; // 20 s — exigido por el taller

unsigned long tiempoAnteriorLCD       = 0;
const long    intervaloLCD            = 1000;

unsigned long tiempoAnteriorWifiCheck = 0;
const long    intervaloWifiCheck      = 2000;

unsigned long tiempoUltimaTecla       = 0;
const long    TIEMPO_INACTIVIDAD      = 15000;

unsigned long tiempoAnteriorConexion  = 0;
const long    intervaloConexion       = 60000; // reportar estado cada 60 s

// ============================================================
//  ESTADO DE CONEXIÓN
// ============================================================
bool wifiConectado     = false;
bool nubeConectada     = false;
bool wifiAnterior      = false; // para detectar cambios de estado
int  contadorReintentos = 0;

// ============================================================
//  SETUP
// ============================================================
void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN);

  lcd.init();
  lcd.backlight();
  lcd.clear();

  sensorTemp.begin();
  pinMode(PIN_HUMEDAD, INPUT);

  teclado.setDebounceTime(25);
  teclado.setHoldTime(500);

  // Mostrar MAC en Serial (útil para configurar la API)
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

  // Intento con timeout de 15 s para no bloquear indefinidamente
  unsigned long inicioIntento = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - inicioIntento < 15000) {
    delay(500);
    Serial.print(".");
  }

  wifiConectado = (WiFi.status() == WL_CONNECTED);
  wifiAnterior  = wifiConectado;

  // Reportar estado inicial de conexión
  if (wifiConectado) reportarConexion(true);

  lcd.clear();
  if (wifiConectado) {
    Serial.println("\nWiFi conectado.");
    Serial.print("IP asignada: ");
    Serial.println(WiFi.localIP());
    lcd.setCursor(0, 0);
    lcd.print("WiFi Conectado!");
    lcd.setCursor(0, 1);
    lcd.print(WiFi.localIP());
  } else {
    Serial.println("\nSin WiFi. Modo local activo.");
    lcd.setCursor(0, 0);
    lcd.print("Sin conexion");
    lcd.setCursor(0, 1);
    lcd.print("Modo local");
  }

  delay(2500);

  // Primera captura inmediata
  capturarSensores();
  lcd.clear();
  tiempoUltimaTecla = millis();
  dibujarPantalla();
}

// ============================================================
//  LOOP PRINCIPAL
// ============================================================
void loop() {
  unsigned long ahora = millis();

  // --- Leer teclado ---
  char tecla = teclado.getKey();
  if (tecla) {
    tiempoUltimaTecla = ahora;
    procesarTecla(tecla);
  }

  // --- Captura + envío cada 20 segundos ---
  if (ahora - tiempoAnteriorCaptura >= intervaloCaptura) {
    tiempoAnteriorCaptura = ahora;
    capturarSensores();
    enviarAAPI(temperaturaC, humedadPorcentaje);
  }

  // --- Verificar estado WiFi periódicamente ---
  if (ahora - tiempoAnteriorWifiCheck >= intervaloWifiCheck) {
    tiempoAnteriorWifiCheck = ahora;
    bool wifiAhora = (WiFi.status() == WL_CONNECTED);

    // Detectar cambio de estado (perdió o recuperó conexión)
    if (wifiAhora != wifiAnterior) {
      if (!wifiAhora) contadorReintentos++;
      reportarConexion(wifiAhora);
      wifiAnterior = wifiAhora;
    }

    wifiConectado = wifiAhora;
    if (!wifiConectado) nubeConectada = false;
  }

  // --- Reportar estado de conexión periódicamente (cada 60s) ---
  if (ahora - tiempoAnteriorConexion >= intervaloConexion) {
    tiempoAnteriorConexion = ahora;
    reportarConexion(wifiConectado);
  }

  // --- Volver al inicio por inactividad ---
  if (estadoActual != PANTALLA_INICIO &&
      (ahora - tiempoUltimaTecla >= TIEMPO_INACTIVIDAD)) {
    estadoActual = PANTALLA_INICIO;
    lcd.clear();
    dibujarPantalla();
  }

  // --- Refrescar LCD cada segundo ---
  if (ahora - tiempoAnteriorLCD >= intervaloLCD) {
    tiempoAnteriorLCD = ahora;
    dibujarPantalla();
  }
}

// ============================================================
//  CAPTURA DE SENSORES + BUFFER DE ANALÍTICA
// ============================================================
void capturarSensores() {
  // Temperatura DS18B20
  sensorTemp.requestTemperatures();
  temperaturaC = sensorTemp.getTempCByIndex(0);

  if (temperaturaC != DEVICE_DISCONNECTED_C) {
    if (primeraLectura) {
      temperaturaMin = temperaturaC;
      temperaturaMax = temperaturaC;
      primeraLectura = false;
    } else {
      if (temperaturaC < temperaturaMin) temperaturaMin = temperaturaC;
      if (temperaturaC > temperaturaMax) temperaturaMax = temperaturaC;
    }
  }

  // Humedad capacitiva
  lecturaHumedadCruda = analogRead(PIN_HUMEDAD);
  Serial.print("RAW humedad: ");
  Serial.println(lecturaHumedadCruda);
  humedadPorcentaje = map(lecturaHumedadCruda, valorSeco, valorHumedo, 0, 100);
  humedadPorcentaje = constrain(humedadPorcentaje, 0, 100);

  // Guardar en buffer circular (alimenta teclas 2, 4 y 5)
  bufferTemp[indiceBuffer] = temperaturaC;
  bufferHum[indiceBuffer]  = (float)humedadPorcentaje;
  indiceBuffer = (indiceBuffer + 1) % TAM_BUFFER;
  if (muestrasGuardadas < TAM_BUFFER) muestrasGuardadas++;

  Serial.print("Temp: ");
  Serial.print(temperaturaC);
  Serial.print(" C | Humedad: ");
  Serial.print(humedadPorcentaje);
  Serial.print(" % | Muestras en buffer: ");
  Serial.println(muestrasGuardadas);
}

// ============================================================
//  ENVÍO A LA API (FastAPI → PostgreSQL + TimescaleDB)
// ============================================================
void enviarAAPI(float temp, int hum) {
  if (!wifiConectado) {
    Serial.println("[HTTP] Sin WiFi, no se envía.");
    return;
  }

  HTTPClient http;
  http.begin(API_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);

  // Schema PayloadESP32:
  // { "mac_address": "...", "lecturas": [
  //     {"tipo_sensor": "temperatura_ds18b20",      "valor": 24.6},
  //     {"tipo_sensor": "humedad_suelo_capacitivo",  "valor": 63.0}
  // ]}
  StaticJsonDocument<256> doc;
  doc["mac_address"] = MAC_ESP32;

  JsonArray lecturas = doc.createNestedArray("lecturas");

  JsonObject lecTemp = lecturas.createNestedObject();
  lecTemp["tipo_sensor"] = "temperatura_ds18b20";
  lecTemp["valor"]       = temp;

  JsonObject lecHum = lecturas.createNestedObject();
  lecHum["tipo_sensor"] = "humedad_suelo_capacitivo";
  lecHum["valor"]       = (float)hum;

  String body;
  serializeJson(doc, body);

  Serial.print("[HTTP] POST → ");
  Serial.println(body);

  int httpCode = http.POST(body);

  if (httpCode == 201) {
    Serial.println("[HTTP] Lecturas guardadas OK (201)");
    nubeConectada = true;
  } else {
    Serial.print("[HTTP] Error: ");
    Serial.println(httpCode);
    Serial.println(http.getString());
    nubeConectada = false;
  }

  http.end();
}

// ============================================================
//  FUNCIONES DE ANALÍTICA SOBRE EL BUFFER
// ============================================================
float calcularPromedio(float* buffer, int n) {
  if (n == 0) return 0;
  float suma = 0;
  for (int i = 0; i < n; i++) suma += buffer[i];
  return suma / n;
}

float calcularDesviacionEstandar(float* buffer, int n, float promedio) {
  if (n < 2) return 0;
  float sumaCuadrados = 0;
  for (int i = 0; i < n; i++) {
    float d = buffer[i] - promedio;
    sumaCuadrados += d * d;
  }
  return sqrt(sumaCuadrados / n);
}

// Tendencia simple: compara promedio de la primera mitad del buffer
// contra la segunda mitad.
const char* calcularTendencia(float* buffer, int n) {
  if (n < 4) return "SIN DATOS";
  int   mitad         = n / 2;
  float promedioInicio = calcularPromedio(buffer, mitad);
  float promedioFinal  = calcularPromedio(buffer + mitad, n - mitad);
  float diferencia     = promedioFinal - promedioInicio;
  if (diferencia > 0.3)  return "SUBIENDO";
  if (diferencia < -0.3) return "BAJANDO";
  return "ESTABLE";
}

// Outlier por z-score: ¿la última lectura supera 2 desviaciones estándar?
bool esOutlier(float ultimoValor, float promedio, float desviacion) {
  if (desviacion == 0) return false;
  float z = fabs(ultimoValor - promedio) / desviacion;
  return z > 2.0;
}

int contarAlertas() {
  int contador = 0;
  for (int i = 0; i < muestrasGuardadas; i++) {
    if (bufferTemp[i] >= UMBRAL_ALTA_TEMP) contador++;
  }
  return contador;
}

// ============================================================
//  REPORTE DE ESTADO DE CONEXIÓN A LA API
// ============================================================
void reportarConexion(bool conectado) {
  if (!conectado) {
    Serial.println("[CONEXION] Sin WiFi, no se reporta estado.");
    return;
  }

  HTTPClient http;
  http.begin("https://parcial-bryan.onrender.com/api/v1/conexion");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);

  int rssi = WiFi.RSSI();

  StaticJsonDocument<200> doc;
  doc["mac_address"]        = MAC_ESP32;
  doc["conectado"]          = conectado;
  doc["rssi_dbm"]           = rssi;
  doc["reintentos"]         = contadorReintentos;
  doc["lecturas_en_buffer"] = muestrasGuardadas;

  String body;
  serializeJson(doc, body);

  int httpCode = http.POST(body);
  Serial.print("[CONEXION] Estado reportado → HTTP ");
  Serial.print(httpCode);
  Serial.print(" | RSSI: ");
  Serial.print(rssi);
  Serial.println(" dBm");
  http.end();
}

// ============================================================
//  REPORTE DE TECLA PULSADA A LA API
// ============================================================
void reportarTecla(char tecla) {
  if (!wifiConectado) return;

  HTTPClient http;
  http.begin("https://parcial-bryan.onrender.com/api/v1/menu");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);

  StaticJsonDocument<128> doc;
  doc["mac_address"] = MAC_ESP32;
  char teclaStr[2] = { tecla, '\0' };
  doc["tecla"] = teclaStr;

  String body;
  serializeJson(doc, body);

  int httpCode = http.POST(body);
  Serial.print("[MENU] Tecla '");
  Serial.print(tecla);
  Serial.print("' reportada → HTTP ");
  Serial.println(httpCode);
  http.end();
}

// ============================================================
//  NAVEGACIÓN — acceso directo por número, según tabla del taller
// ============================================================
void procesarTecla(char tecla) {
  switch (tecla) {
    case '1': estadoActual = PANTALLA_TIEMPO_REAL;    reportarTecla(tecla); break;
    case '2': estadoActual = PANTALLA_PROMEDIO_HORA;  reportarTecla(tecla); break;
    case '3': estadoActual = PANTALLA_MAX_MIN_DIA;    reportarTecla(tecla); break;
    case '4': estadoActual = PANTALLA_DESV_TENDENCIA; reportarTecla(tecla); break;
    case '5': estadoActual = PANTALLA_OUTLIERS;       reportarTecla(tecla); break;
    case '6': estadoActual = PANTALLA_ALERTAS;        reportarTecla(tecla); break;
    case '7': estadoActual = PANTALLA_CONEXION_NUBE;  reportarTecla(tecla); break;
    case '#': // Volver al inicio
    case '*': // Confirmar / volver (misma función que '#')
      estadoActual = PANTALLA_INICIO;
      break;
    default:
      break; // 0, 8, 9, A, B, C, D sin función asignada
  }
  lcd.clear();
  dibujarPantalla();
}

// ============================================================
//  DIBUJO EN LCD
// ============================================================
void dibujarPantalla() {
  switch (estadoActual) {
    case PANTALLA_INICIO:         dibujarInicio();        break;
    case PANTALLA_TIEMPO_REAL:    dibujarTiempoReal();    break;
    case PANTALLA_PROMEDIO_HORA:  dibujarPromedioHora();  break;
    case PANTALLA_MAX_MIN_DIA:    dibujarMaxMinDia();     break;
    case PANTALLA_DESV_TENDENCIA: dibujarDesvTendencia(); break;
    case PANTALLA_OUTLIERS:       dibujarOutliers();      break;
    case PANTALLA_ALERTAS:        dibujarAlertas();       break;
    case PANTALLA_CONEXION_NUBE:  dibujarConexionNube();  break;
  }
}

// --- Pantalla de reposo ---
void dibujarInicio() {
  lcd.setCursor(0, 0);
  lcd.print("T:");
  lcd.print(temperaturaC, 1);
  lcd.print("C H:");
  lcd.print(humedadPorcentaje);
  lcd.print("%  ");
  lcd.setCursor(0, 1);
  lcd.print("1-7 Menu Datos  ");
}

// --- Tecla 1: Valor actual de cada sensor (tiempo real) ---
void dibujarTiempoReal() {
  lcd.setCursor(0, 0);
  lcd.print("Temp: ");
  lcd.print(temperaturaC, 1);
  lcd.print(" C   ");
  lcd.setCursor(0, 1);
  lcd.print("Hum: ");
  lcd.print(humedadPorcentaje);
  lcd.print("% ADC:");
  lcd.print(lecturaHumedadCruda);
}

// --- Tecla 2: Promedio de la última hora ---
void dibujarPromedioHora() {
  float promT = calcularPromedio(bufferTemp, muestrasGuardadas);
  float promH = calcularPromedio(bufferHum,  muestrasGuardadas);
  lcd.setCursor(0, 0);
  lcd.print("Prom 1h T:");
  lcd.print(promT, 1);
  lcd.print("C  ");
  lcd.setCursor(0, 1);
  lcd.print("Prom 1h H:");
  lcd.print((int)promH);
  lcd.print("%   ");
}

// --- Tecla 3: Máximo y mínimo del día ---
void dibujarMaxMinDia() {
  lcd.setCursor(0, 0);
  lcd.print("Max dia: ");
  lcd.print(temperaturaMax, 1);
  lcd.print("C ");
  lcd.setCursor(0, 1);
  lcd.print("Min dia: ");
  lcd.print(temperaturaMin, 1);
  lcd.print("C ");
}

// --- Tecla 4: Desviación estándar y tendencia ---
void dibujarDesvTendencia() {
  float promT = calcularPromedio(bufferTemp, muestrasGuardadas);
  float desvT = calcularDesviacionEstandar(bufferTemp, muestrasGuardadas, promT);
  const char* tendencia = calcularTendencia(bufferTemp, muestrasGuardadas);
  lcd.setCursor(0, 0);
  lcd.print("DesvEst T:");
  lcd.print(desvT, 2);
  lcd.print("  ");
  lcd.setCursor(0, 1);
  lcd.print("Tend: ");
  lcd.print(tendencia);
  lcd.print("   ");
}

// --- Tecla 5: Detección de valores atípicos (outliers) ---
void dibujarOutliers() {
  float promT = calcularPromedio(bufferTemp, muestrasGuardadas);
  float desvT = calcularDesviacionEstandar(bufferTemp, muestrasGuardadas, promT);
  bool  outlier = esOutlier(temperaturaC, promT, desvT);
  lcd.setCursor(0, 0);
  lcd.print("Analisis Outlier");
  lcd.setCursor(0, 1);
  if (muestrasGuardadas < 5) {
    lcd.print("Datos insuf.    ");
  } else if (outlier) {
    lcd.print("DETECTADO!      ");
  } else {
    lcd.print("Normal          ");
  }
}

// --- Tecla 6: Conteo de alertas activas ---
void dibujarAlertas() {
  int alertas = contarAlertas();
  lcd.setCursor(0, 0);
  lcd.print("Alertas activas:");
  lcd.setCursor(0, 1);
  lcd.print(alertas);
  lcd.print(" de ");
  lcd.print(muestrasGuardadas);
  lcd.print(" muestras   ");
}

// --- Tecla 7: Estado de conexión a la nube ---
void dibujarConexionNube() {
  lcd.setCursor(0, 0);
  lcd.print("WiFi: ");
  lcd.print(wifiConectado ? "OK   " : "FALLO");
  lcd.setCursor(0, 1);
  lcd.print("Nube: ");
  lcd.print(nubeConectada ? "OK   " : "FALLO");
}
