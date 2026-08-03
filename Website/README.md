# 🌐 Website – Smart Parking System

Folder ini berisi kode untuk bagian **Website / Backend** pada sistem Smart Parking.

## Deskripsi

Bagian Website bertanggung jawab untuk:
- Backend server menggunakan **Flask** (Python)
- Dashboard monitoring parkir secara real-time
- Sistem autentikasi & manajemen pengguna
- Prediksi kepadatan volume kendaraan (Regresi Linear)
- Integrasi dengan hardware ESP32 via Serial USB
- Sistem langganan (subscription) berbasis RFID

## Persyaratan Sistem

- **Python 3.8+**
- **MySQL Server**
- **Raspberry Pi** (atau PC/Laptop Windows) sebagai Server Lokal

## Setup & Cara Menjalankan

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
- Buka `raspi_hardware_controller.py` dan sesuaikan nama port Serial USB ESP32 (misal: `COM3` di Windows atau `/dev/ttyUSB0` di Linux)

### 5. Jalankan Server
```bash
python app.py
```

Akses dashboard melalui browser: `http://localhost:5000` atau `http://<IP-RaspberryPi>:5000`

## Struktur File

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
├── ukur_latensi_skripsi.py      # Script pengukuran latensi
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

## Anggota Tim

- **Nama**: Joko Febrianto
- **Bagian**: Website / Backend Flask

---
*Folder ini adalah bagian dari project skripsi Smart Parking System.*
