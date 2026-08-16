# 🌐 Website – Smart Parking System

<div align="center">

![Version](https://img.shields.io/badge/versi-1.0-blue?style=for-the-badge)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red?style=for-the-badge&logo=raspberrypi)
![Backend](https://img.shields.io/badge/backend-Flask-black?style=for-the-badge&logo=flask)
![Database](https://img.shields.io/badge/database-MySQL-blue?style=for-the-badge&logo=mysql)
![License](https://img.shields.io/badge/lisensi-MIT-yellow?style=for-the-badge)
![Status](https://img.shields.io/badge/status-Selesai%20Skripsi-brightgreen?style=for-the-badge)

**Backend server dan dashboard monitoring sistem Smart Parking berbasis Raspberry Pi, dengan NFC PN532, LCD TFT 2.6", Push Button, dan integrasi ESP32 via Serial USB.**

[📖 Deskripsi](#-deskripsi) · [🔌 Koneksi Pin](#-koneksi-pin-raspberry-pi) · [🚀 Setup & Menjalankan](#-setup--cara-menjalankan) · [📁 Struktur File](#-struktur-file)

</div>

---

## 📋 Daftar Isi

- [Deskripsi](#-deskripsi)
- [Persyaratan Sistem](#-persyaratan-sistem)
- [Koneksi Pin Raspberry Pi](#-koneksi-pin-raspberry-pi)
- [Setup & Cara Menjalankan](#-setup--cara-menjalankan)
- [Struktur File](#-struktur-file)


---

## 🧩 Deskripsi

Folder ini berisi kode untuk bagian **Website / Backend** pada sistem Smart Parking. Bagian ini bertanggung jawab untuk:

| Fitur | Keterangan |
|---|---|
| 🖥 **Backend Flask** | Server utama menggunakan Python Flask |
| 📊 **Dashboard Real-time** | Monitoring parkir secara live |
| 🔐 **Autentikasi** | Sistem login & manajemen pengguna |
| 📈 **Prediksi Kepadatan** | Model Regresi Linear volume kendaraan |
| 🔌 **Integrasi ESP32** | Komunikasi via Serial USB |
| 💳 **Langganan RFID** | Sistem subscription berbasis RFID/NFC |

---

## ⚙️ Persyaratan Sistem

- **Python 3.8+**
- **MySQL Server**
- **Raspberry Pi** (atau PC/Laptop Windows) sebagai Server Lokal

### Komponen Hardware (Raspberry Pi)

- 1× Raspberry Pi (model 3B+ / 4 atau sejenisnya)
- 1× Modul NFC **PN532** (mode I2C)
- 1× Layar **LCD TFT 2.6 Inch** (mode SPI)
- 1× **Push Button** (tombol fisik)
- Kabel jumper Female-to-Female

---

## 🔌 Koneksi Pin Raspberry Pi

Berikut adalah panduan lengkap penyambungan kabel hardware ke Raspberry Pi.

---

### 1. Modul NFC PN532 (Mode I2C)

> **⚠️ Penting:** Pastikan sakelar/jumper kecil di modul PN532 Anda sudah disetel ke **mode I2C** sebelum menyambungkan kabel.

| Kabel Modul | Pin Raspberry Pi | Nomor Pin | Keterangan |
|:---:|---|:---:|---|
| **VCC** | 3.3V *(atau 5V)* | Pin 1 *(atau Pin 2)* | Cek tulisan di modul, umumnya mendukung 3.3V |
| **GND** | GND | Pin 6 | Ground |
| **SDA** | GPIO 2 (SDA) | Pin 3 | Data I2C |
| **SCL** | GPIO 3 (SCL) | Pin 5 | Clock I2C |

```
Raspberry Pi                      PN532 NFC Module
─────────────                     ────────────────
Pin 1  (3.3V)      ─────────────► VCC
Pin 6  (GND)       ─────────────► GND
Pin 3  (GPIO2/SDA) ─────────────► SDA
Pin 5  (GPIO3/SCL) ─────────────► SCL
```

---

### 2. Layar LCD TFT 2.6 Inch (Mode SPI)

> **📝 Catatan:** Penamaan pin di layar Anda mungkin sedikit berbeda, namun secara umum merujuk pada fungsi yang sama.

| Kabel Modul | Pin Raspberry Pi | Nomor Pin | Keterangan |
|:---:|---|:---:|---|
| **VCC** | 3.3V | Pin 17 | Daya layar |
| **GND** | GND | Pin 20 | Ground |
| **CS** *(atau CE)* | GPIO 8 / CE0 | Pin 24 | Chip Select SPI |
| **RESET** *(atau RST)* | GPIO 25 | Pin 22 | Reset layar |
| **DC** *(atau RS)* | GPIO 24 | Pin 18 | Data/Command select |
| **MOSI** *(atau SDA pada LCD)* | GPIO 10 | Pin 19 | Data SPI (Master Out) |
| **SCK** *(atau SCLK)* | GPIO 11 | Pin 23 | Clock SPI |
| **MISO** | GPIO 9 | Pin 21 | Data SPI (Master In) |
| **LED** *(atau BLK)* | 3.3V | — | Sumber listrik backlight layar |

```
Raspberry Pi                     LCD TFT 2.6"
─────────────                    ────────────
Pin 17 (3.3V)   ───────────────► VCC
Pin 20 (GND)    ───────────────► GND
Pin 24 (GPIO8)  ───────────────► CS / CE
Pin 22 (GPIO25) ───────────────► RESET / RST
Pin 18 (GPIO24) ───────────────► DC / RS
Pin 19 (GPIO10) ───────────────► MOSI / SDA
Pin 23 (GPIO11) ───────────────► SCK / SCLK
Pin 21 (GPIO9)  ───────────────► MISO
3.3V            ───────────────► LED / BLK
```

---

### 3. Push Button (Tombol)

> **📝 Catatan:** Tombol biasanya **tidak memiliki polaritas** — kedua kakinya dapat dipasang bolak-balik.

| Kaki Tombol | Pin Raspberry Pi | Nomor Pin | Keterangan |
|:---:|---|:---:|---|
| **Kaki Kiri** | GPIO 17 | Pin 11 | Input sinyal tombol |
| **Kaki Kanan** | GND | Pin 14 | Ground |

```
Raspberry Pi                  Push Button
─────────────                 ───────────
Pin 11 (GPIO17) ─────────────● Kaki Kiri
Pin 14 (GND)    ─────────────● Kaki Kanan
```

---

### Ringkasan Seluruh Pin

| Komponen | Fungsi | Nomor Pin | GPIO |
|---|---|:---:|---|
| NFC PN532 | VCC | 1 | 3.3V |
| NFC PN532 | GND | 6 | GND |
| NFC PN532 | SDA | 3 | GPIO 2 |
| NFC PN532 | SCL | 5 | GPIO 3 |
| LCD TFT | VCC | 17 | 3.3V |
| LCD TFT | GND | 20 | GND |
| LCD TFT | CS/CE | 24 | GPIO 8 |
| LCD TFT | RESET | 22 | GPIO 25 |
| LCD TFT | DC/RS | 18 | GPIO 24 |
| LCD TFT | MOSI | 19 | GPIO 10 |
| LCD TFT | SCK | 23 | GPIO 11 |
| LCD TFT | MISO | 21 | GPIO 9 |
| Push Button | Input | 11 | GPIO 17 |
| Push Button | GND | 14 | GND |

---

## 🚀 Setup & Cara Menjalankan

### 1. Persiapan Database MySQL
```bash
# Buat database baru
mysql -u root -p -e "CREATE DATABASE smart_parking;"

# Import struktur tabel
mysql -u root -p smart_parking < smart_parking.sql
```

### 2. Setup Virtual Environment
```bash
# Di Windows
python -m venv venv
venv\Scripts\activate

# Di Linux/Raspberry Pi
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Konfigurasi
- Buka `config.py` dan sesuaikan koneksi database (user, password, host)
- Buka `raspi_hardware_controller.py` dan sesuaikan nama port Serial USB ESP32  
  (misal: `COM3` di Windows atau `/dev/ttyUSB0` di Linux)

### 5. Jalankan Server
```bash
python app.py
```

Akses dashboard melalui browser: `http://localhost:5000` atau `http://<IP-RaspberryPi>:5000`

---

## 📁 Struktur File

```
Website/
├── app.py                        # Backend utama Flask & Regresi Linear
├── auth_routes.py                # Route autentikasi
├── config.py                     # Konfigurasi database & server
├── extensions.py                 # Inisialisasi ekstensi Flask
├── init_user.py                  # Script inisialisasi user admin
├── local_auth.py                 # Autentikasi lokal
├── models.py                     # Model database (SQLAlchemy)
├── raspi_hardware_controller.py  # Komunikasi Serial USB ESP32
├── requirements.txt              # Dependensi Python
├── smart_parking.sql             # Skema database MySQL
├── ukur_latensi_skripsi.py       # Script pengukuran latensi
├── static/                       # Aset CSS, JS, Gambar
│   ├── css/
│   ├── js/
│   └── img/
└── templates/                    # Template HTML (Frontend)
    ├── base.html
    ├── index.html
    ├── monitoring.html
    ├── prediction.html
    ├── subscription.html
    └── ...
```

---

## 👤 Penulis

- **Nama**: Joko Febrianto
- **Bagian**: Website / Backend Flask

---

<div align="center">

Dibuat dengan ❤️ untuk keperluan penelitian akademik

*Folder ini adalah bagian dari project skripsi Smart Parking System.*

</div>
