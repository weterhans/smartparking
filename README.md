# 🚗 Smart Parking System

<div align="center">

![Version](https://img.shields.io/badge/versi-1.0-blue?style=for-the-badge)
![Platform](https://img.shields.io/badge/platform-ESP32%20%7C%20Raspberry%20Pi-orange?style=for-the-badge&logo=espressif)
![Network](https://img.shields.io/badge/jaringan-WSN-teal?style=for-the-badge)
![Protocol](https://img.shields.io/badge/protokol-ESP--NOW-purple?style=for-the-badge)
![Backend](https://img.shields.io/badge/backend-Flask-black?style=for-the-badge&logo=flask)
![Database](https://img.shields.io/badge/database-MySQL-blue?style=for-the-badge&logo=mysql)
![AI](https://img.shields.io/badge/AI-KNN-green?style=for-the-badge)
![Status](https://img.shields.io/badge/status-Selesai%20Skripsi-brightgreen?style=for-the-badge)

**Sistem Smart Parking berbasis *Wireless Sensor Network* (WSN) terintegrasi menggunakan ESP32 (ESP-NOW) dan Raspberry Pi sebagai server pusat, dilengkapi algoritma Kecerdasan Buatan untuk klasifikasi kendaraan dan prediksi kepadatan.**

[📁 Struktur Repo](#-struktur-repository) · [🏗 Arsitektur](#️-gambaran-sistem) · [✨ Fitur](#-fitur-utama) · [👥 Tim](#-tim-pengembang) · [📌 Kontribusi](#-cara-berkontribusi-untuk-anggota-tim)

</div>

---

## 📋 Daftar Isi

- [Gambaran Umum](#-gambaran-umum)
- [Fitur Utama](#-fitur-utama)
- [Gambaran Sistem](#️-gambaran-sistem)
- [Struktur Repository](#-struktur-repository)
- [Tim Pengembang](#-tim-pengembang)
- [Cara Berkontribusi](#-cara-berkontribusi-untuk-anggota-tim)

---

## 🧩 Gambaran Umum

Sistem ini merupakan implementasi **Smart Parking** berbasis *Wireless Sensor Network* (WSN) yang mengintegrasikan:

- Mikrokontroler **ESP32** dengan protokol komunikasi **ESP-NOW** (tanpa router/internet)
- **Raspberry Pi 4** sebagai server pusat lokal
- **Sensor Ultrasonik JSN SR04T** untuk deteksi ketersediaan slot parkir (6 slot)
- **LED Indikator** per slot sebagai penanda status parkir
- **NFC PN532** untuk sistem akses berbasis kartu
- **RTC DS3231** untuk pencatatan waktu yang akurat
- **TF-Luna LiDAR** (2 buah) untuk klasifikasi jenis kendaraan di gerbang
- **Panel P10 & Keypad** untuk tampilan dan input lokal di pintu masuk
- **TFT LCD 2.4 Inch & Push Button** di sisi server
- **Flask & MySQL** untuk backend dan penyimpanan data
- **Algoritma AI** untuk klasifikasi kendaraan dan prediksi kepadatan

---

## ✨ Fitur Utama

| Fitur | Keterangan |
|---|---|
| 🅿️ **Deteksi Slot Real-time** | Sensor JSN SR04T memantau ketersediaan 6 slot parkir secara langsung |
| 📡 **Komunikasi ESP-NOW** | Transfer data antar ESP32 tanpa memerlukan koneksi internet |
| 💳 **Akses RFID/NFC** | Sistem masuk & keluar otomatis berbasis kartu RFID |
| 🚧 **Palang Pintu Otomatis** | Motor Servo mengontrol buka/tutup palang berdasarkan otorisasi |
| 📊 **Dashboard Web** | Monitoring parkir secara real-time melalui browser |
| 🤖 **Prediksi AI** | Regresi Linear untuk memprediksi kepadatan kendaraan |
| 🗄 **Database MySQL** | Penyimpanan riwayat parkir, pengguna, dan transaksi |
| 🔐 **Autentikasi** | Sistem login & manajemen pengguna untuk admin |

---

## 🏗️ Gambaran Sistem

```
╔══════════════════════════════════════════════════════════════════════════╗
║                    AREA PARKIR — 6 SLOT (ESP MASTER 3)                   ║
║                                                                          ║
║  ┌─────────────────────────┐                ┌─────────────────────────┐  ║
║  │  [JSN SR04T] [LED] SLOT 4│               │  [JSN SR04T] [LED] SLOT 3│ ║
║  └────────────┬────────────┘                └────────────┬────────────┘  ║
║               │                                          │               ║
║  ┌─────────────────────────┐  ┌──────────┐  ┌─────────────────────────┐  ║
║  │  [JSN SR04T] [LED] SLOT 5│  │ESP MASTER│  │  [JSN SR04T] [LED] SLOT 2│║
║  └────────────┬────────────┘  │    3     │  └────────────┬────────────┘  ║
║               │               └────┬─────┘               │               ║
║  ┌─────────────────────────┐       │       ┌─────────────────────────┐   ║
║  │  [JSN SR04T] [LED] SLOT 6│       │       │  [JSN SR04T] [LED] SLOT 1│ ║
║  └────────────┬────────────┘       │       └────────────┬────────────┘   ║
║               └────────────────────┘────────────────────┘                ║
╚════════════════════════════╤═════════════════════════════════════════════╝
                    ESP-NOW  │  ESP-NOW
           ┌─────────────────┴───────────────────┐
           │                                     │
           ▼                                     ▼
╔══════════════════════════╗         ╔═══════════════════════════════════╗
║  PINTU KIRI              ║         ║  PINTU KANAN / SERVER             ║
║  (ESP SLAVE 1/MASTER 2)  ║         ║  (ESP SLAVE 2/MASTER 4)           ║
║                          ║         ║           │ Serial USB            ║
║  ┌──────────────────┐    ║         ║           ▼                       ║
║  │  PANEL P10       │    ║         ║  ┌────────────────────────────┐   ║
║  │  (Display Slot)  │    ║         ║  │      Raspberry Pi 4        │   ║
║  └──────────────────┘    ║         ║  │                            │   ║
║  ┌──────────────────┐    ║         ║  │  ┌─────────┐ ┌──────────┐  │   ║
║  │  KEYPAD          │    ║         ║  │  │  Flask  │ │  MySQL   │  │   ║
║  └──────────────────┘    ║         ║  │  │ Backend │ │   DB     │  │   ║
║           │ ESP-NOW      ║         ║  │  └─────────┘ └──────────┘  │   ║
╚═══════════╪══════════════╝         ║  │  ┌─────────┐ ┌──────────┐  │   ║
            │                        ║  │  │Prediksi │ │ RTC DS   │  │   ║
            │                        ║  │  │         │ │  3231    │  │   ║
            ▼                        ║  │  └─────────┘ └──────────┘  │   ║
╔══════════════════════════╗         ║  └──────────────┬─────────────┘   ║
║  KLASIFIKASI KENDARAAN   ║         ║                 │ IP Local        ║
║  (ESP MASTER 1)          ║         ║                 ▼                 ║
║                          ║         ║           ┌───────────┐           ║
║  [TF Luna LiDAR 1]       ║         ║           │  Website  │           ║
║  [TF Luna LiDAR 2]  ──►  ║         ║           │(Dashboard)│           ║
║  [ESP MASTER 1]          ║         ║           └───────────┘           ║
║  [LCD I2C]               ║         ║                                   ║
║  → HASIL KLASIFIKASI     ║         ║  [TFT LCD 2.4"] [PN532] [Tombol]  ║
╚══════════════════════════╝         ╚═══════════════════════════════════╝
                            
```

### Alur Kerja Sistem

| Komponen | Node | Peran |
|---|---|---|
| **Area Parkir** | ESP Master 3 | Membaca 6 sensor JSN SR04T & LED Indikator, kirim status slot via ESP-NOW |
| **Pintu Kiri** | ESP Slave 1/Master 2 | Menerima data slot, tampil di Panel P10, input Keypad, teruskan via ESP-NOW |
| **Klasifikasi** | ESP Master 1 | Membaca 2× TF-Luna LiDAR, jalankan klasifikasi kendaraan, tampil di LCD I2C |
| **Pintu Kanan** | ESP Slave 2/Master 4 | Agregator data dari semua node, kirim ke Raspberry Pi via Serial USB |
| **Server** | Raspberry Pi 4 | Flask backend, MySQL, Prediksi AI, RTC DS3231, sajikan dashboard web |
| **Antarmuka Lokal** | Hardware RPi | TFT LCD 2.4", NFC PN532, Push Button sebagai UI lokal di Raspberry Pi |

---

## 📁 Struktur Repository

Repository ini dibagi menjadi **3 bagian utama** yang dikerjakan oleh anggota tim secara terpisah:

| Folder | Deskripsi | Penanggung Jawab |
|---|---|---|
| [`Website/`](./Website/) | Backend Flask, Dashboard Web, Prediksi Regresi Linear | Joko |
| [`Klasifikasi/`](./Klasifikasi/) | Edge AI klasifikasi kendaraan via TF-Luna LiDAR & FWkNN di ESP32 | Fariz |
| [`Monitoring_Slot/`](./Monitoring_Slot/) | Kode ESP32 & sensor JSN SR04T untuk monitoring slot parkir | Ikhsan |

> 📂 Lihat `README.md` di dalam masing-masing folder untuk panduan setup dan cara menjalankan bagian tersebut.

```
smartparking/
│
├── 📁 Website/                  # Backend Flask & Dashboard Web
│   ├── 📁 static/               # Aset CSS, JS, Gambar
│   ├── 📁 templates/            # Template HTML (Frontend)
│   └── README.md
│
├── 📁 Klasifikasi/              # Edge AI — Klasifikasi Kendaraan (TF-Luna LiDAR)
│   ├── 📁 firmware/             # Kode firmware ESP32 (Arduino IDE)
│   ├── 📁 analysis/             # Script Python analisis & confusion matrix
│   ├── 📁 visualization/        # Visualisasi interaktif (HTML)
│   ├── 📁 docs/                 # Dokumentasi teknis (hardware, algoritma)
│   └── README.md
│
├── 📁 Monitoring_Slot/          # Firmware ESP32 & Sensor JSN SR04T
│   └── README.md
│
└── README.md                    # ← Anda di sini
```

---

## 👥 Tim Pengembang

| Nama | Bagian | Tanggung Jawab |
|---|---|---|
| **Joko** | Website / Backend Flask | Server Flask, Dashboard, Prediksi, NFC PN532, TFT LCD |
| **Fariz** | Klasifikasi Kendaraan | Edge AI klasifikasi jenis kendaraan menggunakan TF-Luna LiDAR & algoritma FWkNN di ESP32 |
| **Ikhsan** | Monitoring Slot | Firmware ESP32 & sensor JSN SR04T untuk monitoring ketersediaan slot parkir |

---

## 📌 Cara Berkontribusi (untuk Anggota Tim)

### 1. Clone Repository

```bash
git clone https://github.com/weterhans/smartparking.git
cd smartparking
```

### 2. Masuk ke Folder Bagian Anda

```bash
# Contoh untuk bagian Klasifikasi
cd Klasifikasi

# Contoh untuk bagian Monitoring Slot
cd Monitoring_Slot
```

### 3. Kerjakan & Commit Perubahan

```bash
# Tambahkan perubahan di folder Anda
git add Klasifikasi/

# Tulis pesan commit yang deskriptif
git commit -m "feat(klasifikasi): tambah model klasifikasi SVM"

# Push ke repository
git push origin main
```

> [!WARNING]
> **Penting**: Hanya lakukan perubahan di dalam folder bagian Anda sendiri untuk menghindari konflik dengan anggota tim lain.


---

<div align="center">

Dibuat dengan ❤️ untuk keperluan penelitian akademik

**Project Skripsi – Sistem Smart Parking**

---

🎓 **Politeknik Negeri Malang**

📚 Jurusan Teknik Elektro · Program Studi Jaringan Telekomunikasi Digital

📅 2025

</div>
