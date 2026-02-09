#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ModbusMaster.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// --- ไลบรารีสำหรับ AI ---
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "E:/ProjectPython/models/soil_plant_mlp_isan_npk_model_data.h"

// ======================================================================
//      *** 1. ตั้งค่าโปรเจกต์และ WiFi ของคุณที่นี่ ***
// ======================================================================
const char* WIFI_SSID = "Philosopher";
const char* WIFI_PASSWORD = "12234444";
const char* GAS_URL = "https://script.google.com/macros/s/AKfycbwgfMjZDHOpwurEes4Y0Kv2POhIZ88xxNXdr4mXhPcfjWYtbTog4GOlLXugKx1bz4oQow/exec";

const char* PROJECT_ID = "แปลง";
const char* LOCATION = "17.413,103.504";
// ======================================================================

// --- การตั้งค่าจอ OLED และเซ็นเซอร์ ---
Adafruit_SSD1306 display(128, 64, &Wire, -1);
ModbusMaster node;
HardwareSerial& sensorSerial = Serial2;
const int SENSOR_SLAVE_ID = 1;
const int SENSOR_BAUD_RATE = 4800;
const int RX_PIN = 16;
const int TX_PIN = 17;

// --- ค่า Scaler ---
const float scaler_mean[8] = {54.91852941, 5.46647059, 30.14705882, 5.51470588, 90. , 0. , 1. , 1. };
const float scaler_scale[8] = {8.66318859, 0.53676103, 11.2335496 , 2.87289524, 42.42640687, 0. , 0.81649658, 0.81649658};

// ✅ **จุดที่แก้ไข 1: อัปเดตรายการพืชเป็น 22 ชนิดให้ตรงกับโมเดล AI**
const char* plant_classes_thai[] = {
    "ข้าว", "ข้าวโพด", "มันสำปะหลัง", "อ้อย", "ถั่วเขียว", "ขิง", "ขมิ้น", 
    "มะม่วง", "กล้วย", "ยางพารา", "ปาล์มน้ำมัน", "สับปะรด", "ชา", "กาแฟ", 
    "ข้าวเหนียวดำ", "กล้วยน้ำว้า", "สะตอ", "มะละกอ", "มะม่วงหิมพานต์", 
    "แตงโม", "พริก", "ยาสูบ"
};
const char* plant_classes_eng[] = {
    "Rice", "Corn", "Cassava", "Sugarcane", "MungBean", "Ginger", "Turmeric",
    "Mango", "Banana", "Rubber", "PalmOil", "Pineapple", "Tea", "Coffee",
    "BlackRice", "NamwaBanana", "Sato", "Papaya", "Cashew",
    "Watermelon", "Chilli", "Tobacco"
};
const int NUM_PLANT_CLASSES = sizeof(plant_classes_thai) / sizeof(plant_classes_thai[0]);


// --- ตัวแปรสำหรับ AI ---
const tflite::Model* model = nullptr;
tflite::MicroInterpreter* interpreter = nullptr;
TfLiteTensor* input = nullptr;
TfLiteTensor* output = nullptr;
constexpr int kTensorArenaSize = 8 * 1024;
uint8_t tensor_arena[kTensorArenaSize];

void setup() {
  Serial.begin(115200);
  tflite::InitializeTarget();
  
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  sensorSerial.begin(SENSOR_BAUD_RATE, SERIAL_8N1, RX_PIN, TX_PIN);
  node.begin(SENSOR_SLAVE_ID, sensorSerial);
  
  model = tflite::GetModel(soil_plant_mlp_isan_npk_separated_tflite);
  static tflite::MicroMutableOpResolver<5> resolver;
  resolver.AddFullyConnected(); resolver.AddRelu(); resolver.AddSoftmax(); resolver.AddReshape(); resolver.AddDequantize();
  static tflite::MicroInterpreter static_interpreter(model, resolver, tensor_arena, kTensorArenaSize);
  interpreter = &static_interpreter;
  interpreter->AllocateTensors();
  input = interpreter->input(0);
  output = interpreter->output(0);
  
  // ✅ **จุดที่แก้ไข 2: เริ่มพยายามเชื่อมต่อ WiFi แต่ไม่รอ**
  // โค้ดจะทำงานต่อไปทันที ทำให้สามารถวัดค่าได้แม้ไม่มี WiFi
  display.clearDisplay(); display.setTextSize(1); display.setTextColor(WHITE);
  display.setCursor(0,0); display.println("System Starting..."); 
  display.println("Connecting to WiFi...");
  display.display();
  Serial.println("System Starting...");
  Serial.print("Attempting to connect to WiFi...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  delay(1000); // ดีเลย์เล็กน้อยเพื่อให้ระบบพร้อม
}

void loop() {
  display.clearDisplay();
  display.setCursor(0, 0);
  display.setTextSize(1);
  display.setTextColor(WHITE);

  // ✅ **จุดที่แก้ไข 3: แสดงสถานะ WiFi ที่หน้าจอทุกรอบ**
  if (WiFi.status() == WL_CONNECTED) {
    display.println("WiFi: Connected");
  } else {
    display.println("WiFi: OFFLINE");
  }
  display.println("---------------------");
  display.display();

  Serial.println("\n-------------------- NEW CYCLE --------------------");
  Serial.printf("WiFi Status: %s\n", (WiFi.status() == WL_CONNECTED) ? "Connected" : "OFFLINE");

  uint8_t result;
  int retries = 3;
  while (retries > 0) {
    result = node.readHoldingRegisters(0x0000, 7);
    if (result == node.ku8MBSuccess) break;
    retries--;
    delay(300);
  }

  if (result == node.ku8MBSuccess) {
    float moisture = (int16_t)node.getResponseBuffer(0) / 10.0;
    float temp     = (int16_t)node.getResponseBuffer(1) / 10.0;
    float ec       = (int16_t)node.getResponseBuffer(2);
    float pH       = (int16_t)node.getResponseBuffer(3) / 10.0;
    float N        = (int16_t)node.getResponseBuffer(4);
    float P        = (int16_t)node.getResponseBuffer(5);
    float K        = (int16_t)node.getResponseBuffer(6);
    float region_input = 0.0, soil_type_input = 0.0, season_input = 0.0;
    float input_data[8] = {moisture, pH, N, P, K, region_input, soil_type_input, season_input};
    for (int i = 0; i < 8; i++) {
        input->data.int8[i] = (input_data[i] - scaler_mean[i]) / scaler_scale[i] / input->params.scale + input->params.zero_point;
    }
    interpreter->Invoke();

    int top_plant_index = -1;
    float top_plant_score = -1.0f;
    for (int i = 0; i < NUM_PLANT_CLASSES; i++) {
        float dequantized_score = ((float)output->data.int8[i] - output->params.zero_point) * output->params.scale;
        if (dequantized_score > top_plant_score) {
            top_plant_score = dequantized_score;
            top_plant_index = i;
        }
    }
    
    String top_plant_name_eng = (top_plant_index != -1) ? plant_classes_eng[top_plant_index] : "N/A";
    String top_plant_name_thai = (top_plant_index != -1) ? plant_classes_thai[top_plant_index] : "N/A";

    Serial.println(">>> Sensor & AI Data <<<");
    Serial.printf(" > Moisture: %.1f%%, pH: %.1f, Temp: %.1f C, EC: %.0f\n", moisture, pH, temp, ec);
    Serial.printf(" > N: %.0f, P: %.0f, K: %.0f\n", N, P, K);
    Serial.printf(" > Top Plant (TH): %s (%.1f%%)\n", top_plant_name_thai.c_str(), top_plant_score * 100.0);
    
    // แสดงผลบนจอ OLED (ส่วนนี้จะทำงานเสมอ ไม่ว่าจะมี WiFi หรือไม่)
    display.printf("N: %.0f  P: %.0f  K: %.0f\n", N, P, K);
    display.printf("Moist: %.1f%% pH: %.1f\n", moisture, pH);
    display.println("---------------------");
    display.printf("Plant: %s\n", top_plant_name_eng.c_str());
    display.printf("Score: %.0f%%\n", top_plant_score * 100.0); 
    display.display();
    
    // ✅ **จุดที่แก้ไข 4: ตรวจสอบ WiFi ก่อนส่งข้อมูล**
    // บล็อกนี้จะทำงาน 'เฉพาะเมื่อ' เชื่อมต่อ WiFi ได้สำเร็จเท่านั้น
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(GAS_URL);
      http.addHeader("Content-Type", "application/json");
      StaticJsonDocument<2048> doc;
      doc["ProjectId"] = PROJECT_ID;
      doc["Location"] = LOCATION;
      doc["Moisture"] = moisture;
      doc["PH"] = pH;
      doc["N"] = N;
      doc["P"] = P;
      doc["K"] = K;
      doc["Temp"] = temp;
      doc["EC"] = ec;
      JsonArray plants = doc.createNestedArray("plants");
      for (int i = 0; i < NUM_PLANT_CLASSES; i++) {
          float dequantized_score = ((float)output->data.int8[i] - output->params.zero_point) * output->params.scale;
          JsonObject plant = plants.createNestedObject();
          plant["plant"] = plant_classes_thai[i]; 
          plant["suitability"] = dequantized_score * 100.0;
      }
      String json_output;
      serializeJson(doc, json_output);
      Serial.println("\nWiFi Connected. Sending data to Google Sheets...");
      int httpResponseCode = http.POST(json_output);
      Serial.printf("HTTP Response: %d\n", httpResponseCode);
      http.end();
    } else {
      Serial.println("\nWiFi not connected. Skipping data upload.");
    }
  } else {
    Serial.println("Sensor Reading FAILED!");
    display.clearDisplay();
    display.setCursor(0,0);
    display.setTextSize(2);
    display.println("SENSOR FAILED");
    display.display();
  }
  
  Serial.println("End of cycle. Waiting 30 seconds...");
  delay(30000); // คงการหน่วงเวลา 30 วินาทีไว้ตามที่คุณต้องการ
}