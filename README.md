# 🚗 Smart Parking System

Sistem *Smart Parking* berbasis *Internet of Things* (IoT) terintegrasi yang dirancang menggunakan mikrokontroler ESP32 (Protokol Komunikasi ESP-NOW) dan Raspberry Pi sebagai *server* pusat. Sistem ini dilengkapi dengan algoritma Kecerdasan Buatan untuk klasifikasi dan prediksi kepadatan kendaraan.

---

## 📁 Struktur Repository

Repository ini dibagi menjadi **3 bagian utama** yang dikerjakan oleh anggota tim secara terpisah:

| Folder | Deskripsi | Penanggung Jawab |
|---|---|---|
| [`Website/`](./Website/) | Backend Flask, Dashboard Web, Prediksi Regresi Linear | Joko Febrianto |
| [`Klasifikasi/`](./Klasifikasi/) | Model Machine Learning untuk klasifikasi status slot parkir | Fariz Hadi Pamungkas |
| [`Monitoring_Slot/`](./Monitoring_Slot/) | Kode ESP32 & sensor untuk monitoring slot parkir | Muhamad Ikhsan |

> Lihat `README.md` di dalam masing-masing folder untuk panduan setup dan menjalankan bagian tersebut.

---
## 👥 Tim Pengembang

| Nama | Bagian |
|---|---|
| Joko Febrianto | Website / Backend Flask |
| Fariz Hadi Pamungkas | Klasifikasi |
| Muhamad Ikhsan | Monitoring Slot |

---

## 📌 Cara Berkontribusi (untuk Anggota Tim)

1. **Clone** repository ini:
   ```bash
   git clone https://github.com/weterhans/smartparking.git
   ```
2. Masuk ke folder bagian Anda, misalnya:
   ```bash
   cd smartparking/Klasifikasi
   ```
3. Kerjakan kode Anda di dalam folder tersebut
4. **Commit & Push** perubahan:
   ```bash
   git add Klasifikasi/
   git commit -m "feat(klasifikasi): tambah model klasifikasi SVM"
   git push origin main
   ```

> ⚠️ **Penting**: Hanya lakukan perubahan di dalam folder bagian Anda sendiri untuk menghindari konflik.

---

*Project Skripsi – Sistem Smart Parking IoT*
