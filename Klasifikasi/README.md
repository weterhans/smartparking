# 🔭 Edge AI Vehicle Classifier — TF-Luna LiDAR

<div align="center">

![Version](https://img.shields.io/badge/versi-3.0-blue?style=for-the-badge)
![Platform](https://img.shields.io/badge/platform-ESP32-orange?style=for-the-badge&logo=espressif)
![Sensor](https://img.shields.io/badge/sensor-TF--Luna%20LiDAR-green?style=for-the-badge)
![Algorithm](https://img.shields.io/badge/algoritma-FWkNN-purple?style=for-the-badge)
![License](https://img.shields.io/badge/lisensi-MIT-yellow?style=for-the-badge)
![Status](https://img.shields.io/badge/status-Selesai%20Skripsi-brightgreen?style=for-the-badge)

**Sistem klasifikasi kendaraan real-time berbasis Edge AI menggunakan dua sensor LiDAR TF-Luna dan algoritma Feature-Weighted K-Nearest Neighbor (FWkNN) yang berjalan langsung di ESP32 tanpa koneksi cloud.**

[📖 Dokumentasi](#-dokumentasi) · [🚀 Mulai Cepat](#-mulai-cepat) · [📊 Hasil Pengujian](#-hasil-pengujian) · [🛠 Hardware](#-diagram-hardware) · [🤝 Kontribusi](#-kontribusi)

</div>

---

## 📋 Daftar Isi

- [Gambaran Umum](#-gambaran-umum)
- [Fitur Utama](#-fitur-utama)
- [Arsitektur Sistem](#-arsitektur-sistem)
- [Diagram Hardware](#-diagram-hardware)
- [Struktur Repositori](#-struktur-repositori)
- [Mulai Cepat](#-mulai-cepat)
- [Kelas Kendaraan](#-kelas-kendaraan)
- [Algoritma FWkNN](#-algoritma-fwknn)
- [Filter REMA](#-filter-rema)
- [Web Monitor](#-web-monitor)
- [Hasil Pengujian](#-hasil-pengujian)
- [Riwayat Versi](#-riwayat-versi)
- [Dokumentasi](#-dokumentasi)
- [Kontribusi](#-kontribusi)
- [Penulis](#-penulis)
- [Lisensi](#-lisensi)

---

## 🧩 Gambaran Umum

Sistem ini merupakan implementasi **Edge AI** untuk klasifikasi jenis kendaraan bermotor secara real-time menggunakan profil siluet yang direkonstruksi dari dua sensor LiDAR [Benewake TF-Luna](https://www.benewake.com/TFLuna.html). Seluruh proses komputasi berjalan di atas mikrokontroler **ESP32** tanpa memerlukan koneksi internet atau server eksternal.

### Latar Belakang

> Penelitian ini dikembangkan sebagai Tugas Akhir (Skripsi) di **Politeknik Negeri Malang**, Program Studi Teknik Elektro. Tujuannya adalah mengeksplorasi kemungkinan implementasi kecerdasan buatan ringan (*TinyML / Edge AI*) pada perangkat keras mikrokontroler untuk keperluan manajemen lalu lintas.

### Cara Kerja (Ringkasan)

```
Kendaraan Lewat → S1 & S2 TF-Luna → Profil Siluet → Ekstraksi 8 Fitur → FWkNN (K=3) → Kelas Kendaraan
```

1. **Deteksi**: Dua sensor LiDAR (S1 dan S2) dipasang di atas portal jalan dengan jarak 53 cm antar sensor.
2. **Akuisisi**: Saat kendaraan melintas, tinggi profil disampling hingga 100 Hz dengan filter REMA.
3. **Rekonstruksi Spasial**: Timestamp tiap sampel dikonversi ke posisi spasial menggunakan kecepatan terukur (dari selisih waktu S1→S2).
4. **Ekstraksi Fitur**: 8 fitur geometri dihitung dari profil siluet (panjang, tinggi, kemiringan, kerapatan, dll).
5. **Klasifikasi**: FWkNN dengan K=3 dan 75 data referensi mengklasifikasikan kendaraan ke salah satu dari 5 kelas.
6. **Output**: Hasil ditampilkan di LCD 20×4, Web Monitor (WiFi), dan dikirim via ESP-NOW ke perangkat penerima.

---

## ✨ Fitur Utama

| Fitur | Keterangan |
|---|---|
| 🚗 **5 Kelas Kendaraan** | City Car, Sedan, MPV, SUV, Pickup |
| ⚡ **Real-time Edge AI** | Inferensi <50ms, seluruhnya di ESP32 |
| 📡 **Dual LiDAR** | Pengukuran kecepatan & arah dari S1+S2 |
| 🌊 **Filter REMA** | Regularized EMA untuk lag minimal tanpa noise |
| 📶 **Web Monitor** | Dashboard real-time via WiFi (WebSocket) |
| 📺 **LCD 20×4** | Tampilan langsung di perangkat |
| 📡 **ESP-NOW** | Kirim hasil klasifikasi ke ESP32 penerima |
| 🔍 **Anti-Kaca** | Mitigasi bacaan invalid saat kaca kendaraan |
| 🔄 **Anti-Arah Salah** | Deteksi kendaraan yang melintas terbalik |
| 🛡 **Debounce** | Stabilisasi sinyal keluar anti-flicker |

---

## 🏗 Arsitektur Sistem

```
┌─────────────────────────────────────────────────────────────────┐
│                         PORTAL JALAN                            │
│                                                                  │
│   ┌──────────┐         53 cm         ┌──────────┐               │
│   │ TF-Luna  │◄──────────────────────│ TF-Luna  │               │
│   │  Sensor 1│     (S1 → S2)         │  Sensor 2│               │
│   │  (RX:16) │                       │  (RX:4)  │               │
│   └────┬─────┘                       └────┬─────┘               │
│        │ UART 115200                       │ UART 115200         │
│        └──────────────┬────────────────────┘                    │
│                       │                                          │
│              ┌────────▼────────┐                                 │
│              │     ESP32       │                                  │
│              │                 │                                  │
│              │  ┌───────────┐  │◄── I2C (SDA:13, SCL:14)        │
│              │  │  FWkNN    │  │                      │          │
│              │  │  K=3      │  │               ┌──────▼──────┐  │
│              │  │  8 Fitur  │  │               │  LCD 20×4   │  │
│              │  │  REMA     │  │               │  (I2C 0x27) │  │
│              │  └───────────┘  │               └─────────────┘  │
│              │                 │                                  │
│              └────┬───────┬────┘                                 │
│                   │       │                                       │
│            WiFi AP│       │ESP-NOW                               │
│                   │       └──────────────────► ESP32 Penerima   │
│                   ▼                                               │
│            Web Monitor                                            │
│            (192.168.4.1)                                         │
│            WebSocket :81                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔌 Diagram Hardware

Lihat panduan lengkap di [docs/HARDWARE_SETUP.md](docs/HARDWARE_SETUP.md).

### Ringkasan Pin ESP32

| Komponen | Pin ESP32 | Keterangan |
|---|---|---|
| TF-Luna S1 RX | GPIO 16 | HardwareSerial 2 |
| TF-Luna S1 TX | GPIO 17 | HardwareSerial 2 |
| TF-Luna S2 RX | GPIO 4 | HardwareSerial 1 |
| TF-Luna S2 TX | GPIO 5 | HardwareSerial 1 |
| LCD SDA | GPIO 13 | I2C kustom |
| LCD SCL | GPIO 14 | I2C kustom |

### Komponen yang Dibutuhkan

- 1× ESP32 DevKit (WROOM-32 atau sejenisnya)
- 2× Sensor LiDAR [Benewake TF-Luna](https://www.benewake.com/TFLuna.html)
- 1× LCD I2C 20×4 karakter (alamat 0x27 atau 0x3F)
- Kabel jumper, catu daya 5V/3A

---

## 📁 Struktur Repositori

```
tf-luna-vehicle-classifier/
│
├── 📁 firmware/                  # Kode firmware ESP32 (Arduino)
│   ├── 📁 vehicle_v3/            # ★ VERSI UTAMA — REMA Filter
│   │   └── vehicle_v3.ino
│   ├── 📁 vehicle_v2/            # Versi sebelumnya — EMA Filter
│   │   └── vehicle.ino
│   ├── 📁 vehicle_tanpa_filter_panjang/  # Varian: tanpa filter panjang
│   │   └── vehicle_tanpa_filter_panjang.ino
│   ├── 📁 tes_tfluna/            # Sketch pengujian sensor TF-Luna
│   │   └── tes_tfluna.ino
│   └── README.md
│
├── 📁 analysis/                  # Script Python untuk analisis hasil
│   ├── confusion_matrix_f1.py    # Confusion Matrix + F1 Score
│   ├── hitung_fdr.py             # Optimasi bobot LOOCV
│   ├── analisis_misklasifikasi.py# Analisis kasus misklasifikasi
│   ├── requirements.txt          # Dependensi Python
│   └── README.md
│
├── 📁 visualization/             # Visualisasi interaktif (HTML)
│   ├── Simulasi_Siluet_Web.html  # Simulasi siluet kendaraan
│   ├── fitur_visualization.html  # Visualisasi distribusi fitur
│   ├── glbb_visualization.html   # Visualisasi model GLBB kecepatan
│   └── README.md
│
├── 📁 docs/                      # Dokumentasi teknis
│   ├── HARDWARE_SETUP.md         # Panduan pemasangan hardware
│   ├── ALGORITHM.md              # Penjelasan algoritma FWkNN & REMA
│   └── WEBMONITOR_API.md         # Referensi API Web Monitor
│
├── 📁 .github/                   # Template GitHub
│   ├── 📁 ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   └── pull_request_template.md
│
├── README.md                     # ← Anda di sini
├── CHANGELOG.md                  # Riwayat perubahan versi
├── CONTRIBUTING.md               # Panduan kontribusi
├── LICENSE                       # Lisensi MIT
└── .gitignore                    # File yang diabaikan Git
```

---

## 🚀 Mulai Cepat

### Prasyarat

- [Arduino IDE](https://www.arduino.cc/en/software) versi 2.x atau lebih baru
- Board package: **esp32 by Espressif Systems** (versi 3.x / IDF v5.x)
- Python 3.8+ (untuk script analisis)

### 1. Pasang Library Arduino

Buka Arduino IDE → Tools → Manage Libraries, lalu cari dan pasang:

```
WebSockets         by Markus Sattler   (versi ≥ 2.4.0)
LiquidCrystal I2C  by Frank de Brabander
```

> **Catatan**: Library `WiFi`, `WebServer`, `HardwareSerial`, `esp_now`, `Wire` sudah tersedia bawaan ESP32 core.

### 2. Konfigurasi Firmware

Buka `firmware/vehicle_v3/vehicle_v3.ino` dan sesuaikan:

```cpp
// ── Nama WiFi Hotspot ESP32 ──
const char* WIFI_SSID = "NamaHotspot";   // ← ubah sesuai keinginan
const char* WIFI_PASS = "12345678";      // ← min 8 karakter

// ── MAC Address ESP32 Penerima (ESP-NOW) ──
const uint8_t MAC_PENERIMA[6] = {0xB0, 0xCB, 0xD8, 0xCE, 0xE9, 0x80};

// ── Jarak Fisik Antar Sensor ──
const float JARAK_ANTAR_SENSOR_CM = 53.f;  // ← ukur dan sesuaikan

// ── Tinggi Portal (Tinggi Sensor dari Tanah) ──
const float TARGET_JARAK_KOSONG = 250.0f;  // ← cm
```

### 3. Upload ke ESP32

1. Sambungkan ESP32 via USB
2. Pilih board: **ESP32 Dev Module**
3. Pilih port COM yang sesuai
4. Klik **Upload** (Ctrl+U)

### 4. Akses Web Monitor

1. Sambungkan perangkat (HP/laptop) ke WiFi ESP32 (`FarizHP` secara default)
2. Buka browser dan akses: **http://192.168.4.1**
3. Dashboard akan terhubung otomatis via WebSocket

### 5. Jalankan Analisis Python (Opsional)

```bash
cd analysis
pip install -r requirements.txt
python confusion_matrix_f1.py    # Buat confusion matrix
python hitung_fdr.py             # Analisis optimasi bobot
python analisis_misklasifikasi.py# Analisis kasus gagal
```

---

## 🚗 Kelas Kendaraan

Sistem mengklasifikasikan kendaraan ke dalam 5 kategori:

| Label | Kelas | Panjang (m) | Tinggi (m) | Contoh |
|:---:|---|---|---|---|
| 0 | **City Car** | 3.29 – 3.64 | 1.48 – 1.49 | Honda Jazz, Brio, Kia Picanto |
| 1 | **Sedan** | 4.36 – 4.75 | 1.45 – 1.50 | Honda Accord |
| 2 | **MPV** | 3.45 – 4.11 | 1.60 – 1.65 | Avanza, Xpander, Mobilio, Grand Livina |
| 3 | **SUV** | 3.86 – 4.34 | 1.65 – 1.79 | Honda HRV, Mitsubishi Pajero, Toyota Rush |
| 4 | **Pickup** | 3.50 – 5.46 | 1.75 – 1.85 | Mitsubishi Colt L300 |

---

## 🧠 Algoritma FWkNN

Sistem menggunakan **Feature-Weighted K-Nearest Neighbor (FWkNN)** dengan K=3 dan dataset referensi 75 sampel.

### 8 Fitur yang Diekstraksi

| # | Fitur | Satuan | Bobot | Keterangan |
|:---:|---|---|:---:|---|
| 0 | **Panjang** | meter | 0.5 | Panjang total kendaraan |
| 1 | **Tinggi** | meter | **2.0** | Tinggi maks kendaraan (pembeda utama) |
| 2 | **StdDev** | - | 1.0 | Standar deviasi profil siluet |
| 3 | **PosMax** | normalized | 1.0 | Posisi relatif titik tertinggi |
| 4 | **Slope** | derajat | 1.5 | Sudut kemiringan atap kendaraan |
| 5 | **Compactness** | - | 1.2 | Rasio area terisi terhadap bounding box |
| 6 | **RearComp** | - | 1.0 | Compactness bagian belakang kendaraan |
| 7 | **FlatRoof** | - | 1.0 | Skor atap datar |

### Rumus Jarak Euclidean Terbobot

```
d(q, r) = sqrt( Σ [ w_i × ((q_i - r_i) / (max_i - min_i))² ] )
```

Lihat penjelasan lengkap di [docs/ALGORITHM.md](docs/ALGORITHM.md).

---

## 🌊 Filter REMA

**REMA (Regularized Exponential Moving Average)** adalah pengembangan dari filter EMA standar yang digunakan pada versi v3.

```
State[n]   = α × raw[n] + (1-α) × State[n-1]          ← EMA murni
Output[n]  = State[n] + λ × (State[n] - State[n-1])    ← kompensasi lag
```

| Parameter | Nilai | Keterangan |
|---|---|---|
| `REMA_ALPHA` | 0.50 | Kecepatan respons (setara EMA alpha) |
| `REMA_LAMBDA` | 0.40 | Kekuatan kompensasi lag (0 = EMA biasa) |
| Lag residual | ~5 ms | Jauh lebih kecil dari EMA (~14 ms) |

---

## 🖥 Web Monitor

ESP32 membuat hotspot WiFi sendiri dan menjalankan web server di port 80. Dashboard real-time diperbarui via WebSocket di port 81.

| Alamat | Keterangan |
|---|---|
| `http://192.168.4.1` | Halaman Web Monitor |
| `ws://192.168.4.1:81` | WebSocket data stream |

Fitur dashboard:
- ✅ Log serial real-time berwarna
- ✅ Hasil klasifikasi kendaraan terakhir
- ✅ Statistik kecepatan masuk & keluar
- ✅ Tampilan jarak sensor S1 & S2 secara live
- ✅ Grafik siluet kendaraan

---

## 📊 Hasil Pengujian

Pengujian dilakukan dengan **24 sampel** dari 5 kelas kendaraan:

| Kelas | Jumlah Sampel | Benar | Salah | Akurasi |
|---|:---:|:---:|:---:|:---:|
| City Car | 5 | 5 | 0 | 100% |
| Sedan | 4 | 4 | 0 | 100% |
| MPV | 5 | 4 | 1 | 80% |
| SUV | 5 | 4 | 1 | 80% |
| Pickup | 5 | 5 | 0 | 100% |
| **Total** | **24** | **22** | **2** | **91.67%** |

> Kasus misklasifikasi: Grand Livina (MPV → City Car) dan Mitsubishi Pajero (SUV → MPV) akibat kedekatan fitur antar kelas yang bertetangga.

---

## 📅 Riwayat Versi

| Versi | File | Perubahan Utama |
|---|---|---|
| **v3.0** ★ | `firmware/vehicle_v3/` | Filter REMA menggantikan EMA; lag diturunkan 14ms → 5ms |
| **v2.0** | `firmware/vehicle_v2/` | Buffer siluet bertimestamp; rekonstruksi spasial akurat |
| **Tanpa Filter** | `firmware/vehicle_tanpa_filter_panjang/` | Varian eksperimental tanpa filter panjang kendaraan |

Lihat [CHANGELOG.md](CHANGELOG.md) untuk riwayat lengkap.

---

## 📖 Dokumentasi

| Dokumen | Deskripsi |
|---|---|
| [HARDWARE_SETUP.md](docs/HARDWARE_SETUP.md) | Panduan pemasangan & kalibrasi hardware |
| [ALGORITHM.md](docs/ALGORITHM.md) | Penjelasan mendalam algoritma FWkNN & REMA |
| [WEBMONITOR_API.md](docs/WEBMONITOR_API.md) | Referensi API Web Monitor & WebSocket |
| [firmware/README.md](firmware/README.md) | Panduan firmware dan versi |
| [analysis/README.md](analysis/README.md) | Panduan script analisis Python |
| [visualization/README.md](visualization/README.md) | Panduan visualisasi HTML |

---

## 🤝 Kontribusi

Kontribusi sangat disambut! Silakan baca [CONTRIBUTING.md](CONTRIBUTING.md) untuk panduan lengkap.

Secara singkat:
1. Fork repositori ini
2. Buat branch fitur: `git checkout -b fitur/nama-fitur`
3. Commit perubahan: `git commit -m 'feat: tambah fitur baru'`
4. Push ke branch: `git push origin fitur/nama-fitur`
5. Buat Pull Request

---

## 👤 Penulis

**Fari Hadi P**

- 📧 GitHub: [@farihadi](https://github.com/farihadi)
- 🎓 Tugas Akhir — Politeknik Negeri Malang
- 📚 Program Studi: Teknik Elektro

---

## 📄 Lisensi

Proyek ini dilisensikan di bawah [MIT License](LICENSE).

```
MIT License — bebas digunakan, dimodifikasi, dan didistribusikan
dengan tetap mencantumkan atribusi kepada penulis asli.
```

---

<div align="center">

Dibuat dengan ❤️ untuk keperluan penelitian akademik

**Politeknik Negeri Malang · Teknik Elektro · 2025**

</div>
