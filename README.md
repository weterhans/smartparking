# Smart Parking System 🚗

Sistem *Smart Parking* berbasis *Internet of Things* (IoT) terintegrasi yang dirancang menggunakan mikrokontroler ESP32 (Protokol Komunikasi ESP-NOW) dan Raspberry Pi sebagai *server* pusat. Sistem ini juga dilengkapi dengan algoritma Kecerdasan Buatan (Regresi Linear) untuk memprediksi kepadatan volume kendaraan di masa mendatang.

## 🛠️ Persyaratan Sistem (System Requirements)

### 1. Perangkat Keras (Hardware)
* **Raspberry Pi** (atau PC/Laptop Windows) sebagai *Server* Lokal.
* **ESP32** (Minimal 2 unit: 1 sebagai Master/Gateway, 1 atau lebih sebagai Slave/Sensor).
* **Modul Sensor Jarak Ultrasonik (HC-SR04)** untuk deteksi slot parkir.
* **Modul RFID / NFC** untuk akses masuk pelanggan (Langganan).
* **Motor Servo** untuk palang pintu gerbang.

### 2. Perangkat Lunak (Software)
* **Python 3.8+**
* **MySQL Server**
* **Arduino IDE** (dengan ekstensi papan ESP32 terinstal) untuk *flashing* perangkat keras.

---

## 🚀 Panduan Instalasi & Menjalankan Sistem

Bagi pengembang selanjutnya, ikuti langkah-langkah berurutan di bawah ini agar *hardware* dan *software* dapat berjalan dengan sinkron:

### Langkah 1: Persiapan Database MySQL
1. Pastikan layanan MySQL (*MySQL Service*) sudah menyala di perangkat Anda.
2. Buat *database* baru dengan nama `smart_parking`.
3. Lakukan *import* struktur tabel menggunakan file SQL yang telah disediakan:
   ```bash
   mysql -u root -p smart_parking < smart_parking/smart_parking.sql
   ```

### Langkah 2: Persiapan Perangkat Keras (Flashing ESP32)
1. Buka aplikasi **Arduino IDE**.
2. **Konfigurasi Node Slave (Sensor):** Buka file `konek_joko_MASTER.ino` yang ada di dalam folder proyek. Hubungkan ESP32 Slave dengan kabel USB, pilih port yang sesuai, lalu tekan **Upload**.
3. **Konfigurasi Node Master (Gateway):** Buka file `JOKO_gateway_espnow.ino`. Hubungkan ESP32 Master (yang terhubung dengan RFID & Servo) ke USB, lalu tekan **Upload**.
4. **PENTING:** Biarkan kabel USB ESP32 Master *tetap terhubung* ke port USB Raspberry Pi/PC Anda. Jangan dicabut, karena sistem *server* akan membaca data serial dari port USB ini.

### Langkah 3: Persiapan Perangkat Lunak (Backend Flask)
1. Buka *Terminal* atau *Command Prompt* dan masuk ke dalam folder proyek.
2. Aktifkan *virtual environment* (sangat disarankan):
   ```bash
   # Di Windows
   venv\Scripts\activate
   # Di Linux/Raspberry Pi
   source venv/bin/activate
   ```
3. Instal semua paket *library* Python yang dibutuhkan:
   ```bash
   pip install -r requirements.txt
   ```
4. Buka file `config.py` dan `raspi_hardware_controller.py`. Pastikan nama port Serial USB (misal: `COM3` di Windows atau `/dev/ttyUSB0` di Linux) sudah sesuai dengan port tempat Anda mencolokkan ESP32 Master!

### Langkah 4: Menjalankan Server Utama
Setelah *database* siap, ESP32 menyala, dan *port* serial terhubung, jalankan perintah ini di terminal:
```bash
python app.py
```
Jika berhasil, *server* akan berjalan secara lokal. Anda bisa mengakses *dashboard* melalui *browser* di perangkat mana saja yang berada pada satu jaringan WiFi yang sama dengan mengetikkan alamat IP dari Raspberry Pi (Contoh: `http://10.42.0.1:5000` atau `http://localhost:5000`).

---

## 📂 Struktur Direktori Utama

* `/smart_parking/esp32_nodes/` : Berisi *source code* C++ (`.ino`) untuk perangkat keras.
* `app.py` : Berkas sentral *backend* Flask dan perhitungan Regresi Linear.
* `raspi_hardware_controller.py` : Menangani komunikasi data serial dari kabel USB ESP32 ke dalam *Database* MySQL.
* `/templates/` : Kumpulan antarmuka visual HTML (*Frontend*).
* `/static/` : Aset desain visual, CSS, dan skrip *browser* pendukung.

---
**Catatan untuk Pengembang:** Jika Anda mengembangkan sistem ini di komputer baru, pastikan untuk selalu menyesuaikan koneksi *user* dan *password* MySQL di dalam *file* konfigurasi agar aplikasi Flask tidak mengalami kegagalan akses (*Access Denied*).