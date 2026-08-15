# Panduan Pemasangan Hardware

Dokumen ini menjelaskan cara memasang dan mengkalibrasi seluruh komponen hardware sistem klasifikasi kendaraan.

---

## 🧰 Daftar Komponen

| Komponen | Spesifikasi | Jumlah |
|---|---|:---:|
| ESP32 DevKit | WROOM-32 (dual-core 240 MHz, 4MB Flash) | 1 |
| Sensor LiDAR | Benewake TF-Luna (jarak 0.2–8 m, UART 115200) | 2 |
| LCD | I2C 20×4 karakter, 5V, alamat 0x27 | 1 |
| Catu Daya | 5V ≥ 2A (disarankan 3A untuk stabilitas) | 1 |
| Kabel Jumper | Male-Female, Male-Male | secukupnya |

---

## 🔌 Diagram Wiring

### ESP32 → TF-Luna Sensor 1 (S1)

```
ESP32 GPIO16 (RX2) ─────────────────── TF-Luna TX
ESP32 GPIO17 (TX2) ─────────────────── TF-Luna RX
ESP32 GND          ─────────────────── TF-Luna GND
ESP32 5V           ─────────────────── TF-Luna VCC (5V)
```

> ⚠️ TF-Luna beroperasi di level UART 3.3V meskipun VCC-nya 5V. Kompatibel langsung dengan GPIO ESP32 3.3V.

### ESP32 → TF-Luna Sensor 2 (S2)

```
ESP32 GPIO4  (RX1) ─────────────────── TF-Luna TX
ESP32 GPIO5  (TX1) ─────────────────── TF-Luna RX
ESP32 GND          ─────────────────── TF-Luna GND
ESP32 5V           ─────────────────── TF-Luna VCC (5V)
```

### ESP32 → LCD I2C 20×4

```
ESP32 GPIO13 (SDA) ─────────────────── LCD SDA
ESP32 GPIO14 (SCL) ─────────────────── LCD SCL
ESP32 GND          ─────────────────── LCD GND
ESP32 5V           ─────────────────── LCD VCC (5V)
```

> ℹ️ Pin I2C kustom (GPIO13/14) digunakan untuk menghindari konflik dengan LiDAR di GPIO 4, 5, 16, 17.

---

## 📐 Pemasangan Fisik di Portal

```
                        PORTAL JALAN (tampak atas)
┌──────────────────────────────────────────────────┐
│                                                  │
│  ┌─────────┐  ←──── 53 cm ────→  ┌─────────┐   │
│  │ TF-Luna │                     │ TF-Luna │   │
│  │  (S1)   │                     │  (S2)   │   │
│  └─────────┘                     └─────────┘   │
│       ↑                               ↑         │
│       │ mengarah ke bawah (tanah)      │         │
│       └──────────── ESP32 ────────────┘         │
│                                                  │
└──────────────────────────────────────────────────┘
                         ↓ arah kendaraan
```

```
                        PORTAL JALAN (tampak samping)
┌────────────────────────────────────────────────────┐
│  Balok portal                                      │
│  ┌──┬──────────────────────────────────────────┐  │
│  │S1│←──────── 250 cm (tinggi kosong) ────────→│  │
│  └──┘                                           │  │
│                        ↑                        │  │
│               Kendaraan melintas                 │  │
│                                                  │  │
│  ══════════════════════════════════════════════  │  │
│  (permukaan jalan)                               │  │
└────────────────────────────────────────────────────┘
```

### Ketentuan Pemasangan

| Parameter | Nilai | Keterangan |
|---|---|---|
| Tinggi sensor dari tanah | **250 cm** | Parameter `TARGET_JARAK_KOSONG` di firmware |
| Ambang batas trigger | **246 cm** | Kendaraan terdeteksi saat objek < 246 cm |
| Jarak antar sensor | **53 cm** | Parameter `JARAK_ANTAR_SENSOR_CM` di firmware |
| Sudut sensor | **90° (vertikal ke bawah)** | Pastikan sensor tegak lurus dengan jalan |

---

## ⚙️ Kalibrasi Awal

### Prosedur Kalibrasi

Kalibrasi otomatis berjalan saat ESP32 pertama kali dinyalakan:

1. **Jangan ada kendaraan** di bawah sensor saat booting
2. Serial Monitor / Web Monitor akan menampilkan:
   ```
   [KALIBRASI] S1 mentah=249.8 → offset=-0.2
   [KALIBRASI] S2 mentah=250.3 → offset=+0.3
   ```
3. Nilai offset disimpan dan digunakan untuk semua pembacaan berikutnya

### Kalibrasi Manual

Jika kalibrasi otomatis tidak berjalan sempurna, set manual di firmware:

```cpp
// Di struct LidarData:
s1.offsetKalibrasi = -0.2f;  // cm
s2.offsetKalibrasi = +0.3f;  // cm
```

---

## 🔍 Verifikasi Instalasi

Setelah upload firmware dan pemasangan hardware, verifikasi dengan langkah berikut:

1. Buka Serial Monitor (115200 baud) atau Web Monitor
2. Tanpa kendaraan, pembacaan S1 dan S2 harus sekitar **250 cm**
3. Lewatkan tangan di bawah sensor → nilai turun ke < 246 cm → deteksi aktif
4. Tarik tangan → nilai kembali ke ~250 cm → deteksi selesai

### Log Normal Saat Booting

```
[BOOT] Edge AI Vehicle Classifier v3.0
[WIFI] AP aktif: FarizHP (192.168.4.1)
[ESPNOW] Inisialisasi OK
[LCD] Ready
[KALIBRASI] S1 offset=-0.2 | S2 offset=+0.3
[SIAP] Menunggu kendaraan...
```

---

## ⚠️ Catatan Penting

- **Jarak sensor** harus diukur akurat dengan penggaris (±0.5 cm) karena berpengaruh langsung pada rekonstruksi panjang kendaraan
- **Kaca mobil** dapat menyebabkan sensor membaca 0 cm — ini normal, sistem menggunakan mekanisme LKG (Last Known Good)
- **Cahaya matahari langsung** ke lubang sensor dapat menyebabkan bacaan tidak stabil — pasang sensor di area teduh atau tambahkan pelindung
- **Getaran portal** dapat mempengaruhi kalibrasi — pasang sensor sekencang mungkin
