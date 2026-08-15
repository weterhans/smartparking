# Firmware — Edge AI Vehicle Classifier

Direktori ini berisi seluruh kode firmware ESP32 (Arduino `.ino`) untuk sistem klasifikasi kendaraan.

---

## 📂 Struktur Direktori

```
firmware/
├── vehicle_v3/                        ★ VERSI UTAMA
│   └── vehicle_v3.ino
├── vehicle_v2/                        Versi sebelumnya (legacy)
│   └── vehicle.ino
├── vehicle_tanpa_filter_panjang/      Varian eksperimental
│   └── vehicle_tanpa_filter_panjang.ino
└── tes_tfluna/                        Sketch pengujian sensor
    └── tes_tfluna.ino
```

---

## 📋 Perbandingan Versi

| Aspek | v2.0 (`vehicle.ino`) | v3.0 (`vehicle_v3.ino`) ★ |
|---|---|---|
| Filter sinyal | EMA (α=0.50) | REMA (α=0.50, λ=0.40) |
| Lag kompensasi | 14.000 µs | 5.000 µs |
| Lag residual | ~14 ms per transisi | ~5 ms per transisi |
| Kode lain | — | Identik dengan v2.0 |

### Kapan Menggunakan Masing-masing?

| Firmware | Gunakan Saat... |
|---|---|
| `vehicle_v3.ino` ★ | Penggunaan normal — akurasi & lag terbaik |
| `vehicle.ino` | Referensi / perbandingan dengan v3 |
| `vehicle_tanpa_filter_panjang.ino` | Analisis sensitivitas filter panjang |
| `tes_tfluna.ino` | Pengujian awal koneksi sensor TF-Luna |

---

## 🔧 Library yang Diperlukan

Pasang melalui Arduino IDE → Tools → Manage Libraries:

```
WebSockets           by Markus Sattler    ≥ 2.4.0
LiquidCrystal I2C    by Frank de Brabander
```

Library bawaan ESP32 Core (tidak perlu install manual):
- `HardwareSerial`, `WiFi`, `WebServer`
- `esp_now`, `esp_wifi`, `Wire`
- `math.h`

---

## ⚙️ Parameter Konfigurasi Utama

Semua parameter konfigurasi berada di bagian `PARAMETER LAPANGAN` pada baris 45–82 firmware:

```cpp
const float  TARGET_JARAK_KOSONG   = 250.0f;   // cm — tinggi portal kosong
const float  AMBANG_BATAS_MASUK    = 246.0f;   // cm — trigger masuk
const float  JARAK_ANTAR_SENSOR_CM = 53.f;     // cm — jarak fisik S1 ke S2

const float  REMA_ALPHA            = 0.50f;    // kecepatan respons filter
const float  REMA_LAMBDA           = 0.40f;    // kekuatan kompensasi lag

const char*  WIFI_SSID             = "FarizHP";
const char*  WIFI_PASS             = "12345678";

const uint8_t MAC_PENERIMA[6]      = {0xB0, 0xCB, 0xD8, 0xCE, 0xE9, 0x80};
```

> ⚠️ **Penting**: Sesuaikan `TARGET_JARAK_KOSONG` dan `JARAK_ANTAR_SENSOR_CM` dengan kondisi instalasi fisik Anda sebelum upload.

---

## 📡 Konfigurasi Hardware

| Komponen | Pin | Serial / Bus |
|---|---|---|
| TF-Luna S1 | RX: GPIO16, TX: GPIO17 | HardwareSerial(2) @ 115200 |
| TF-Luna S2 | RX: GPIO4, TX: GPIO5 | HardwareSerial(1) @ 115200 |
| LCD 20×4 | SDA: GPIO13, SCL: GPIO14 | Wire (I2C kustom) |

---

## 🚀 Langkah Upload

1. Buka file `.ino` yang diinginkan di Arduino IDE
2. Pilih board: **ESP32 Dev Module**
3. CPU Frequency: **240 MHz**
4. Flash Size: **4MB (32Mb)**
5. Upload Speed: **921600**
6. Pilih port COM yang sesuai
7. Klik **Upload** (Ctrl+U)

---

## 🐛 Troubleshooting

| Masalah | Kemungkinan Penyebab | Solusi |
|---|---|---|
| LCD blank/gelap | Alamat I2C salah | Ganti `0x27` → `0x3F` di baris `LiquidCrystal_I2C lcd(...)` |
| Sensor baca 0 terus | Kaca kendaraan | Normal — sistem menggunakan LKG (Last Known Good) |
| WebSocket tidak connect | Tidak tersambung ke WiFi ESP32 | Pastikan tersambung ke SSID yang benar |
| Kompilasi error IDF v5 | Versi board package | Pastikan ESP32 core versi 3.x terpasang |
| ESP-NOW gagal kirim | MAC address salah | Update `MAC_PENERIMA` sesuai ESP32 penerima Anda |
