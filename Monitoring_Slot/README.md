# 📡 Monitoring Slot – Smart Parking System

Folder ini berisi kode untuk bagian **Monitoring Slot** pada sistem Smart Parking.

## Deskripsi

Bagian Monitoring Slot bertanggung jawab untuk:
- Membaca data dari sensor ultrasonik (HC-SR04) melalui ESP32
- Memonitor status slot parkir secara real-time
- Mengirimkan data ke server pusat (Raspberry Pi / Backend Flask)

## Struktur Folder (Rencana)

```
Monitoring_Slot/
├── esp32/            # Source code Arduino (.ino) untuk ESP32
│   ├── slave_sensor/ # Node sensor (ESP32 Slave)
│   └── master_gateway/ # Node gateway (ESP32 Master)
├── src/              # Script Python pendukung (jika ada)
├── docs/             # Dokumentasi & wiring diagram
└── README.md
```

## Setup & Cara Menjalankan

> 📌 Bagian ini akan diisi oleh anggota tim yang bertanggung jawab.

**Hardware yang dibutuhkan:**
- ESP32 (minimal 2 unit: 1 Master, 1+ Slave)
- Sensor Ultrasonik HC-SR04
- Modul RFID / NFC
- Motor Servo

**Software:**
- Arduino IDE (dengan board ESP32 terinstal)

```bash
# Flash ESP32 menggunakan Arduino IDE
# Buka file .ino yang sesuai dan tekan Upload
```

## Anggota Tim

- **Nama**: *(isi nama)*
- **Bagian**: Monitoring Slot / Hardware

---
*Folder ini adalah bagian dari project skripsi Smart Parking System.*
