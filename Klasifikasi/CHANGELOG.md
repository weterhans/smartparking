# Changelog

Semua perubahan signifikan pada proyek ini didokumentasikan di file ini.

Format mengikuti [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
dan proyek ini mengikuti [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.0.0] — 2025

### Ditambahkan
- Filter **REMA (Regularized Exponential Moving Average)** menggantikan EMA pada pipeline sinyal LiDAR
  - Parameter baru `REMA_ALPHA` (kecepatan respons) dan `REMA_LAMBDA` (kekuatan regularisasi lag)
  - Field `jarakRemaState` pada struct `LidarData` untuk menyimpan state internal EMA
- Dokumentasi rinci perbedaan v2 → v3 di header file

### Diubah
- `EMA_LAG_KOMPENSASI_US` diturunkan dari **14.000 µs** → **5.000 µs**
  - REMA memiliki lag residual ~5 ms per transisi (vs EMA ~14 ms)
- Semua kode selain filter identik dengan v2.0

### Tetap Sama (dari v2.0)
- Dataset referensi 75 sampel, 8 fitur, 5 kelas
- Bobot FWkNN: `[0.5, 2.0, 1.0, 1.0, 1.5, 1.2, 1.0, 1.0]`
- Nilai K = 3
- Web Monitor (WebSocket)
- Integrasi ESP-NOW
- Tampilan LCD 20×4
- Mitigasi bacaan kaca (LKG)

---

## [2.0.0] — 2025

### Ditambahkan
- **Buffer siluet bertimestamp** (`SampelSiluet.waktu_us`) untuk rekonstruksi spasial akurat
- **Frame parser TF-Luna** yang benar: validasi header (0x59 0x59) + checksum byte
- **Kalibrasi** dengan validasi frame penuh
- **Deteksi arah salah**: kendaraan melintas dari S2 ke S1 (arah berlawanan) diabaikan
- **Mitigasi kaca** (LKG — Last Known Good): saat laser mengenai kaca dan mengembalikan 0, sistem menggunakan pembacaan valid terakhir
- **Anti-flicker exit** (`keluar_debounce`) untuk stabilisasi sinyal keluar
- **Force-trigger S2** saat kendaraan terdeteksi S1 (timeout 5 detik)
- **ESP-NOW**: Pengiriman hasil klasifikasi ke ESP32 penerima via ESP-NOW
- **Web Monitor** dengan dashboard WebSocket real-time
- **LCD 20×4** dengan tampilan detail (kelas, panjang, tinggi, siluet, kecepatan)

### Diubah
- Filter sinyal dari rata-rata sederhana ke **EMA (Exponential Moving Average)**
  - Parameter: `ALPHA_FILTER = 0.50`, `EMA_LAG_KOMPENSASI_US = 14000`
- Sampling berhenti saat sensor S2 terpicu (mengurangi distorsi ekor kendaraan)
- Perhitungan kecepatan lebih robust dengan guard `v_keluar`
- Reset yang aman: preservasi offset kalibrasi setelah reset

### Diperbaiki
- Rekonstruksi spasial tidak akurat pada v1 akibat tidak ada timestamp
- Parser TF-Luna yang tidak memvalidasi header dan checksum

---

## [1.0.0] — 2024

### Rilis Awal
- Implementasi dasar KNN (tanpa bobot) dengan K=3
- Pembacaan dua sensor TF-Luna via UART
- Klasifikasi 5 kelas kendaraan
- Output via Serial Monitor Arduino

---

## Varian Eksperimental

### [tanpa-filter-panjang]
- Berdasarkan v2.0, tanpa filter panjang kendaraan
- Digunakan untuk analisis sensitivitas terhadap filter panjang
- File: `firmware/vehicle_tanpa_filter_panjang/vehicle_tanpa_filter_panjang.ino`

### [tes-tfluna]
- Sketch sederhana untuk pengujian koneksi dan pembacaan sensor TF-Luna
- File: `firmware/tes_tfluna/tes_tfluna.ino`
