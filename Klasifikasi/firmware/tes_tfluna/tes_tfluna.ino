/**
 * ============================================================
 *  PROGRAM PENGECEKAN SENSOR TF-LUNA LIDAR
 *  Membaca dan menampilkan data Jarak dan Kekuatan Sinyal (Amp)
 *  dari 2 buah sensor TF-Luna sekaligus.
 * ============================================================
 */

#include <HardwareSerial.h>

// Konfigurasi Pin Sensor sesuai dengan proyek utama
HardwareSerial lidar1(2);  // Sensor 1 - RX:16, TX:17
HardwareSerial lidar2(1);  // Sensor 2 - RX:4,  TX:5

// Struktur untuk menyimpan state pembacaan masing-masing sensor
struct TFData {
  int id;
  uint8_t buffer[9];
  int index = 0;
  uint16_t distance = 0;
  uint16_t strength = 0;
  uint16_t temperature = 0;
};

TFData sensor1 = {1};
TFData sensor2 = {2};

void setup() {
  // Serial Monitor (baud rate 115200)
  Serial.begin(115200);
  
  // Inisialisasi Serial untuk LiDAR (baud rate bawaan TF-Luna adalah 115200)
  lidar1.begin(115200, SERIAL_8N1, 16, 17);
  lidar2.begin(115200, SERIAL_8N1, 4, 5);

  Serial.println("\n=== PENGECEKAN SENSOR TF-LUNA ===");
  Serial.println("Format Data: [Sensor ID] Jarak: <cm> | Sinyal: <amp>");
  Serial.println("Menunggu data...");
}

void loop() {
  bacaSensor(lidar1, sensor1);
  bacaSensor(lidar2, sensor2);
}

// Fungsi untuk membaca dan mem-parsing frame data TF-Luna
void bacaSensor(HardwareSerial &serialLidar, TFData &sensor) {
  while (serialLidar.available() > 0) {
    uint8_t b = serialLidar.read();

    // State machine untuk menangkap frame 9-byte
    // Byte 0 dan 1 harus 0x59
    if (sensor.index == 0) {
      if (b == 0x59) {
        sensor.buffer[sensor.index++] = b;
      }
    } 
    else if (sensor.index == 1) {
      if (b == 0x59) {
        sensor.buffer[sensor.index++] = b;
      } else {
        sensor.index = 0; // Header salah, reset
      }
    } 
    else {
      sensor.buffer[sensor.index++] = b;
    }

    // Jika 1 frame (9 byte) sudah lengkap
    if (sensor.index == 9) {
      sensor.index = 0;

      // Hitung checksum
      uint16_t checksum = 0;
      for (int i = 0; i < 8; i++) {
        checksum += sensor.buffer[i];
      }
      
      // Jika checksum valid
      if (sensor.buffer[8] == (uint8_t)(checksum & 0xFF)) {
        // Ekstrak data (Little Endian)
        sensor.distance = sensor.buffer[2] | (sensor.buffer[3] << 8);
        sensor.strength = sensor.buffer[4] | (sensor.buffer[5] << 8);
        sensor.temperature = (sensor.buffer[6] | (sensor.buffer[7] << 8)) / 8 - 256;

        // Tampilkan ke Serial Monitor
        Serial.print("[Sensor ");
        Serial.print(sensor.id);
        Serial.print("] Jarak: ");
        Serial.print(sensor.distance);
        Serial.print(" cm | Sinyal: ");
        Serial.print(sensor.strength);
        // Uncomment baris di bawah jika ingin melihat suhu chip LiDAR
        // Serial.print(" | Suhu: ");
        // Serial.print(sensor.temperature);
        // Serial.print(" C");
        Serial.println();
      }
    }
  }
}
