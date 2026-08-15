/**
 * ============================================================
 *  EDGE AI VEHICLE CLASSIFIER — v3.0
 *  Perubahan dari v2.0:
 *   1. Filter EMA diganti dengan REMA (Regularized Exponential Moving Average)
 *      → Kompensasi lag otomatis tanpa mengorbankan kehalusan sinyal
 *      → Parameter baru: REMA_ALPHA (kecepatan respons) dan REMA_LAMBDA (kekuatan regularisasi)
 *   2. Tambah field `jarakRemaState` pada struct LidarData untuk menyimpan state REMA
 *   3. EMA_LAG_KOMPENSASI_US diturunkan dari 14000µs → 5000µs
 *      (REMA memiliki lag residual yang jauh lebih kecil dari EMA)
 *
 *  Kode lainnya IDENTIK dengan v2.0 (vehicle.ino).
 * ============================================================
 */

#include <HardwareSerial.h>
#include <math.h>
#include <WiFi.h>
#include <WebServer.h>
#include <WebSocketsServer.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

// LCD I2C 20x4 — alamat default 0x27 (ganti ke 0x3F jika layar blank)
// Ukuran: 20 kolom, 4 baris
// Pin I2C kustom (menghindari konflik dengan LiDAR di pin 4,5,16,17)
#define LCD_SDA 13
#define LCD_SCL 14
LiquidCrystal_I2C lcd(0x27, 20, 4);
void tampilLCD(const String& kelas, float panjang, float tinggi, float siluet,
               float posMax, float slope, float compact, float rear, float flatRoof,
               float vMasuk, float vKeluar);


// ─────────────────────────────────────────────
//  KONFIGURASI HARDWARE
// ─────────────────────────────────────────────
HardwareSerial lidar1(2);  // RX:16, TX:17
HardwareSerial lidar2(1);  // RX:4,  TX:5

// ─────────────────────────────────────────────
//  PARAMETER LAPANGAN
// ─────────────────────────────────────────────
const float  TARGET_JARAK_KOSONG   = 250.0f;   // cm — tinggi portal kosong (tinggi sensor dari tanah)
const float  AMBANG_BATAS_MASUK    = 246.0f;   // cm — trigger masuk (>4cm dari tanah)
const float  HISTERESIS_KELUAR     = 2.0f;     // cm — trigger keluar di 248 cm (masih di bawah 250 cm)
const float  JARAK_ANTAR_SENSOR_CM = 53.f;    // cm — jarak fisik S1 ke S2

// ── REMA FILTER (menggantikan EMA) ──
// REMA: jarakMulus[n] = jarakRemaState[n] + lambda*(jarakRemaState[n] - jarakRemaState[n-1])
// di mana jarakRemaState[n] = alpha*rawDist + (1-alpha)*jarakRemaState[n-1]
//
// REMA_ALPHA : kecepatan respons filter (setara ALPHA_FILTER di EMA).
//              Semakin besar → semakin responsif, semakin kecil → semakin halus.
// REMA_LAMBDA: kekuatan kompensasi lag (0.0 = sama dengan EMA, 0.5 = kompensasi sedang).
//              Semakin besar → lag semakin kecil, tapi terlalu besar bisa overshoot.
const float  REMA_ALPHA            = 0.50f;    // REMA filter — kecepatan respons
const float  REMA_LAMBDA           = 0.40f;    // REMA filter — kekuatan regularisasi lag

// Kompensasi lag REMA di kedua ujung deteksi (masuk & keluar)
// Pada α=0.5, λ=0.4, dan 100Hz, lag residual REMA ≈ 0.5 sample per transisi ≈ 5 ms per ujung
// (lebih kecil dari EMA yang lag-nya ≈ 14 ms per ujung)
const float  EMA_LAG_KOMPENSASI_US = 5000.0f; // µs per ujung (diturunkan dari 14000 karena REMA)

const int    JEDA_SIMPAN_MS        = 10;       // ms — max 100 sampel/detik (resolusi spasial 2x lipat lebih padat)
const int    MAKS_BUFFER           = 1000;     // batas hard buffer siluet
const unsigned long TIMEOUT_MACET_MS = 30000UL; // ms — reset jika macet

// ── MITIGASI KACA ──
// TF-Luna mengembalikan 0 (atau sangat kecil) saat laser mengenai kaca.
// Nilai di bawah JARAK_MIN_VALID dianggap bacaan kaca → gunakan LKG (last-known-good).
const float  JARAK_MIN_VALID       = 5.0f;    // cm — di bawah ini dianggap bacaan kaca/invalid
// Durasi maks sensor S2 mempertahankan paksa-trigger saat kendaraan terdeteksi S1 (ms)
const unsigned long FORCE_TRIGGER_S2_MS = 5000UL;

// Batas sanity kecepatan (cm/s): ~5 km/h s.d. ~120 km/h
const float  V_MIN_CMS = 139.0f;
const float  V_MAX_CMS = 3334.0f;

// ─────────────────────────────────────────────
//  STRUKTUR DATA
// ─────────────────────────────────────────────
struct LidarData {
  uint8_t       tfData[9];
  int           dataIndex        = 0;
  float         jarakMentah      = TARGET_JARAK_KOSONG;
  float         jarakMulus       = TARGET_JARAK_KOSONG;
  float         jarakRemaState   = TARGET_JARAK_KOSONG; // [REMA v3] State internal REMA (EMA murni sebelum regularisasi)
  float         jarakLKG         = TARGET_JARAK_KOSONG; // Last-Known-Good sebelum kena kaca
  unsigned long waktuSkrg        = 0;
  bool          terdeteksi       = false;
  bool          bacaanKacaAktif  = false;  // true saat pembacaan sedang invalid (kaca)
  int           jumlahKaca       = 0;      // hitung sampel invalid berturut-turut
  unsigned long waktuTriggerMasuk  = 0;
  unsigned long waktuTriggerKeluar = 0;
  int           keluar_debounce    = 0;      // anti-flicker exit
  int           idSensor;
  float         offsetKalibrasi  = 0.0f;
};

/**
 * SampelSiluet — menyimpan tinggi DAN timestamp per sampel.
 * Timestamp diperlukan agar posisi spasial bisa direkonstruksi
 * secara akurat meski kendaraan bergerak tidak konstan.
 */
struct SampelSiluet {
  float         tinggi_cm;
  unsigned long waktu_us;   // dari micros() saat sampel diambil
};

// ─────────────────────────────────────────────
//  STATE GLOBAL
// ─────────────────────────────────────────────
LidarData    s1 = { .idSensor = 1 };
LidarData    s2 = { .idSensor = 2 };

SampelSiluet bufferSiluet[MAKS_BUFFER];
int          jumlahSiluet         = 0;

bool         kendaraanLewat       = false;
bool         arahSalah            = false;
unsigned long waktuKosong         = 0;
unsigned long waktuSimpanTerakhir = 0;

// ★ FIX: Simpan waktu masuk PERTAMA kali (tidak di-reset saat mid-crossing)
// Ini kunci agar t_durasi_s1 dan t_masuk_s = waktu penuh kendaraan melintas
unsigned long waktuMasukS1_pertama = 0;
unsigned long waktuMasukS2_pertama = 0;

// ─────────────────────────────────────────────
//  DATASET KNN (50 referensi, 8 fitur, 5 kelas)
// ─────────────────────────────────────────────
struct DataReferensi {
  float fitur[8];   // [Panjang(m), Tinggi(m), StdDev, PosMax, Slope°, Compactness, RearComp, FlatRoof]
  int   label;      // 0:CityCar 1:Sedan 2:MPV 3:SUV 4:Pickup
};

const String NAMA_KELAS[5]  = {"CityCar", "Sedan", "MPV", "SUV", "Pickup"};
const int    JUMLAH_DATA    = 75;
const int    NILAI_K        = 3;
const int    JUMLAH_FITUR   = 8;

// Min-Max global untuk normalisasi (8 fitur)
const float FITUR_MIN[8] = {3.20f, 1.28f, 0.251f, 0.23f, 14.6f, 0.51f, 0.39f, 0.14f};
const float FITUR_MAX[8] = {5.46f, 2.05f, 0.460f, 1.03f, 58.0f, 0.96f, 1.00f, 0.79f};

// BOBOT_FITUR untuk Feature-Weighted KNN
// Fitur: [Panjang, Tinggi, StdDev, PosMax, Slope, Compactness, RearComp, FlatRoof]
const float BOBOT_FITUR[8] = {
  0.5f,  // 0: Panjang     (Sering overlap SUV/MPV, prioritas diturunkan)
  2.0f,  // 1: Tinggi      (Pembeda utama _ground clearance_, prioritas tertinggi)
  1.0f,  // 2: StdDev      (Standar)
  1.0f,  // 3: PosMax      (Standar)
  1.5f,  // 4: Slope       (Pembeda bentuk kap tegak/landai, prioritas tinggi)
  1.2f,  // 5: Compactness (Pembeda bodi _boxy_ vs melengkung, ditingkatkan)
  1.0f,  // 6: RearComp    (Standar)
  1.0f   // 7: FlatRoof    (Standar)
};

const DataReferensi dataset[JUMLAH_DATA] = {
  // CityCar (0) — DATA REAL (H=1.48-1.49m, L=3.29-3.64m)
  // 5 pengukuran real + 5 variasi sintetis di sekitar target L=3.5m H=1.48m
  {{3.52f, 1.49f, 0.378f, 0.586f, 29.0f, 0.752f, 0.897f, 0.510f}, 0},  // real #1 — terbaik (dL=0.02, dH=0.01)
  {{3.57f, 1.49f, 0.378f, 0.576f, 29.0f, 0.768f, 0.892f, 0.520f}, 0},  // real #2 — (dL=0.07, dH=0.01)
  {{3.33f, 1.48f, 0.364f, 0.657f, 25.1f, 0.785f, 0.884f, 0.490f}, 0},  // real #3 — (dL=0.17, dH=0.00)
  {{3.29f, 1.49f, 0.397f, 0.566f, 32.9f, 0.747f, 0.864f, 0.490f}, 0},  // real #4 — (dL=0.21, dH=0.01)
  {{3.64f, 1.48f, 0.385f, 0.657f, 25.5f, 0.772f, 0.884f, 0.520f}, 0},  // real #5 — (dL=0.14, dH=0.00)
  {{3.50f, 1.48f, 0.375f, 0.590f, 28.5f, 0.755f, 0.895f, 0.505f}, 0},  // synth #1 — anchor real#1
  {{3.55f, 1.48f, 0.380f, 0.580f, 29.5f, 0.762f, 0.890f, 0.515f}, 0},  // synth #2 — anchor real#2
  {{3.38f, 1.48f, 0.368f, 0.650f, 25.8f, 0.778f, 0.880f, 0.492f}, 0},  // synth #3 — anchor real#3
  {{3.45f, 1.49f, 0.382f, 0.600f, 30.0f, 0.760f, 0.875f, 0.500f}, 0},  // synth #4 — anchor real#4
  {{3.60f, 1.48f, 0.380f, 0.645f, 26.0f, 0.770f, 0.882f, 0.510f}, 0},  // synth #5 — anchor real#5
  {{3.48f, 1.49f, 0.372f, 0.595f, 27.8f, 0.758f, 0.893f, 0.508f}, 0},  // synth #6 — anchor real#1 varian
  {{3.54f, 1.48f, 0.376f, 0.610f, 28.0f, 0.756f, 0.888f, 0.512f}, 0},  // synth #7 — anchor real#2 varian
  {{3.35f, 1.48f, 0.367f, 0.640f, 26.2f, 0.782f, 0.878f, 0.494f}, 0},  // synth #8 — anchor real#3 varian
  {{3.31f, 1.49f, 0.392f, 0.572f, 31.5f, 0.750f, 0.866f, 0.491f}, 0},  // synth #9 — anchor real#4 varian
  {{3.62f, 1.48f, 0.383f, 0.648f, 25.8f, 0.774f, 0.881f, 0.518f}, 0},  // synth #10 — anchor real#5 varian
  // Sedan (1) — panjang, slope landai, RearComp menengah (bagasi), FlatRoof rendah
  {{4.40f, 1.45f, 0.285f, 0.50f, 16.0f, 0.75f, 0.80f, 0.39f}, 1},  // real #1 — manual (L=4.40m, H=1.45m, slope=16°)
  {{4.42f, 1.45f, 0.286f, 0.50f, 16.2f, 0.75f, 0.80f, 0.39f}, 1},  // synth — anchor real#1
  {{4.38f, 1.45f, 0.284f, 0.51f, 15.8f, 0.75f, 0.80f, 0.38f}, 1},  // synth — anchor real#1
  {{4.64f, 1.46f, 0.292f, 0.51f, 22.1f, 0.75f, 0.80f, 0.39f}, 1},
  {{4.47f, 1.47f, 0.300f, 0.36f, 31.1f, 0.75f, 0.80f, 0.38f}, 1},
  {{4.73f, 1.46f, 0.295f, 0.43f, 25.3f, 0.75f, 0.80f, 0.39f}, 1},
  {{4.63f, 1.49f, 0.306f, 0.36f, 30.6f, 0.75f, 0.80f, 0.39f}, 1},
  {{4.45f, 1.48f, 0.306f, 0.53f, 22.6f, 0.75f, 0.80f, 0.38f}, 1},
  {{4.74f, 1.47f, 0.301f, 0.62f, 18.3f, 0.75f, 0.80f, 0.39f}, 1},
  {{4.52f, 1.50f, 0.312f, 0.44f, 26.6f, 0.75f, 0.80f, 0.39f}, 1},
  {{4.36f, 1.45f, 0.283f, 0.49f, 16.5f, 0.74f, 0.79f, 0.38f}, 1},  // synth #11 — anchor real#1 varian
  {{4.44f, 1.46f, 0.287f, 0.51f, 15.5f, 0.75f, 0.80f, 0.39f}, 1},  // synth #12 — anchor real#1 varian
  {{4.66f, 1.46f, 0.293f, 0.50f, 22.5f, 0.75f, 0.80f, 0.39f}, 1},  // synth #13 — anchor synth varian
  {{4.49f, 1.47f, 0.299f, 0.38f, 30.5f, 0.75f, 0.80f, 0.38f}, 1},  // synth #14 — anchor synth varian
  {{4.75f, 1.46f, 0.296f, 0.44f, 24.8f, 0.75f, 0.80f, 0.39f}, 1},  // synth #15 — anchor synth varian
  // MPV (2) — DATA REAL (H=1.64-1.65m, L=3.45-4.06m) | target: L=3.8m H=1.6m
  // 5 pengukuran real + 5 variasi sintetis (CC?-A4 relabel: H=1.65m = MPV territory)
  {{3.83f, 1.64f, 0.373f, 0.697f, 20.3f, 0.788f, 0.864f, 0.490f}, 2},  // real #1 — TERBAIK (dL=0.03, dH=0.04)
  {{3.56f, 1.64f, 0.380f, 0.737f, 20.1f, 0.771f, 0.863f, 0.480f}, 2},  // real #2 — (dL=0.24, dH=0.04)
  {{4.06f, 1.64f, 0.393f, 0.707f, 20.1f, 0.791f, 0.859f, 0.530f}, 2},  // real #3 — (dL=0.26, dH=0.04)
  {{3.55f, 1.65f, 0.387f, 0.697f, 22.2f, 0.788f, 0.850f, 0.490f}, 2},  // real #4 — relabel dari CityCar (H=1.65m)
  {{3.45f, 1.65f, 0.349f, 0.707f, 21.3f, 0.791f, 0.885f, 0.500f}, 2},  // real #5 — (dL=0.35, dH=0.05)
  {{3.86f, 1.63f, 0.376f, 0.700f, 20.5f, 0.789f, 0.867f, 0.493f}, 2},  // synth #1 — anchor real#1
  {{3.62f, 1.63f, 0.380f, 0.730f, 20.2f, 0.773f, 0.861f, 0.482f}, 2},  // synth #2 — anchor real#2
  {{4.02f, 1.63f, 0.390f, 0.705f, 20.3f, 0.790f, 0.857f, 0.525f}, 2},  // synth #3 — anchor real#3
  {{3.60f, 1.64f, 0.383f, 0.700f, 22.0f, 0.787f, 0.853f, 0.492f}, 2},  // synth #4 — anchor real#4
  {{3.48f, 1.64f, 0.352f, 0.710f, 21.5f, 0.790f, 0.882f, 0.498f}, 2},  // synth #5 — anchor real#5
  {{4.11f, 1.62f, 0.385f, 0.485f, 25.9f, 0.789f, 0.877f, 0.550f}, 2},  // real tambahan
  {{4.03f, 1.60f, 0.374f, 0.434f, 27.4f, 0.799f, 0.913f, 0.580f}, 2},  // real tambahan
  {{3.84f, 1.64f, 0.374f, 0.695f, 20.8f, 0.787f, 0.865f, 0.491f}, 2},  // synth #6 — anchor real#1 varian
  {{3.58f, 1.63f, 0.378f, 0.720f, 20.5f, 0.774f, 0.860f, 0.483f}, 2},  // synth #7 — anchor real#2 varian
  {{4.08f, 1.63f, 0.391f, 0.700f, 20.6f, 0.790f, 0.858f, 0.528f}, 2},  // synth #8 — anchor real#3 varian
  // SUV (3) — target L=4.0m, H=1.7m
  // Menggunakan data log terbaru yang sangat akurat sebagai REAL data
  {{3.86f, 1.69f, 0.384f, 0.596f, 24.9f, 0.808f, 0.890f, 0.550f}, 3},  // real #1 — log terbaru (akurat)
  {{3.92f, 1.66f, 0.364f, 0.677f, 20.8f, 0.819f, 0.891f, 0.570f}, 3},  // real #2 — log sebelumnya
  {{4.04f, 1.65f, 0.355f, 0.649f, 21.7f, 0.826f, 0.907f, 0.529f}, 3},  // synth #1 — var 4.0m / 1.7m
  {{3.98f, 1.65f, 0.353f, 0.678f, 18.9f, 0.807f, 0.897f, 0.574f}, 3},  // synth #2
  {{3.92f, 1.71f, 0.376f, 0.628f, 22.0f, 0.827f, 0.885f, 0.536f}, 3},  // synth #3
  {{4.14f, 1.68f, 0.348f, 0.637f, 22.2f, 0.823f, 0.903f, 0.593f}, 3},  // synth #4
  {{4.01f, 1.75f, 0.359f, 0.682f, 22.1f, 0.824f, 0.905f, 0.578f}, 3},  // synth #5
  {{4.06f, 1.65f, 0.353f, 0.656f, 19.1f, 0.808f, 0.875f, 0.548f}, 3},  // synth #6
  {{4.10f, 1.73f, 0.353f, 0.630f, 20.1f, 0.810f, 0.879f, 0.614f}, 3},  // synth #7
  {{4.11f, 1.68f, 0.370f, 0.667f, 22.5f, 0.817f, 0.882f, 0.545f}, 3},
  {{4.27f, 1.78f, 0.381f, 0.909f, 15.1f, 0.813f, 0.897f, 0.520f}, 3},  // real tambahan
  {{4.34f, 1.79f, 0.456f, 0.414f, 36.4f, 0.787f, 0.891f, 0.530f}, 3},  // real tambahan
  {{3.88f, 1.70f, 0.382f, 0.600f, 24.5f, 0.810f, 0.888f, 0.552f}, 3},  // synth #8 — anchor real#1 varian
  {{3.94f, 1.67f, 0.366f, 0.672f, 21.2f, 0.820f, 0.889f, 0.568f}, 3},  // synth #9 — anchor real#2 varian
  {{4.16f, 1.69f, 0.350f, 0.640f, 21.5f, 0.825f, 0.902f, 0.590f}, 3},  // synth #10 — anchor synth#4 varian
  // Pickup (4) — panjang, RearComp RENDAH (bak terbuka), FlatRoof RENDAH
  {{3.50f, 1.75f, 0.362f, 0.38f, 34.0f, 0.58f, 0.44f, 0.17f}, 4},  // real #1 — manual (L=3.50m, H=1.75m, slope=34°)
  {{4.10f, 1.83f, 0.370f, 0.35f, 58.0f, 0.57f, 0.43f, 0.16f}, 4},  // real #2 — manual (L=4.10m, H=1.83m, slope=58°)
  {{5.17f, 1.80f, 0.362f, 0.37f, 34.3f, 0.58f, 0.44f, 0.17f}, 4},
  {{5.00f, 1.80f, 0.363f, 0.38f, 34.4f, 0.58f, 0.44f, 0.17f}, 4},
  {{5.13f, 1.85f, 0.377f, 0.35f, 36.9f, 0.57f, 0.43f, 0.17f}, 4},
  {{5.09f, 1.77f, 0.351f, 0.30f, 39.8f, 0.59f, 0.45f, 0.17f}, 4},
  {{5.04f, 1.84f, 0.378f, 0.41f, 33.0f, 0.57f, 0.43f, 0.17f}, 4},
  {{5.10f, 1.85f, 0.378f, 0.30f, 41.5f, 0.57f, 0.43f, 0.16f}, 4},
  {{5.26f, 1.84f, 0.374f, 0.42f, 31.2f, 0.57f, 0.43f, 0.16f}, 4},
  {{5.02f, 1.84f, 0.374f, 0.31f, 40.7f, 0.57f, 0.44f, 0.16f}, 4},
  {{5.06f, 1.82f, 0.370f, 0.44f, 30.7f, 0.58f, 0.44f, 0.17f}, 4},
  {{5.06f, 1.78f, 0.352f, 0.43f, 30.4f, 0.59f, 0.45f, 0.17f}, 4},
  {{3.52f, 1.75f, 0.363f, 0.39f, 33.8f, 0.58f, 0.44f, 0.17f}, 4},  // synth #11 — anchor real#1 varian
  {{4.12f, 1.83f, 0.371f, 0.34f, 57.5f, 0.57f, 0.43f, 0.16f}, 4},  // synth #12 — anchor real#2 varian
  {{5.19f, 1.80f, 0.363f, 0.37f, 34.5f, 0.58f, 0.44f, 0.17f}, 4},  // synth #13 — anchor synth varian
};

// ─────────────────────────────────────────────
//  KONFIGURASI WIFI (Web Serial Monitor)
// ─────────────────────────────────────────────
// ESP32 akan membuat hotspot sendiri.
// Sambungkan HP ke WiFi ini, lalu buka http://192.168.4.1
const char* WIFI_SSID = "FarizHP";  // ← nama hotspot
const char* WIFI_PASS = "12345678";           // ← password (min 8 karakter)

WebServer    webServer(80);
WebSocketsServer webSocket(81);

// ─────────────────────────────────────────────
//  KONFIGURASI ESP-NOW
// ─────────────────────────────────────────────
// MAC address ESP32 penerima
const uint8_t MAC_PENERIMA[6] = {0xB0, 0xCB, 0xD8, 0xCE, 0xE9, 0x80};

// Struktur data yang dikirim via ESP-NOW
// HARUS IDENTIK dengan struct_message di ESP1sketch_jun26a.ino (penerima)
typedef struct struct_message {
  char vehicleType[20]; // Cocok dengan penerima: "CITY CAR", "SEDAN", "MPV", "SUV", "PICKUP"
} struct_message;

// Callback status pengiriman ESP-NOW
// CATATAN: Di ESP32 Arduino Core 3.x (IDF v5.x), parameter pertama berubah
// dari (const uint8_t* mac) menjadi (const wifi_tx_info_t* info)
void onDataSent(const wifi_tx_info_t* info, esp_now_send_status_t status) {
  if (status == ESP_NOW_SEND_SUCCESS) {
    wlog("[ESP-NOW] Terkirim ke penerima\n");
  } else {
    wlog("[ESP-NOW][ERR] Gagal kirim ke penerima\n");
  }
}

// Kirim nama kelas hasil klasifikasi via ESP-NOW
// Mengkonversi format nama kelas ke uppercase + spasi sesuai ekspektasi penerima
void kirimESPNow(const String& namaKelas) {
  struct_message pesan;

  // Mapping format pengirim → format penerima (harus IDENTIK dengan kondisi di prosesDeteksiKendaraan)
  String namaUpper = namaKelas;
  namaUpper.toUpperCase();

  // "CityCar" → "CITY CAR" (penerima mengecek "CITY CAR" setelah toUpperCase)
  if (namaUpper == "CITYCAR")  namaUpper = "CITY CAR";
  // Nama lain sudah cocok setelah toUpperCase: SEDAN, MPV, SUV, PICKUP

  namaUpper.toCharArray(pesan.vehicleType, sizeof(pesan.vehicleType));
  esp_now_send(MAC_PENERIMA, (uint8_t*)&pesan, sizeof(pesan));
}

// Buffer log untuk client yang baru connect
#define LOG_HISTORY_SIZE 50
String logHistory[LOG_HISTORY_SIZE];
int    logHead = 0;
int    logCount = 0;

// Kirim string ke WebSocket DAN Serial fisik secara bersamaan
void wlog(String s) {
  Serial.print(s);
  webSocket.broadcastTXT(s);
  logHistory[logHead] = s;
  logHead = (logHead + 1) % LOG_HISTORY_SIZE;
  if (logCount < LOG_HISTORY_SIZE) logCount++;
}

/**
 * yieldDelay() — pengganti delay() yang NON-BLOCKING.
 * Tetap memproses WebServer & WebSocket selama menunggu,
 * sehingga koneksi web monitor tidak terputus saat LCD sedang tampil.
 */
void yieldDelay(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
    webServer.handleClient();
    webSocket.loop();
  }
}

// Halaman HTML untuk Web Serial Monitor
const char WEB_PAGE[] PROGMEM = R"rawhtml(
<!DOCTYPE html><html lang='id'><head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Edge AI Vehicle Classifier</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#060b18;color:#e2e8f0;font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh;overflow-x:hidden}
header{background:linear-gradient(135deg,#0f172a,#1e1b4b);border-bottom:1px solid rgba(99,102,241,.3);padding:12px 20px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}
.logo{display:flex;align-items:center;gap:10px}
.logo-icon{width:36px;height:36px;background:linear-gradient(135deg,#6366f1,#8b5cf6);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px;box-shadow:0 0 20px rgba(99,102,241,.4)}
.logo-text h1{font-size:.95rem;font-weight:700;color:#e0e7ff;letter-spacing:.5px}
.logo-text p{font-size:.7rem;color:#818cf8;margin-top:1px}
.status-pill{display:flex;align-items:center;gap:8px;background:rgba(15,23,42,.8);border:1px solid #1e293b;border-radius:20px;padding:6px 14px;font-size:.75rem}
.dot{width:8px;height:8px;border-radius:50%;background:#475569;flex-shrink:0;transition:background .3s}
.dot.alive{background:#22c55e;box-shadow:0 0 8px #22c55e;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
#stat-txt{color:#94a3b8;transition:color .3s}
main{display:grid;grid-template-columns:1fr 320px;gap:16px;padding:16px;height:calc(100vh - 62px)}
@media(max-width:700px){main{grid-template-columns:1fr;height:auto}}
.log-panel{background:rgba(15,23,42,.6);border:1px solid rgba(99,102,241,.15);border-radius:16px;display:flex;flex-direction:column;overflow:hidden}
.panel-hdr{display:flex;align-items:center;justify-content:space-between;padding:10px 16px;border-bottom:1px solid rgba(99,102,241,.1);background:rgba(99,102,241,.05)}
.panel-hdr span{font-size:.78rem;font-weight:600;color:#a5b4fc;letter-spacing:.5px;text-transform:uppercase}
.btn-clear{font-size:.72rem;padding:4px 12px;border:1px solid rgba(239,68,68,.3);border-radius:8px;background:rgba(239,68,68,.08);color:#fca5a5;cursor:pointer;transition:all .2s}
.btn-clear:hover{background:rgba(239,68,68,.2);border-color:#f87171;color:#fff}
#log{flex:1;padding:14px 16px;overflow-y:auto;font-family:'Courier New',monospace;font-size:12px;line-height:1.8;scroll-behavior:smooth}
#log::-webkit-scrollbar{width:4px}
#log::-webkit-scrollbar-thumb{background:#334155;border-radius:2px}
.l-head{color:#818cf8;font-weight:700}
.l-cal{color:#38bdf8}
.l-ok{color:#4ade80}
.l-warn{color:#fbbf24}
.l-err{color:#f87171}
.l-data{color:#475569;font-size:11px}
.l-def{color:#94a3b8}
.side{display:flex;flex-direction:column;gap:12px;overflow-y:auto}
.result-card{background:linear-gradient(135deg,rgba(99,102,241,.15),rgba(139,92,246,.1));border:1px solid rgba(99,102,241,.3);border-radius:16px;padding:20px;text-align:center}
.result-label{font-size:.7rem;color:#818cf8;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}
.result-icon{font-size:2.8rem;margin:6px 0}
.result-name{font-size:1.5rem;font-weight:800;color:#a5b4fc;min-height:2rem}
.result-badge{display:inline-block;margin-top:8px;padding:3px 12px;border-radius:20px;font-size:.72rem;background:rgba(99,102,241,.2);color:#a5b4fc;border:1px solid rgba(99,102,241,.3)}
.card{background:rgba(15,23,42,.6);border:1px solid rgba(99,102,241,.12);border-radius:16px;padding:14px}
.card-title{font-size:.74rem;color:#818cf8;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px;font-weight:600}
.stats-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.stat{background:rgba(99,102,241,.06);border:1px solid rgba(99,102,241,.1);border-radius:10px;padding:9px 12px}
.stat-lbl{font-size:.65rem;color:#64748b;text-transform:uppercase}
.stat-val{font-size:1rem;font-weight:700;color:#e2e8f0;margin-top:3px}
.stat-val.hi{color:#a5b4fc}
canvas#cv{width:100%;height:90px;display:block;border-radius:8px;background:rgba(99,102,241,.04)}
.sensor-row{display:flex;gap:8px;margin-top:8px}
.sb{flex:1;background:rgba(99,102,241,.06);border:1px solid rgba(99,102,241,.1);border-radius:10px;padding:7px 10px;text-align:center}
.sb .sl{font-size:.63rem;color:#64748b;display:block}
.sb .sv{font-size:.82rem;font-weight:600;color:#a5b4fc;margin-top:2px}
</style></head>
<body>
<header>
  <div class='logo'>
    <div class='logo-icon'>&#128300;</div>
    <div class='logo-text'><h1>Edge AI Vehicle Classifier</h1><p>Web Serial Monitor &middot; ESP32 TF-Luna</p></div>
  </div>
  <div class='status-pill'><div class='dot' id='dot'></div><span id='stat-txt'>Menghubungkan...</span></div>
</header>
<main>
  <div class='log-panel'>
    <div class='panel-hdr'><span>&#128225; Serial Log</span><button class='btn-clear' onclick='document.getElementById("log").innerHTML=""'>&#128465; Hapus</button></div>
    <div id='log'></div>
  </div>
  <div class='side'>
    <div class='result-card'>
      <div class='result-label'>Hasil Klasifikasi KNN</div>
      <div class='result-icon' id='r-icon'>&#9203;</div>
      <div class='result-name' id='r-name'>Menunggu...</div>
      <div class='result-badge' id='r-badge'>Belum ada kendaraan</div>
    </div>
    <div class='card'>
      <div class='card-title'>&#128202; Data Terakhir</div>
      <div class='stats-grid'>
        <div class='stat'><div class='stat-lbl'>Panjang</div><div class='stat-val hi' id='sp'>&#8212;</div></div>
        <div class='stat'><div class='stat-lbl'>Tinggi</div><div class='stat-val hi' id='st'>&#8212;</div></div>
        <div class='stat'><div class='stat-lbl'>V Masuk</div><div class='stat-val' id='sm'>&#8212;</div></div>
        <div class='stat'><div class='stat-lbl'>V Keluar</div><div class='stat-val' id='sk'>&#8212;</div></div>
        <div class='stat'><div class='stat-lbl'>Slope</div><div class='stat-val' id='ss'>&#8212;</div></div>
        <div class='stat'><div class='stat-lbl'>Sampel Valid</div><div class='stat-val' id='sv'>&#8212;</div></div>
        <div class='stat'><div class='stat-lbl'>StdDev</div><div class='stat-val' id='ssd'>&#8212;</div></div>
        <div class='stat'><div class='stat-lbl'>PosMax</div><div class='stat-val' id='spm'>&#8212;</div></div>
        <div class='stat'><div class='stat-lbl'>Compactness</div><div class='stat-val' id='scp'>&#8212;</div></div>
        <div class='stat'><div class='stat-lbl'>RearComp</div><div class='stat-val' id='src'>&#8212;</div></div>
        <div class='stat'><div class='stat-lbl'>FlatRoof</div><div class='stat-val' id='sfr'>&#8212;</div></div>
      </div>
    </div>
    <div class='card'>
      <div class='card-title'>&#128200; Siluet 100-Bin</div>
      <canvas id='cv' width='280' height='90'></canvas>
      <div class='sensor-row'>
        <div class='sb'><span class='sl'>S1 Offset</span><span class='sv' id='so1'>&#8212;</span></div>
        <div class='sb'><span class='sl'>S2 Offset</span><span class='sv' id='so2'>&#8212;</span></div>
      </div>
    </div>
  </div>
</main>
<script>
const logEl=document.getElementById('log');
const dot=document.getElementById('dot');
const stxt=document.getElementById('stat-txt');
const IC={'CityCar':'&#128663;','Sedan':'&#128665;','MPV':'&#128652;','SUV':'&#128667;','Pickup':'&#128666;'};
let ws,bins=[];
const MAX_LOG=300; // Opsi 4: batas maksimal baris di log
let logCount=0;
function cl(s){
  const e=s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  if(s.includes('==='))return'<span class="l-head">'+e+'</span>';
  if(s.includes('Prediksi')||s.includes('Kecepatan')||s.includes('Panjang')||s.includes('Tinggi')||s.includes('Fitur')||s.includes('Sampel'))return'<span class="l-ok">'+e+'</span>';
  if(s.includes('[CAL]')||s.includes('[SYS]')||s.includes('[WiFi]'))return'<span class="l-cal">'+e+'</span>';
  if(s.includes('[WARN]')||s.includes('[INF]')||s.includes('[INFO]'))return'<span class="l-warn">'+e+'</span>';
  if(s.includes('[ERR]'))return'<span class="l-err">'+e+'</span>';
  return'<span class="l-def">'+e+'</span>';
}
// Opsi 3: insertAdjacentHTML — jauh lebih ringan dari innerHTML +=
// Opsi 4: hapus baris paling atas jika melebihi MAX_LOG
function ap(t){
  logEl.insertAdjacentHTML('beforeend',cl(t));
  logCount++;
  if(logCount>MAX_LOG){
    const first=logEl.firstElementChild;
    if(first){logEl.removeChild(first);logCount--;}
  }
  logEl.scrollTop=logEl.scrollHeight;
}
function parse(t){
  let m;
  if(m=t.match(/S1 offset = ([\-\d.]+)/))document.getElementById('so1').innerHTML=m[1]+' cm';
  if(m=t.match(/S2 offset = ([\-\d.]+)/))document.getElementById('so2').innerHTML=m[1]+' cm';
  if(m=t.match(/Masuk=([\d.]+) km\/h \| Keluar=([\d.]+)/)){document.getElementById('sm').innerHTML=m[1]+' km/h';document.getElementById('sk').innerHTML=m[2]+' km/h';}
  if(m=t.match(/Panjang\s+: ([\d.]+) m/))document.getElementById('sp').innerHTML=m[1]+' m';
  if(m=t.match(/Tinggi Maks: ([\d.]+) m/))document.getElementById('st').innerHTML=m[1]+' m';
  if(m=t.match(/Sampel\s+: (\d+) titik/))document.getElementById('sv').innerHTML=m[1];
  // Parse fitur secara posisional — [Panjang, Tinggi, StdDev, PosMax, Slope°, Compactness, RearComp, FlatRoof]
  if(m=t.match(/Fitur\s+: \[[\d.]+, [\d.]+, ([\d.]+),/))document.getElementById('ssd').innerHTML=m[1];
  if(m=t.match(/Fitur\s+: \[[\d.]+, [\d.]+, [\d.]+, ([\d.]+),/))document.getElementById('spm').innerHTML=m[1];
  if(m=t.match(/Fitur\s+: \[[\d.]+, [\d.]+, [\d.]+, [\d.]+, ([\d.]+),/))document.getElementById('ss').innerHTML=m[1]+'&#176;';
  if(m=t.match(/Fitur\s+: \[[\d.]+, [\d.]+, [\d.]+, [\d.]+, [\d.]+, ([\d.]+),/))document.getElementById('scp').innerHTML=m[1];
  if(m=t.match(/Fitur\s+: \[[\d.]+, [\d.]+, [\d.]+, [\d.]+, [\d.]+, [\d.]+, ([\d.]+),/))document.getElementById('src').innerHTML=m[1];
  if(m=t.match(/Fitur\s+: \[[\d.]+, [\d.]+, [\d.]+, [\d.]+, [\d.]+, [\d.]+, [\d.]+, ([\d.]+)\]/))document.getElementById('sfr').innerHTML=m[1];
  if(m=t.match(/Prediksi\s+: &#9658; (.+?) &#9668;/)||t.match(/Prediksi\s+: .{0,3} (.+?) .{0,3}/)||t.match(/Prediksi\s+: ► (.+?) ◄/)){
    const cls=(m[1]||'').trim();
    document.getElementById('r-name').innerHTML=cls;
    document.getElementById('r-icon').innerHTML=IC[cls]||'&#128663;';
    document.getElementById('r-badge').innerHTML='&#10003; Teridentifikasi';
  }
  // Opsi 2: format baru PLOT: — 1 pesan berisi 100 nilai dipisah '|'
  if(t.startsWith('PLOT:')){
    bins=t.slice(5).trim().split('|').map(Number);
    draw();
    return;
  }
}

function draw(){
  const cv=document.getElementById('cv');
  const ctx=cv.getContext('2d');
  cv.width=cv.offsetWidth||280;
  const W=cv.width,H=cv.height;
  if(!bins.length)return;
  const mx=Math.max(...bins)||1;
  ctx.clearRect(0,0,W,H);
  const g=ctx.createLinearGradient(0,0,0,H);
  g.addColorStop(0,'rgba(139,92,246,.8)');
  g.addColorStop(1,'rgba(99,102,241,.05)');
  ctx.beginPath();
  ctx.moveTo(0,H);
  bins.forEach((v,i)=>ctx.lineTo(i*(W/bins.length),H-(v/mx)*(H-4)));
  ctx.lineTo(W,H);
  ctx.closePath();
  ctx.fillStyle=g;
  ctx.fill();
  ctx.beginPath();
  ctx.strokeStyle='#a5b4fc';
  ctx.lineWidth=1.5;
  bins.forEach((v,i)=>i===0?ctx.moveTo(0,H-(v/mx)*(H-4)):ctx.lineTo(i*(W/bins.length),H-(v/mx)*(H-4)));
  ctx.stroke();
}
function connect(){
  ws=new WebSocket('ws://'+location.hostname+':81/');
  ws.onopen=()=>{dot.className='dot alive';stxt.textContent='Terhubung ✓';};
  ws.onmessage=e=>{ap(e.data);parse(e.data);};
  ws.onclose=()=>{dot.className='dot';stxt.textContent='Terputus — coba ulang...';setTimeout(connect,2500);};
  ws.onerror=()=>ws.close();
}
connect();
window.addEventListener('resize',()=>{if(bins.length)draw();});
</script>
</body></html>
)rawhtml";

// ─────────────────────────────────────────────
//  FORWARD DECLARATIONS
// ─────────────────────────────────────────────
void bacaDataLidar(HardwareSerial &serial, LidarData &s);
void jalankanKalibrasiAwal(HardwareSerial &lidar, LidarData &s, float targetJarak);
int  klasifikasiKNN(float dataBaru[8]);
void evaluasiFitur();
void resetSistem();
void cekTimeout();
void yieldDelay(unsigned long ms);

// ─────────────────────────────────────────────
//  SETUP & LOOP
// ─────────────────────────────────────────────
void setup() {
  Serial.begin(921600);
  lidar1.begin(115200, SERIAL_8N1, 16, 17);
  lidar2.begin(115200, SERIAL_8N1,  4,  5);

  // ── Setup LCD I2C ──
  Wire.begin(LCD_SDA, LCD_SCL);  // SDA=13, SCL=14
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0); lcd.print("Edge AI Classifier");
  lcd.setCursor(0, 1); lcd.print("TF-Luna v3.0 REMA");
  lcd.setCursor(0, 2); lcd.print("Kalibrasi sensor...");
  lcd.setCursor(0, 3); lcd.print("Harap tunggu");

  // PROTEKSI BROWNOUT: Matikan detektor drop tegangan agar tidak mudah merestart
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

  // ── Setup WiFi Access Point & Station Bersamaan ──
  // Kita butuh AP untuk Website, dan kita set channel 1 secara eksplisit.
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(WIFI_SSID, WIFI_PASS, 1);
  
  // PROTEKSI BROWNOUT 2: Turunkan daya pancar TX radio WiFi & ESP-NOW
  // (Mengurangi dari 20dBm ke 10dBm untuk menghemat arus listrik saat memancar)
  esp_wifi_set_max_tx_power(40); 
  
  Serial.printf("[WiFi] Hotspot aktif: SSID='%s' IP=%s\n",
                WIFI_SSID, WiFi.softAPIP().toString().c_str());
  Serial.println("[WiFi] Buka http://192.168.4.1 di browser HP Anda");

  // ── Setup WebServer & WebSocket (HARUS sebelum memanggil wlog!) ──
  webServer.on("/", [](){
    webServer.send_P(200, "text/html", WEB_PAGE);
  });
  webServer.begin();
  webSocket.begin();

  // Kirim histori log ke client yang baru connect
  webSocket.onEvent([](uint8_t num, WStype_t type, uint8_t* payload, size_t length){
    if (type == WStype_CONNECTED) {
      int start = (logCount < LOG_HISTORY_SIZE) ? 0 : logHead;
      for (int i = 0; i < logCount; i++) {
        int idx = (start + i) % LOG_HISTORY_SIZE;
        webSocket.sendTXT(num, logHistory[idx]);
      }
    }
  });

  // ── Setup ESP-NOW ──
  if (esp_now_init() != ESP_OK) {
    wlog("[ESP-NOW][ERR] Gagal inisialisasi ESP-NOW!\n");
  } else {
    esp_now_register_send_cb(onDataSent);

    // Daftarkan ESP32 penerima sebagai peer
    esp_now_peer_info_t peerInfo = {};
    memcpy(peerInfo.peer_addr, MAC_PENERIMA, 6);
    peerInfo.channel = 1;   // HARUS sama dengan channel SoftAP/STA (channel 1, fixed)
    peerInfo.encrypt = false;
    peerInfo.ifidx = WIFI_IF_AP; // KEMBALI KE AP: Karena kita pakai SoftAP (WIFI_AP_STA), jalur ESP-NOW lewat antena AP

    if (esp_now_add_peer(&peerInfo) != ESP_OK) {
      wlog("[ESP-NOW][ERR] Gagal mendaftarkan peer penerima!\n");
    } else {
      wlog("[ESP-NOW] Peer penerima terdaftar (B0:CB:D8:CE:E9:80)\n");
    }
  }

  wlog("\n=== EDGE AI VEHICLE CLASSIFIER v3.0 (REMA Filter) ===\n");
  wlog("[CAL] Kalibrasi Sensor 1...\n");
  jalankanKalibrasiAwal(lidar1, s1, TARGET_JARAK_KOSONG);
  wlog("[CAL] S1 offset = " + String(s1.offsetKalibrasi, 1) + " cm\n");

  wlog("[CAL] Kalibrasi Sensor 2...\n");
  jalankanKalibrasiAwal(lidar2, s2, TARGET_JARAK_KOSONG);
  wlog("[CAL] S2 offset = " + String(s2.offsetKalibrasi, 1) + " cm\n");

  wlog("[SYS] Kalibrasi selesai. Menunggu kendaraan...\n");

  // Tampilan standby setelah kalibrasi selesai
  lcd.clear();
  lcd.setCursor(0, 0); lcd.print("== SIAP DETEKSI ==");
  lcd.setCursor(0, 1); lcd.print("S1:" + String(s1.offsetKalibrasi,1) + "cm  S2:" + String(s2.offsetKalibrasi,1) + "cm");
  lcd.setCursor(0, 2); lcd.print("WiFi: " + String(WIFI_SSID));
  lcd.setCursor(0, 3); lcd.print("IP: 192.168.4.1");
}

void loop() {
  webServer.handleClient();
  webSocket.loop();
  bacaDataLidar(lidar1, s1);
  bacaDataLidar(lidar2, s2);
  cekTimeout();
  evaluasiFitur();
}

// ─────────────────────────────────────────────
//  BACA & PARSE SENSOR TF-LUNA
// ─────────────────────────────────────────────

/**
 * bacaDataLidar() — state machine parsing frame 9-byte TF-Luna.
 *
 * Format frame: [0x59][0x59][DistL][DistH][AmpL][AmpH][TempL][TempH][CS]
 *
 * Perbaikan vs versi lama:
 * - Byte ke-2 wajib 0x59; jika tidak, reset state (anti-misalignment)
 * - stopSampling diperiksa SEBELUM menyimpan ke buffer (fitur baru)
 * - Trigger sensor 2 langsung set stopSampling = true
 *
 * [REMA v3] Filter EMA diganti dengan REMA:
 *   Step 1 — EMA state update : jarakRemaState[n] = α·rawDist + (1-α)·jarakRemaState[n-1]
 *   Step 2 — Regularisasi lag : jarakMulus[n]     = jarakRemaState[n] + λ·(jarakRemaState[n] - jarakRemaState[n-1])
 */
void bacaDataLidar(HardwareSerial &lidarSerial, LidarData &s) {
  while (lidarSerial.available() > 0) {
    uint8_t b = lidarSerial.read();

    switch (s.dataIndex) {
      case 0:
        if (b == 0x59) { s.tfData[0] = b; s.dataIndex = 1; }
        break;
      case 1:
        if (b == 0x59) { s.tfData[1] = b; s.dataIndex = 2; }
        else           { s.dataIndex = 0; }   // ← FIX: reset jika header invalid
        break;
      default:
        s.tfData[s.dataIndex++] = b;
        break;
    }

    if (s.dataIndex == 9) {
      s.dataIndex = 0;

      // Verifikasi checksum
      uint16_t cs = 0;
      for (int i = 0; i < 8; i++) cs += s.tfData[i];
      if (s.tfData[8] != (uint8_t)(cs & 0xFF)) break; // ← frame rusak, buang

      // ── HITUNG JARAK + DETEKSI BACAAN KACA ──
      uint16_t distTF = s.tfData[2] | (s.tfData[3] << 8);
      float rawDist = (float)distTF + s.offsetKalibrasi;
      s.waktuSkrg   = micros();

      // Cek apakah ini bacaan kaca (nilai TF-Luna mentah terlalu kecil/nol)
      // PENTING: Gunakan distTF sebelum ditambah offset. Jika S1 offset = 5.2 dan 
      // TF-Luna kirim 0, rawDist = 5.2. Jika JARAK_MIN_VALID = 5.0, maka 5.2 < 5.0 (FALSE)
      // Ini membuat bacaan kaca dianggap valid dan mengacaukan seluruh siluet!
      bool bacaanInvalid = (distTF < (uint16_t)JARAK_MIN_VALID);

      if (!bacaanInvalid) {
        // Bacaan normal: update semua nilai dan simpan LKG
        s.jarakMentah = rawDist;

        // ── [REMA v3] FILTER REMA (menggantikan EMA) ──
        // Step 1: Simpan state EMA sebelumnya untuk perhitungan delta
        float prevRemaState = s.jarakRemaState;
        // Step 2: Update state EMA (filter dasar, tanpa regularisasi)
        s.jarakRemaState = REMA_ALPHA * rawDist + (1.0f - REMA_ALPHA) * prevRemaState;
        // Step 3: Terapkan regularisasi lag → hasil akhir jarakMulus
        s.jarakMulus     = s.jarakRemaState + REMA_LAMBDA * (s.jarakRemaState - prevRemaState);

        s.jarakLKG        = s.jarakMulus;   // simpan sebagai last-known-good
        s.jumlahKaca      = 0;
        if (s.bacaanKacaAktif) {
          wlog("[S" + String(s.idSensor) + "] Bacaan kaca selesai → kembali normal: " + String(rawDist,1) + " cm\n");
        }
        s.bacaanKacaAktif  = false;
      } else {
        // Bacaan invalid (kaca): pertahankan LKG, jangan update filter REMA
        s.jumlahKaca++;
        if (!s.bacaanKacaAktif) {
          wlog("[S" + String(s.idSensor) + "][KACA] Bacaan invalid (" + String(rawDist,1) + " cm) → pakai LKG: " + String(s.jarakLKG,1) + " cm\n");
        }
        s.bacaanKacaAktif = true;
        s.jarakMentah     = s.jarakLKG;  // gunakan LKG untuk trigger logic
        // jarakMulus & jarakRemaState tidak diupdate, biarkan nilai terakhir yang valid
      }


      // ── PENGAMBILAN SILUET (Sensor 1 SAJA) ──
      // FIX: Jangan dihentikan saat sensor 2 terpicu! Siluet harus diambil penuh.
      if (s.idSensor == 1 && s.terdeteksi && !arahSalah) {
        unsigned long sekarang = millis();
        if (jumlahSiluet < MAKS_BUFFER &&
            (sekarang - waktuSimpanTerakhir) >= (unsigned long)JEDA_SIMPAN_MS) {

          // Gunakan jarakMulus (tidak diupdate saat kaca), sehingga otomatis LKG
          float h = TARGET_JARAK_KOSONG - s.jarakMulus;
          if (h > 0.0f && h <= TARGET_JARAK_KOSONG && !s.bacaanKacaAktif) {
            // Simpan hanya sampel dengan bacaan valid
            bufferSiluet[jumlahSiluet].tinggi_cm = h;
            bufferSiluet[jumlahSiluet].waktu_us  = s.waktuSkrg;
            jumlahSiluet++;
          } else if (s.bacaanKacaAktif && s.terdeteksi) {
            // Kendaraan ada di depan sensor tapi kaca menghalangi → gunakan LKG
            float hLKG = TARGET_JARAK_KOSONG - s.jarakLKG;
            if (hLKG > 0.0f && hLKG <= TARGET_JARAK_KOSONG) {
              bufferSiluet[jumlahSiluet].tinggi_cm = hLKG;
              bufferSiluet[jumlahSiluet].waktu_us  = s.waktuSkrg;
              jumlahSiluet++;
            }
          }
          waktuSimpanTerakhir = sekarang;
        }
      }

      // ── DETEKSI TRIGGER ──
      // ── DETEKSI TRIGGER (menggunakan jarakMulus agar lag S1 & S2 identik & saling cancel) ──
      if (!s.terdeteksi && s.jarakMulus < AMBANG_BATAS_MASUK) {
        
        // Pengecekan kendaraan berlawanan arah (Sensor 2 terpicu sebelum Sensor 1)
        if (s.idSensor == 2 && waktuMasukS1_pertama == 0) {
          if (!arahSalah) {
            wlog("[WARN] Kendaraan berlawanan arah\n");
            arahSalah = true;
          }
        }

        // Strict Gate: Jika salah arah, JANGAN LAKUKAN TRIGGER APAPUN pada kedua sensor
        // Sistem dikunci total hingga mobil lewat sepenuhnya
        if (arahSalah) return;

        s.terdeteksi        = true;
        s.waktuTriggerMasuk = s.waktuSkrg;
        s.keluar_debounce   = 0;

        // Catat waktu masuk S1 PERTAMA kali saja (proteksi dari overwrite mid-crossing)
        if (s.idSensor == 1 && waktuMasukS1_pertama == 0 && !arahSalah) {
          waktuMasukS1_pertama = s.waktuSkrg;
        }
        // Catat waktu masuk S2 PERTAMA kali (mencegah kecepatan salah akibat pantulan kaca)
        if (s.idSensor == 2 && waktuMasukS2_pertama == 0 && !arahSalah) {
          waktuMasukS2_pertama = s.waktuSkrg;
        }

        if (s.idSensor == 2 && !arahSalah) {
          wlog("[S2] Kendaraan tiba di Sensor 2 | t=" + String((float)s.waktuSkrg*1e-6f,3) + " s | Sampel: " + String(jumlahSiluet) + "\n");
        }

      } else if (s.terdeteksi &&
                 s.jarakMulus > (AMBANG_BATAS_MASUK + HISTERESIS_KELUAR)) {
        s.keluar_debounce++;
        if (s.keluar_debounce >= 3) {
          s.terdeteksi         = false;
          s.waktuTriggerKeluar = s.waktuSkrg;
          s.keluar_debounce    = 0;
        }
      } else {
        s.keluar_debounce = 0; // reset jika kendaraan kembali mendekat
      }


    }
  }
}

// ─────────────────────────────────────────────
//  KALIBRASI AWAL — versi diperbaiki
// ─────────────────────────────────────────────

/**
 * Perbaikan: menggunakan parser yang sama dengan loop utama
 * (validasi header 0x59 0x59 + checksum) sehingga offset akurat.
 */
void jalankanKalibrasiAwal(HardwareSerial &lidar, LidarData &s, float targetJarak) {
  long  total     = 0;
  int   n         = 0;
  int   idx       = 0;
  uint8_t buf[9];

  Serial.print("  [");
  while (n < 50) {
    if (!lidar.available()) continue;
    uint8_t b = lidar.read();

    switch (idx) {
      case 0: if (b == 0x59) { buf[idx++] = b; } break;
      case 1:
        if (b == 0x59) { buf[idx++] = b; }
        else           { idx = 0; }    // ← FIX: header harus 0x59 0x59
        break;
      default: buf[idx++] = b; break;
    }

    if (idx == 9) {
      idx = 0;
      uint16_t cs = 0;
      for (int i = 0; i < 8; i++) cs += buf[i];
      if (buf[8] != (uint8_t)(cs & 0xFF)) continue; // buang frame rusak

      total += (buf[2] | (buf[3] << 8));
      n++;
      if (n % 10 == 0) Serial.print("█");
    }
  }
  Serial.println("]");
  s.offsetKalibrasi = targetJarak - ((float)total / 50.0f);
  s.jarakMulus      = targetJarak; // inisialisasi filter REMA (output)
  s.jarakRemaState  = targetJarak; // [REMA v3] inisialisasi state internal REMA
}

// ─────────────────────────────────────────────
//  EVALUASI FITUR & KLASIFIKASI
// ─────────────────────────────────────────────
void evaluasiFitur() {
  // Jika terdeteksi salah arah, hentikan evaluasi.
  // Reset akan ditangani oleh cekTimeout() setelah kondisi benar-benar sunyi.
  if (arahSalah) return;

  // Tandai awal kendaraan
  if (s1.waktuTriggerMasuk > 0 && !kendaraanLewat) {
    kendaraanLewat = true;
  }

  // Proses hanya jika kendaraan sudah lewat kedua sensor
  if (!kendaraanLewat)  return;
  if (s1.terdeteksi)    return;
  if (s2.terdeteksi)    return;
  if (!s1.waktuTriggerKeluar) return;
  if (!s2.waktuTriggerKeluar) return;

  // ── HITUNG WAKTU ANTAR-SENSOR ──
  // ★ FIX: Gunakan waktuMasukS1_pertama (bukan s1.waktuTriggerMasuk yang bisa ter-overwrite
  //         akibat mid-crossing reset) untuk memastikan t_durasi_s1 = waktu penuh kendaraan di S1
  unsigned long t0_s1 = (waktuMasukS1_pertama > 0) ? waktuMasukS1_pertama : s1.waktuTriggerMasuk;
  unsigned long t0_s2 = (waktuMasukS2_pertama > 0) ? waktuMasukS2_pertama : s2.waktuTriggerMasuk;

  float t_masuk_s   = (float)(t0_s2 - t0_s1)             * 1e-6f;
  float t_keluar_s  = (float)(s2.waktuTriggerKeluar - s1.waktuTriggerKeluar) * 1e-6f;
  float t_durasi_s1 = (float)(s1.waktuTriggerKeluar - t0_s1)             * 1e-6f
                    + 2.0f * EMA_LAG_KOMPENSASI_US * 1e-6f;

  // Sanity check waktu
  if (t_masuk_s < 0.01f || t_durasi_s1 < 0.01f || jumlahSiluet < 5) {
    wlog("[WARN] Timing tidak valid (t_masuk=" + String(t_masuk_s,2) + "s, t_durasi=" + String(t_durasi_s1,2) + "s, sampel=" + String(jumlahSiluet) + "). Direset.\n");
    resetSistem();
    return;
  }

  // ── ESTIMASI KECEPATAN ──
  float v_masuk = JARAK_ANTAR_SENSOR_CM / t_masuk_s;   // cm/s
  v_masuk = constrain(v_masuk, 5.0f, V_MAX_CMS);

  // ── DYNAMIC ACCELERATION CLAMPING ──
  // Semakin lambat kendaraan, semakin ketat batas akselerasi yang diizinkan.
  // Mencegah efek kuadrat t² meledak saat t_durasi panjang (kecepatan pelan).
  // Batas didasarkan pada kemampuan fisik nyata kendaraan di tiap rentang kecepatan.
  float a_maks_cms, a_min_cms;
  if (v_masuk < 139.0f) {           // < 5 km/h : merayap — susah akselerasi keras
    a_maks_cms =   30.0f;           //  +0.3 m/s²
    a_min_cms  =  -30.0f;           //  -0.3 m/s²
    wlog("[INF] Mode kecepatan pelan (<5 km/h): clamping akselerasi ±0.3 m/s²\n");
  } else if (v_masuk < 278.0f) {    // 5–10 km/h : lambat
    a_maks_cms =  150.0f;           //  +1.5 m/s²
    a_min_cms  = -200.0f;           //  -2.0 m/s²
  } else {                           // > 10 km/h : normal
    a_maks_cms =  600.0f;           //  +6.0 m/s² (akselerasi penuh)
    a_min_cms  = -1000.0f;          // -10.0 m/s² (rem darurat)
  }

  float v_keluar;
  if (t_keluar_s > 0.01f) {
    v_keluar = JARAK_ANTAR_SENSOR_CM / t_keluar_s;
    float a_estimasi = (v_keluar - v_masuk) / t_durasi_s1;

    if (a_estimasi > a_maks_cms || a_estimasi < a_min_cms || v_keluar <= 0) {
      v_keluar = v_masuk;
      wlog("[WARN] Akselerasi di luar batas (" + String(a_estimasi/100.0f,2) + " m/s²). Fallback ke v_masuk.\n");
    }
  } else {
    v_keluar = v_masuk;
  }
  v_keluar = constrain(v_keluar, 5.0f, V_MAX_CMS);

  float v_rata     = (v_masuk + v_keluar) * 0.5f;
  float akselerasi = (v_keluar - v_masuk) / t_durasi_s1;

  // ── ESTIMASI PANJANG KENDARAAN ──
  // Panjang = kecepatan × waktu kendaraan melintas S1 (ujung depan sampai ujung belakang)
  float panjang_cm = v_masuk * t_durasi_s1
                   + 0.5f * akselerasi * t_durasi_s1 * t_durasi_s1;

  // Fallback: jika hasil GLBB tidak wajar, gunakan kecepatan rata-rata
  if (panjang_cm < 50.0f || panjang_cm > 2000.0f) {
    panjang_cm = v_rata * t_durasi_s1;
    wlog("[INFO] Panjang fallback ke v_rata×t: " + String(panjang_cm,1) + " cm\n");
  }
  float f_panjang = panjang_cm / 100.0f;  // meter

  // ── FILTER NON-MOBIL (Orang, Motor, dll) ──
  // Berdasarkan dataset, panjang minimal mobil (CityCar) adalah ~3.2 meter.
  // Jika panjang terdeteksi kurang dari 2.5 meter (memberi toleransi error kecepatan),
  // maka itu dipastikan BUKAN MOBIL (orang/motor). Langsung abaikan dan buang.
  if (f_panjang < 2.5f) {
    wlog("[REJECT] Objek terlalu pendek (" + String(f_panjang, 2) + " m). Diabaikan (Bukan Mobil).\n");
    resetSistem();
    return;
  }


  // ── REKONSTRUKSI SPASIAL SILUET ──
  // Langkah 1: Hitung posisi X tiap sampel via GLBB (tetap dipakai untuk panjang
  //            dan untuk memetakan sampel ke bin yang tepat)
  static float posisiX[MAKS_BUFFER];

  float tinggiMaks  = 0.0f;
  float totalTinggi = 0.0f;
  int   validCount  = 0;

  unsigned long t0 = (waktuMasukS1_pertama > 0) ? waktuMasukS1_pertama : s1.waktuTriggerMasuk;

  for (int i = 0; i < jumlahSiluet; i++) {
    float dt = (float)(bufferSiluet[i].waktu_us - t0) * 1e-6f;
    if (dt < 0) dt = 0;
    posisiX[i] = v_masuk * dt + 0.5f * akselerasi * dt * dt;
    posisiX[i] = constrain(posisiX[i], 0.0f, panjang_cm);

    float h = bufferSiluet[i].tinggi_cm;
    if (h > 0.0f && h <= TARGET_JARAK_KOSONG) {
      if (h > tinggiMaks) tinggiMaks = h;
      totalTinggi += h;
      validCount++;
    }
  }

  if (validCount < 3) {
    wlog("[WARN] Siluet valid terlalu sedikit. Direset.\n");
    resetSistem();
    return;
  }

  float meanTinggi = totalTinggi / validCount;

  // ── NORMALISASI KE 100 BIN SPASIAL ──
  // Setiap bin mewakili 1% panjang badan kendaraan (0%=depan, 100%=belakang).
  // Semua fitur spasial dihitung dari bin → kebal terhadap perbedaan kecepatan.
  const int JUMLAH_BIN = 100;
  static float sumBin[JUMLAH_BIN];
  static int   cntBin[JUMLAH_BIN];
  for (int b = 0; b < JUMLAH_BIN; b++) { sumBin[b] = 0.0f; cntBin[b] = 0; }

  for (int i = 0; i < jumlahSiluet; i++) {
    float h = bufferSiluet[i].tinggi_cm;
    if (h <= 0.0f || h > TARGET_JARAK_KOSONG) continue;
    int b = (int)(posisiX[i] / panjang_cm * (float)JUMLAH_BIN);
    b = constrain(b, 0, JUMLAH_BIN - 1);
    sumBin[b] += h;
    cntBin[b]++;
  }

  // Rata-rata tiap bin; bin kosong diinterpolasi dari tetangga terdekat
  // (bisa terjadi saat kendaraan melaju cepat sehingga sampel jarang)
  static float tinggi_bin[JUMLAH_BIN];
  for (int b = 0; b < JUMLAH_BIN; b++) {
    if (cntBin[b] > 0) {
      tinggi_bin[b] = sumBin[b] / cntBin[b];
    } else {
      int prev = b - 1, next = b + 1;
      while (prev >= 0 && cntBin[prev] == 0) prev--;
      while (next < JUMLAH_BIN && cntBin[next] == 0) next++;
      if      (prev >= 0 && next < JUMLAH_BIN)
        tinggi_bin[b] = (sumBin[prev]/cntBin[prev] + sumBin[next]/cntBin[next]) * 0.5f;
      else if (prev >= 0)
        tinggi_bin[b] = sumBin[prev] / cntBin[prev];
      else if (next < JUMLAH_BIN)
        tinggi_bin[b] = sumBin[next] / cntBin[next];
      else
        tinggi_bin[b] = meanTinggi;
    }
  }

  // Cari bin maksimum (absolute) sebagai referensi
  int absMaksBin = 0;
  for (int b = 1; b < JUMLAH_BIN; b++) {
    if (tinggi_bin[b] > tinggi_bin[absMaksBin]) absMaksBin = b;
  }

  // Gunakan bin pertama yang mencapai 95% dari tinggi maksimal untuk menghindari noise
  // antena/spoiler di bagian belakang mobil yang menggeser perhitungan slope & posMax
  int idxMaksBin = absMaksBin;
  float thresholdPlateau = tinggi_bin[absMaksBin] * 0.95f;
  for (int b = 1; b <= absMaksBin; b++) {
    if (tinggi_bin[b] >= thresholdPlateau) {
      idxMaksBin = b;
      break;
    }
  }

  // Fitur 1 — Panjang kendaraan (m) [sudah dihitung dari GLBB]

  // Fitur 2 — Tinggi maksimum (m) [dari sampel mentah, tidak bergantung bin]
  float f_tinggi = tinggiMaks / 100.0f;

  // Fitur 3 — Std deviasi dari 100 bin (m) — ukuran variasi bentuk atap
  // Menggunakan bin membuat StdDev konsisten terlepas dari jumlah sampel mentah
  float varS   = 0.0f;
  int   lkgCount = 0;
  for (int b = 0; b < JUMLAH_BIN; b++) {
    float d = tinggi_bin[b] - meanTinggi;
    varS += d * d;
    if (b > 0 && fabsf(tinggi_bin[b] - tinggi_bin[b-1]) < 0.1f) lkgCount++;
  }
  float kompensasiLKG = 1.0f + ((float)lkgCount / JUMLAH_BIN) * 0.2f;
  float f_siluet = (sqrtf(varS / JUMLAH_BIN) * kompensasiLKG) / 100.0f;

  // Fitur 4 — Posisi relatif tinggi maks (0=depan, 1=belakang) — dari bin
  float f_posMax = (float)idxMaksBin / (float)(JUMLAH_BIN - 1);
  f_posMax = constrain(f_posMax, 0.0f, 1.0f);

  // Fitur 5 — Slope (°): sudut kap mesin ke atap — dari bin
  // h_awal: rata-rata 5 bin valid pertama (stabil, bukan 1 titik tunggal)
  float h_awal    = 0.0f;
  int   hAwalCount = 0;
  for (int b = 0; b < JUMLAH_BIN && hAwalCount < 5; b++) {
    if (cntBin[b] > 0) { h_awal += tinggi_bin[b]; hAwalCount++; }
  }
  h_awal = (hAwalCount > 0) ? (h_awal / hAwalCount) : meanTinggi;

  float jarak_ke_max  = ((float)idxMaksBin / (float)JUMLAH_BIN) * panjang_cm; // cm
  float tinggiRelatif = tinggiMaks - h_awal;
  if (tinggiRelatif < 0.0f) tinggiRelatif = 0.0f;
  float f_slope = (jarak_ke_max > 1.0f)
                  ? atan2f(tinggiRelatif, jarak_ke_max) * (180.0f / PI)
                  : 90.0f;

  // Fitur 6 — Compactness: rasio mean/max tinggi (semakin tinggi → flat-top seperti MPV)
  float f_compactness = (f_tinggi > 0.0f)
                        ? ((meanTinggi / 100.0f) / f_tinggi)
                        : 0.0f;

  // Fitur 7 — Rear Compactness: rata-rata bin 50-100% / tinggi maks
  // Bin 70-100% yang nilainya ≈ tinggiMaks diabaikan (kemungkinan LKG kaca belakang)
  float sumRear = 0.0f;
  int   cntRear = 0;
  for (int b = JUMLAH_BIN / 2; b < JUMLAH_BIN; b++) {
    if (b >= (JUMLAH_BIN * 7 / 10) && fabsf(tinggi_bin[b] - tinggiMaks) < 2.0f) continue;
    sumRear += tinggi_bin[b];
    cntRear++;
  }
  float f_rearComp = (cntRear > 0 && f_tinggi > 0.0f)
                     ? ((sumRear / cntRear) / 100.0f) / f_tinggi
                     : f_compactness;
  f_rearComp = constrain(f_rearComp, 0.0f, 1.0f);

  // Fitur 8 — Flat Roof Percentage: persen bin yang tingginya >= 90% tinggi maks
  int   flatCount = 0;
  float threshold = tinggiMaks * 0.90f;
  for (int b = 0; b < JUMLAH_BIN; b++) {
    if (tinggi_bin[b] >= threshold) flatCount++;
  }
  float f_flatRoof = (float)flatCount / (float)JUMLAH_BIN;

  // ── KLASIFIKASI KNN ──
  float fiturBaru[8] = { f_panjang, f_tinggi, f_siluet, f_posMax,
                         f_slope, f_compactness, f_rearComp, f_flatRoof };
  int   hasil        = klasifikasiKNN(fiturBaru);

  // ── OUTPUT ──
  String out = "";
  out += "\n═══════════════════════════════════════════\n";
  out += "Kecepatan  : Masuk=" + String(v_masuk*0.036f,1) + " km/h | Keluar=" + String(v_keluar*0.036f,1) + " km/h\n";
  out += "Akselerasi : " + String(akselerasi/100.0f,2) + " m/s²\n";
  out += "Panjang    : " + String(f_panjang,2) + " m\n";
  out += "Tinggi Maks: " + String(f_tinggi,2) + " m\n";
  out += "Sampel     : " + String(validCount) + " titik valid dari " + String(jumlahSiluet) + " total\n";
  out += "Fitur      : [" + String(f_panjang,2) + ", " + String(f_tinggi,2) + ", " + String(f_siluet,3) + ", " + String(f_posMax,3) + ", " + String(f_slope,1) + ", " + String(f_compactness,3) + ", " + String(f_rearComp,3) + ", " + String(f_flatRoof,3) + "]\n";
  out += "Prediksi   : ► " + String((hasil >= 0) ? NAMA_KELAS[hasil].c_str() : "TIDAK DIKETAHUI") + " ◄\n";
  out += "═══════════════════════════════════════════\n";
  wlog(out);

  // ── TAMPIL LCD ──
  tampilLCD(
    (hasil >= 0) ? NAMA_KELAS[hasil] : "UNKNOWN",
    f_panjang, f_tinggi, f_siluet, f_posMax,
    f_slope, f_compactness, f_rearComp, f_flatRoof,
    v_masuk * 0.036f, v_keluar * 0.036f
  );

  // ── KIRIM VIA ESP-NOW ──
  String kelasHasil = (hasil >= 0) ? NAMA_KELAS[hasil] : "UNKNOWN";
  kirimESPNow(kelasHasil);
  wlog("[ESP-NOW] Mengirim kelas: " + kelasHasil + "\n");

  // ── OUTPUT DATA PLOT (bin vs tinggi) — Opsi 2: 100 nilai dikirim sebagai 1 pesan ──
  // Format: PLOT:val0|val1|...|val99
  // Menggantikan 100x wlog() menjadi 1x wlog() → beban WebSocket turun drastis
  String plotMsg = "PLOT:";
  for (int b = 0; b < JUMLAH_BIN; b++) {
    plotMsg += String(tinggi_bin[b], 2);
    if (b < JUMLAH_BIN - 1) plotMsg += "|";
  }
  plotMsg += "\n";
  wlog(plotMsg);

  resetSistem();
}

// ─────────────────────────────────────────────
//  TAMPIL LCD — scroll 3 halaman: Hasil, Fitur A, Fitur B
// ─────────────────────────────────────────────
void tampilLCD(const String& kelas, float panjang, float tinggi, float siluet,
               float posMax, float slope, float compact, float rear, float flatRoof,
               float vMasuk, float vKeluar) {

  // Helper: pad/truncate string ke lebar tetap (rata kiri)
  auto pad = [](String s, int w) -> String {
    while ((int)s.length() < w) s += ' ';
    if ((int)s.length() > w) s = s.substring(0, w);
    return s;
  };

  // ── HALAMAN 1: Hasil Klasifikasi & Kecepatan (4 detik) ──
  lcd.clear();
  lcd.setCursor(0, 0); lcd.print(pad(">> " + kelas + " <<", 20));
  lcd.setCursor(0, 1); lcd.print(pad("P:" + String(panjang,2) + "m T:" + String(tinggi,2) + "m", 20));
  lcd.setCursor(0, 2); lcd.print(pad("Vin:" + String(vMasuk,1) + " Vout:" + String(vKeluar,1) + "km/h", 20));
  lcd.setCursor(0, 3); lcd.print(pad("Slope:" + String(slope,1) + String((char)223) + " StD:" + String(siluet,3), 20));
  yieldDelay(4000); // ← non-blocking: WebServer & WebSocket tetap berjalan

  // ── HALAMAN 2: Fitur f3–f6 (3 detik) ──
  lcd.clear();
  lcd.setCursor(0, 0); lcd.print("-- FITUR SPASIAL --");
  lcd.setCursor(0, 1); lcd.print(pad("PosMax : " + String(posMax,3), 20));
  lcd.setCursor(0, 2); lcd.print(pad("Compact: " + String(compact,3), 20));
  lcd.setCursor(0, 3); lcd.print(pad("RearCmp: " + String(rear,3), 20));
  yieldDelay(3000); // ← non-blocking

  // ── HALAMAN 3: Fitur f7–f8 & standby (3 detik) ──
  lcd.clear();
  lcd.setCursor(0, 0); lcd.print("-- FITUR ATAP ----");
  lcd.setCursor(0, 1); lcd.print(pad("FlatRoof: " + String(flatRoof,3), 20));
  lcd.setCursor(0, 2); lcd.print(pad("StdDev  : " + String(siluet,3), 20));
  lcd.setCursor(0, 3); lcd.print(pad("Pred: >> " + kelas + " <<", 20));
  yieldDelay(3000); // ← non-blocking

  // ── Kembali ke layar standby ──
  lcd.clear();
  lcd.setCursor(0, 0); lcd.print("== SIAP DETEKSI ==");
  lcd.setCursor(0, 1); lcd.print(pad("Terakhir: " + kelas, 20));
  lcd.setCursor(0, 2); lcd.print(pad("P:" + String(panjang,2) + "m T:" + String(tinggi,2) + "m", 20));
  lcd.setCursor(0, 3); lcd.print("IP: 192.168.4.1");
}


int klasifikasiKNN(float dataBaru[8]) {
  // 1. Min-Max normalisasi data baru (8 dimensi)
  float dataNorm[8];
  for (int i = 0; i < JUMLAH_FITUR; i++) {
    float range = FITUR_MAX[i] - FITUR_MIN[i];
    dataNorm[i] = (range > 0.0f)
                  ? (dataBaru[i] - FITUR_MIN[i]) / range
                  : 0.0f;
    dataNorm[i] = constrain(dataNorm[i], 0.0f, 1.0f);
  }

  // 2. Cari K terdekat (squared Euclidean di 8 dimensi)
  float jarakTerdekat[NILAI_K];
  int   labelTerdekat[NILAI_K];
  for (int i = 0; i < NILAI_K; i++) {
    jarakTerdekat[i] = 1e30f;
    labelTerdekat[i] = -1;
  }

  for (int i = 0; i < JUMLAH_DATA; i++) {
    float jarakKuadrat = 0.0f;
    for (int j = 0; j < JUMLAH_FITUR; j++) {
      float range = FITUR_MAX[j] - FITUR_MIN[j];
      float valNorm = (range > 0.0f)
                      ? (dataset[i].fitur[j] - FITUR_MIN[j]) / range
                      : 0.0f;
      float d = dataNorm[j] - valNorm;
      // Gunakan BOBOT_FITUR untuk memberikan skala prioritas pada tiap dimensi
      jarakKuadrat += BOBOT_FITUR[j] * (d * d);
    }

    // Insertion sort ke K terdekat
    for (int k = 0; k < NILAI_K; k++) {
      if (jarakKuadrat < jarakTerdekat[k]) {
        for (int m = NILAI_K - 1; m > k; m--) {
          jarakTerdekat[m] = jarakTerdekat[m - 1];
          labelTerdekat[m] = labelTerdekat[m - 1];
        }
        jarakTerdekat[k] = jarakKuadrat;
        labelTerdekat[k] = dataset[i].label;
        break;
      }
    }
  }

  // 3. Majority voting
  int voting[5] = {0};
  for (int i = 0; i < NILAI_K; i++) {
    if (labelTerdekat[i] >= 0 && labelTerdekat[i] < 5) {
      voting[labelTerdekat[i]]++;
    }
  }

  int labelPemenang = -1, maxVote = 0;
  for (int i = 0; i < 5; i++) {
    if (voting[i] > maxVote) {
      maxVote      = voting[i];
      labelPemenang = i;
    }
  }
  return labelPemenang;
}

// ─────────────────────────────────────────────
//  TIMEOUT & RESET
// ─────────────────────────────────────────────
void cekTimeout() {
  // TIMEOUT KEHENINGAN (Idle Timeout)
  // Memeriksa apakah ada fisik kendaraan di bawah salah satu sensor (menggunakan jarak mentah)
  bool adaFisik = (s1.jarakMulus > 0 && s1.jarakMulus < AMBANG_BATAS_MASUK) || 
                  (s2.jarakMulus > 0 && s2.jarakMulus < AMBANG_BATAS_MASUK);

  if (adaFisik) {
    waktuKosong = 0; // Bekukan timer karena ada objek fisik menutupi sensor
  } else {
    if (waktuKosong == 0) {
      waktuKosong = micros();
    } else if ((micros() - waktuKosong) > 1500000UL) { // 1.5 detik area benar-benar kosong
      // Jika masih ada state menggantung (ghost state / sisa salah arah)
      if (kendaraanLewat || waktuMasukS1_pertama > 0 || waktuMasukS2_pertama > 0 || arahSalah) {
        wlog("[SYS] Area bersih. Mereset sisa data menggantung...\n");
        resetSistem();
      }
    }
  }

  // TIMEOUT MACET PARAH (> 60 detik)
  // Fallback jika sensor tertutup objek permanen (misal benda nyangkut di sensor)
  if (waktuMasukS1_pertama > 0 && (micros() - waktuMasukS1_pertama > 60000000UL)) {
    wlog("[!] TIMEOUT — Sensor terhalang >60 detik. Reset paksa.\n");
    resetSistem();
  }
}

/**
 * resetSistem() — reset state TANPA menghapus offset kalibrasi.
 * Offset kalibrasi hanya dihitung sekali di setup().
 */
void resetSistem() {
  // Simpan offset sebelum reset
  float offset1 = s1.offsetKalibrasi;
  float offset2 = s2.offsetKalibrasi;
  float mulus1  = s1.jarakMulus;    // pertahankan filter REMA output
  float mulus2  = s2.jarakMulus;
  float rema1   = s1.jarakRemaState; // [REMA v3] pertahankan state internal REMA
  float rema2   = s2.jarakRemaState;

  // ★ FIX: Cek apakah ini reset di tengah crossing (S1 masih aktif atau baru saja aktif)
  // Jika ya, pertahankan waktuMasukS1_pertama agar t_durasi_s1 tetap akurat
  bool midCrossing = (s1.terdeteksi || (s1.waktuTriggerMasuk > 0 && s1.waktuTriggerKeluar == 0));

  // Reset struktur sensor
  s1 = LidarData();  s1.idSensor = 1;
  s2 = LidarData();  s2.idSensor = 2;

  // Restore nilai penting
  s1.offsetKalibrasi = offset1;  s1.jarakMulus = mulus1;  s1.jarakRemaState = rema1;
  s2.offsetKalibrasi = offset2;  s2.jarakMulus = mulus2;  s2.jarakRemaState = rema2;

  // Reset state global
  kendaraanLewat       = false;
  arahSalah            = false;
  waktuKosong          = 0;
  jumlahSiluet         = 0;
  waktuSimpanTerakhir  = 0;

  // ★ FIX: Jika bukan mid-crossing, bersihkan waktu sesi S1 dan S2
  // Jika mid-crossing, PERTAHANKAN waktuMasuk pertama agar crossing time tetap benar
  if (!midCrossing) {
    waktuMasukS1_pertama = 0;
    waktuMasukS2_pertama = 0;
  }
}
