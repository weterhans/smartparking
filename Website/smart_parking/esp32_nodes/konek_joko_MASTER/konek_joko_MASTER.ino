#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>   
#include <Preferences.h>
#include <Keypad.h>
#include <DMD32.h>
#include "fonts/Arial_black_16.h"

#define DISPLAYS_ACROSS 2
#define DISPLAYS_DOWN 1
DMD dmd(DISPLAYS_ACROSS, DISPLAYS_DOWN);

hw_timer_t * timer = NULL;
void IRAM_ATTR triggerScan() {
  dmd.scanDisplayBySPI();
}

Preferences preferences;

// Pin Mapping Relay (Urutan Baru yang Berurutan Sejajar)
const int relayPins[6] = {13, 12, 14, 17, 16, 4}; 

// Pin Mapping Keypad
const byte ROWS = 2; 
const byte COLS = 3; 
char keys[ROWS][COLS] = {
  {'1','2','3'},
  {'4','5','6'}
};
byte rowPins[ROWS] = {32, 33}; 
byte colPins[COLS] = {25, 26, 27}; 
Keypad customKeypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

// MAC Address Sistem Informasi (Joko)
uint8_t jokoAddress[] = {0xD4, 0xE9, 0xF4, 0xE2, 0xE4, 0xB4};

// ========================================================
// STRUKTUR DATA ESP-NOW
// ========================================================
// 1. Data dari Slave Sensor Anda (6 float = 24 byte)
typedef struct struct_sensor {
  float distances[6];
} struct_sensor;
struct_sensor sensorData;
volatile bool flagDataSensorBaru = false; 

// 2. Data komunikasi dengan Joko (Sistem Informasi) (64 char = 64 byte)
typedef struct struct_info {
  char text[64];
} struct_info;
struct_info msgToJoko;
struct_info msgFromJoko;
volatile bool flagPesanJokoBaru = false;

// ========================================================
// VARIABEL STATE PARKIR
// ========================================================
// 0 = KOSONG (Flap Naik, Relay HIGH)
// 1 = TUNGGU MASUK (Flap Rata, Relay LOW)
// 2 = TERISI (Flap Naik, Relay HIGH)
// 3 = MAU KELUAR (Flap Rata, Relay LOW)
int slotState[6] = {0, 0, 0, 0, 0, 0}; 

// Variabel Gembok Virtual untuk Slot Member
bool isReserved[6] = {false, false, false, false, false, false};
String savedCarType[6] = {"-", "-", "-", "-", "-", "-"}; 

void simpanKeMemori() {
  if(timer != NULL) timerAlarmDisable(timer); 
  delay(5);
  preferences.putBytes("states", slotState, sizeof(slotState));
  for(int i=0; i<6; i++) {
    String key = "car" + String(i);
    preferences.putString(key.c_str(), savedCarType[i]);
  }
  delay(5);
  if(timer != NULL) timerAlarmEnable(timer);
}

// ========================================================
// VARIABEL RUNNING TEXT P10
// ========================================================
String currentScrollText = "";
char marqueeBuffer[100] = ""; 
String pesanPrioritas = "";
unsigned long waktuPrioritas = 0;
unsigned long lastMarqueeStep = 0;
const int speedMarquee = 40; 

void tampilkanPesanPrioritas(String pesan) {
  pesanPrioritas = pesan;
  waktuPrioritas = millis(); 
}

void perbaruiTeksP10() {
  String teksBaru = "";
  if (pesanPrioritas != "" && (millis() - waktuPrioritas < 10000)) {
    teksBaru = pesanPrioritas; 
  } else {
    pesanPrioritas = ""; 
    int slotKosong = 0;
    for(int i = 0; i < 6; i++) {
      if(slotState[i] == 0) slotKosong++;
    }
    if (slotKosong == 0) {
      teksBaru = "PARKIR PENUH";
    } else {
      teksBaru = "TERSEDIA " + String(slotKosong);
    }
  }

  if (currentScrollText != teksBaru) {
    currentScrollText = teksBaru;
    currentScrollText.toCharArray(marqueeBuffer, sizeof(marqueeBuffer));
    dmd.clearScreen(true);
    dmd.drawMarquee(marqueeBuffer, currentScrollText.length(), (32 * DISPLAYS_ACROSS) - 1, 0); 
  }
}

void handleMarquee() {
  if (millis() - lastMarqueeStep > speedMarquee) {
    lastMarqueeStep = millis();
    bool isFinished = dmd.stepMarquee(-1, 0); 
    if (isFinished) {
      dmd.drawMarquee(marqueeBuffer, currentScrollText.length(), (32 * DISPLAYS_ACROSS) - 1, 0);
    }
  }
}

// Tampilan monitoring mendetail dengan 4 State
void tampilkanMonitoring() {
  Serial.println("\n==================== STATUS KONDISI SLOT PARKIR ====================");
  for(int i = 0; i < 6; i++) {
    Serial.print("Slot "); Serial.print(i + 1);
    Serial.print(" | Status: "); Serial.print(slotState[i]);
    
    if(slotState[i] == 0) {
      Serial.println(" | [KOSONG] - Flaplock NAIK");
    } else if (slotState[i] == 1) {
      Serial.print(" | [TUNGGU MASUK] - Flaplock RATA | Jenis: "); Serial.println(savedCarType[i]);
    } else if(slotState[i] == 2) {
      Serial.print(" | [TERISI] - Flaplock NAIK | Jenis: "); Serial.println(savedCarType[i]);
    } else if (slotState[i] == 3) {
      Serial.print(" | [MAU KELUAR] - Flaplock RATA | Jenis: "); Serial.println(savedCarType[i]);
    }
  }
  Serial.println("====================================================================\n");
}

// ========================================================
// FUNGSI KOMUNIKASI JOKO
// ========================================================
void kirimStatusKeJoko() {
  // Format: STAT:0,K,B,0,M,0
  // 0 = Kosong
  // K = Mobil Kecil
  // B = Mobil Besar
  // M = Member
  String status = "STAT:";
  for (int i = 0; i < 6; i++) {
    if (slotState[i] == 0) {
      status += "0";
    } else {
      if (savedCarType[i] == "CITY CAR" || savedCarType[i] == "K") {
        status += "K";
      } else if (savedCarType[i] == "MEMBER") {
        status += "M";
      } else {
        status += "B"; // SUV, MPV, dll
      }
    }
    if (i < 5) status += ",";
  }
  strncpy(msgToJoko.text, status.c_str(), sizeof(msgToJoko.text));
  esp_now_send(jokoAddress, (uint8_t *) &msgToJoko, sizeof(msgToJoko));
  Serial.println("[ESP-NOW] Mengirim status ke Joko: " + status);
}

void kirimPayReqKeJoko(int slotIdx) {
  // Format: PAYREQ:1
  String req = "PAYREQ:" + String(slotIdx + 1);
  strncpy(msgToJoko.text, req.c_str(), sizeof(msgToJoko.text));
  esp_now_send(jokoAddress, (uint8_t *) &msgToJoko, sizeof(msgToJoko));
  Serial.println("[ESP-NOW] Mengirim request bayar ke Joko: " + req);
}

// Callback saat data Master berhasil atau gagal dikirim
void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  // Filter hanya untuk MAC Address Joko agar tidak menuh-menuhin Serial Monitor
  if (mac_addr[0] == jokoAddress[0] && mac_addr[5] == jokoAddress[5]) {
    Serial.print("[KONEKSI JOKO] Mengirim data ke Joko... ");
    Serial.println(status == ESP_NOW_SEND_SUCCESS ? "BERHASIL (TERHUBUNG)" : "GAGAL (JOKO MATI / JAUH)");
  }
}

// Callback ESP-NOW: Memisahkan berdasarkan panjang data (len)
void OnDataRecv(const uint8_t * mac, const uint8_t *incomingData, int len) {
  if (len == sizeof(struct_sensor)) {
    // Pesan dari Slave Sensor Anda (24 byte)
    memcpy(&sensorData, incomingData, sizeof(sensorData));
    flagDataSensorBaru = true; 
  } 
  else if (len == sizeof(struct_info)) {
    // Pesan dari Sistem Informasi Joko (64 byte)
    memcpy(&msgFromJoko, incomingData, sizeof(msgFromJoko));
    flagPesanJokoBaru = true;
  }
}

int alokasiSlot(char gol) {
  int slotReguler[] = {2, 3, 0, 5}; 
  if (gol == 'K') { 
    if (slotState[1] == 0 && !isReserved[1]) return 1; 
    if (slotState[4] == 0 && !isReserved[4]) return 4; 
    for (int i = 0; i < 4; i++) {
      if (slotState[slotReguler[i]] == 0 && !isReserved[slotReguler[i]]) return slotReguler[i];
    }
  } 
  else if (gol == 'B') { 
    for (int i = 0; i < 4; i++) {
      if (slotState[slotReguler[i]] == 0 && !isReserved[slotReguler[i]]) return slotReguler[i];
    }
    if (slotState[1] == 0 && !isReserved[1]) return 1; 
    if (slotState[4] == 0 && !isReserved[4]) return 4; 
  }
  return -1; 
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);

  // Kunci channel ke 1 agar sinkron dengan pengirim
  esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);
  Serial.println("[WiFi] Channel dikunci ke 1 (sinkron dengan pengirim ESP-NOW)");
  
  preferences.begin("parkir", false);
  if (preferences.getBytesLength("states") > 0) {
    preferences.getBytes("states", slotState, sizeof(slotState));
    for(int i=0; i<6; i++) {
      String key = "car" + String(i);
      savedCarType[i] = preferences.getString(key.c_str(), "-");
    }
  }
  
  // Set inisial kondisi relay flap berdasarkan state tersimpan
  for(int i = 0; i < 6; i++) {
    pinMode(relayPins[i], OUTPUT);
    if (slotState[i] == 0 || slotState[i] == 2) {
      digitalWrite(relayPins[i], HIGH); // Flap Naik
    } else {
      digitalWrite(relayPins[i], LOW);  // Flap Rata (Tunggu Masuk / Mau Keluar)
    }
  }

  if (esp_now_init() == ESP_OK) {
    esp_now_register_recv_cb(OnDataRecv);
    
    // Mendaftarkan callback status kirim (berhasil/gagal)
    esp_now_register_send_cb(OnDataSent);
    
    // Daftarkan Joko sebagai Peer untuk mengirim data
    esp_now_peer_info_t peerInfoJoko;
    memset(&peerInfoJoko, 0, sizeof(peerInfoJoko)); 
    memcpy(peerInfoJoko.peer_addr, jokoAddress, 6);
    peerInfoJoko.channel = 1; 
    peerInfoJoko.encrypt = false;
    
    if (esp_now_add_peer(&peerInfoJoko) != ESP_OK) {
      Serial.println("Gagal mendaftarkan Peer Joko!");
    } else {
      Serial.println("Peer Joko berhasil didaftarkan.");
    }
  }

  dmd.clearScreen(true);
  dmd.selectFont(Arial_Black_16); 

  uint8_t cpuClock = ESP.getCpuFreqMHz();
  timer = timerBegin(0, cpuClock, true);
  timerAttachInterrupt(timer, &triggerScan, true);
  timerAlarmWrite(timer, 1000, true); 
  timerAlarmEnable(timer);

  Serial.println("\n=== SISTEM MONITORING & INFORMASI READY ===");
  Serial.println("Ketik 'K' (City Car) atau 'B' (SUV/MPV) di Serial Monitor untuk simulasi kendaraan masuk.");
  tampilkanMonitoring();
  
  // Kirim status inisial ke Joko
  kirimStatusKeJoko();
}

void prosesDeteksiKendaraanSerial() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    if (input.length() == 0) return;
    
    input.toUpperCase();
    
    char golongan = ' ';
    String jenisMobil = input;
    
    // Cek input simulasi
    if (input == "CITY CAR" || input == "K") {
      golongan = 'K';
      jenisMobil = "CITY CAR";
    } else if (input == "SUV" || input == "MPV" || input == "SEDAN" || input == "PICKUP" || input == "B") {
      golongan = 'B';
      if (input == "B") jenisMobil = "SUV"; 
    } else {
      // Abaikan jika input tidak sesuai dengan format simulasi
      return; 
    }
    
    Serial.print("\n[SIMULASI] Kendaraan masuk: ");
    Serial.println(jenisMobil);
    
    int alokasi = alokasiSlot(golongan);
    if (alokasi != -1) {
      slotState[alokasi] = 1; // 1 = TUNGGU MASUK
      savedCarType[alokasi] = jenisMobil; 
      digitalWrite(relayPins[alokasi], LOW); // Buka jalan (Flap Rata)
      simpanKeMemori();
      
      tampilkanPesanPrioritas("SILAHKAN KE SLOT " + String(alokasi + 1)); 
      tampilkanMonitoring();
      kirimStatusKeJoko(); // Update ke Joko
    } else {
      tampilkanPesanPrioritas("MAAF PARKIR PENUH");
    }
  }
}

void prosesDataSensor() {
  if (flagDataSensorBaru) {
    flagDataSensorBaru = false;
    bool adaPerubahan = false;

    for(int i = 0; i < 6; i++) {
      float jarak = sensorData.distances[i];

      // Jika sedang TUNGGU MASUK dan sensor mendeteksi mobil parkir (jarak <= 30cm)
      if (slotState[i] == 1 && jarak > 0 && jarak <= 30.0) {
        slotState[i] = 2; // 2 = TERISI
        digitalWrite(relayPins[i], HIGH); // Flap Naik (mengunci)
        simpanKeMemori(); 
        pesanPrioritas = ""; 
        adaPerubahan = true;
      }
      // Jika MAU KELUAR dan sensor mendeteksi mobil sudah pergi (jarak > 40cm)
      else if (slotState[i] == 3 && jarak > 40.0) {
        slotState[i] = 0; // 0 = KOSONG
        savedCarType[i] = "-"; 
        digitalWrite(relayPins[i], HIGH); // Flap Naik (reset ke default)
        simpanKeMemori();
        adaPerubahan = true;
      }
    }
    if (adaPerubahan) {
      tampilkanMonitoring();
      kirimStatusKeJoko(); // Update ke Joko jika ada mobil terparkir/pergi
    }
  }
}

// Memproses pesan yang diterima dari Joko
void prosesPesanJoko() {
  if (flagPesanJokoBaru) {
    flagPesanJokoBaru = false;
    
    String msg = String(msgFromJoko.text);
    msg.trim();
    Serial.println("[ESP-NOW] Pesan dari Joko: " + msg);
    
    // PEMBAYARAN BERHASIL: "PAID:1"
    if (msg.startsWith("PAID:")) {
      int slot = msg.substring(5).toInt(); // Ambil angka slot
      if (slot >= 1 && slot <= 6) {
        int idx = slot - 1;
        if (slotState[idx] == 2) {
          slotState[idx] = 3; // 3 = MAU KELUAR
          digitalWrite(relayPins[idx], LOW); // Flap Rata
          simpanKeMemori();
          tampilkanPesanPrioritas("TERIMA KASIH HATI-HATI");
          tampilkanMonitoring();
          kirimStatusKeJoko(); // Konfirmasi state baru ke Joko
        }
      }
    }
    // MEMBER MASUK: "MEMBER_IN:1"
    else if (msg.startsWith("MEMBER_IN:")) {
      int slot = msg.substring(10).toInt();
      if (slot >= 1 && slot <= 6) {
        int idx = slot - 1;
        if (slotState[idx] == 0) { // Pastikan slot kosong
          slotState[idx] = 1; // 1 = TUNGGU MASUK
          savedCarType[idx] = "MEMBER";
          digitalWrite(relayPins[idx], LOW); // Buka jalan
          simpanKeMemori();
          tampilkanPesanPrioritas("MEMBER SLOT " + String(slot));
          tampilkanMonitoring();
          kirimStatusKeJoko(); 
        }
      }
    }
    // MEMBER KELUAR: "MEMBER_OUT:1"
    else if (msg.startsWith("MEMBER_OUT:")) {
      int slot = msg.substring(11).toInt();
      if (slot >= 1 && slot <= 6) {
        int idx = slot - 1;
        if (slotState[idx] == 2) {
          slotState[idx] = 3; // 3 = MAU KELUAR
          digitalWrite(relayPins[idx], LOW); // Buka jalan keluar
          simpanKeMemori();
          tampilkanPesanPrioritas("SAMPAI JUMPA MEMBER");
          tampilkanMonitoring();
          kirimStatusKeJoko();
        }
      }
    }
    // SINKRONISASI SLOT RESERVASI: "RESERVED:1,0,0,0,0,0"
    else if (msg.startsWith("RESERVED:")) {
      String resData = msg.substring(9);
      int startIdx = 0;
      for (int i = 0; i < 6; i++) {
        int commaIdx = resData.indexOf(',', startIdx);
        String valStr = (commaIdx == -1) ? resData.substring(startIdx) : resData.substring(startIdx, commaIdx);
        valStr.trim();
        isReserved[i] = (valStr == "1");
        if (commaIdx == -1) break;
        startIdx = commaIdx + 1;
      }
    }
  }
}

void loop() {
  perbaruiTeksP10();
  handleMarquee();
  prosesDeteksiKendaraanSerial(); // Diganti jadi input Serial
  prosesDataSensor();
  prosesPesanJoko(); // Pengecekan pesan dari Joko

  // Membaca Keypad untuk inisiasi MINTA BAYAR
  char customKey = customKeypad.getKey();
  if (customKey) {
    int idx = customKey - '1'; 
    if (idx >= 0 && idx <= 5) {
      if (slotState[idx] == 2) { 
        kirimPayReqKeJoko(idx);
        tampilkanPesanPrioritas("SILAHKAN BAYAR SLOT " + String(idx + 1)); 
      } else {
         Serial.println("Slot tidak sedang parkir/terisi penuh!");
      }
    }
  }
}
