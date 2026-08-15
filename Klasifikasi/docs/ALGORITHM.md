# Dokumentasi Algoritma — FWkNN & Filter REMA

Dokumen ini menjelaskan secara mendalam dua algoritma inti sistem: **Feature-Weighted K-Nearest Neighbor (FWkNN)** dan **Regularized Exponential Moving Average (REMA)**.

---

## 1. Pipeline Keseluruhan

```
Raw LiDAR (UART) → [REMA Filter] → Profil Siluet → [Ekstrasi Fitur] → [FWkNN] → Label Kelas
```

---

## 2. Filter REMA (Regularized Exponential Moving Average)

### 2.1 Latar Belakang

Sensor TF-Luna menghasilkan pembacaan yang mengandung noise. Filter EMA (Exponential Moving Average) standar mampu menghaluskan noise, namun memiliki **lag (keterlambatan)** saat terjadi transisi tajam (kendaraan masuk/keluar). Lag ini menyebabkan error pada estimasi panjang kendaraan.

**REMA** mengatasi masalah ini dengan menambahkan kompensasi lag menggunakan turunan pertama dari state EMA.

### 2.2 Rumus REMA

**Langkah 1 — Hitung State EMA Internal:**
```
State[n] = α × raw[n] + (1-α) × State[n-1]
```

**Langkah 2 — Kompensasi Lag:**
```
Output[n] = State[n] + λ × (State[n] - State[n-1])
```

Dimana:
- `raw[n]`   = pembacaan jarak mentah dari sensor (cm)
- `State[n]` = state internal EMA
- `α`        = `REMA_ALPHA` = 0.50 (kecepatan respons)
- `λ`        = `REMA_LAMBDA` = 0.40 (kekuatan kompensasi lag)
- `Output[n]`= jarak mulus terkomensasi yang digunakan sistem

### 2.3 Perbandingan EMA vs REMA

| Metrik | EMA (v2) | REMA (v3) |
|---|---|---|
| Lag per transisi | ~14 ms | ~5 ms |
| Overshoot | Tidak ada | Sangat kecil (λ < 0.5) |
| Kompleksitas komputasi | O(1) | O(1) |
| Parameter tambahan | — | λ (REMA_LAMBDA) |

### 2.4 Implementasi C++ (di firmware)

```cpp
// Hitung state EMA internal
lidar.jarakRemaState = REMA_ALPHA * rawDist
                     + (1.0f - REMA_ALPHA) * lidar.jarakRemaState;

// Kompensasi lag → output REMA
float prevState = lidar.jarakRemaState_prev; // state sebelumnya
lidar.jarakMulus = lidar.jarakRemaState
                 + REMA_LAMBDA * (lidar.jarakRemaState - prevState);
```

---

## 3. Rekonstruksi Spasial Siluet

### 3.1 Konsep

Sensor LiDAR menghasilkan sampel **temporal** (berbasis waktu). Untuk mendapatkan profil **spasial** (berbasis posisi), diperlukan informasi kecepatan kendaraan.

```
Posisi_cm = (waktu_us - waktu_masuk_us) / 1e6 × kecepatan_cms
```

### 3.2 Estimasi Kecepatan

Kecepatan diestimasi dari selisih waktu antara kendaraan mencapai S1 dan S2:

```
t_s12 = waktuMasukS2 - waktuMasukS1     [µs]
v_masuk = JARAK_ANTAR_SENSOR_CM / (t_s12 / 1e6)   [cm/s]
```

Kecepatan keluar dihitung dari S2:
```
t_s2 = waktuKeluarS2 - waktuMasukS2
v_keluar = JARAK_ANTAR_SENSOR_CM / (t_s2 / 1e6)
```

Kecepatan final = rata-rata v_masuk dan v_keluar.

### 3.3 Kompensasi Lag

Karena filter REMA memiliki lag residual ~5 ms, timestamp deteksi masuk/keluar dikompensasi:

```
t_efektif_masuk  = t_raw_masuk  - EMA_LAG_KOMPENSASI_US   (= 5000 µs)
t_efektif_keluar = t_raw_keluar + EMA_LAG_KOMPENSASI_US
```

---

## 4. Ekstraksi 8 Fitur

Dari profil siluet N sampel `(posisi_cm, tinggi_cm)`, diekstraksi 8 fitur:

### Fitur 0: Panjang (meter)

```
panjang = (posisi_sampel_terakhir - posisi_sampel_pertama) / 100
```

### Fitur 1: Tinggi (meter)

```
tinggi = max(tinggi_cm semua sampel) / 100
```

### Fitur 2: StdDev (Standar Deviasi)

```
stddev = std(tinggi_cm semua sampel) / tinggi_cm_max
```

Mengukur keragaman variasi profil — sedan memiliki stddev rendah (profil landai), pickup memiliki stddev tinggi (bak terbuka).

### Fitur 3: PosMax (Posisi Relatif Titik Tertinggi)

```
idx_max    = argmax(tinggi_cm)
posMax     = idx_max / (N - 1)    # 0.0 = depan, 1.0 = belakang
```

### Fitur 4: Slope (Derajat Kemiringan Atap)

Sudut kemiringan dari atap ke bagian belakang kendaraan (persentil 75% → 95% posisi):

```
Δy = rata-rata tinggi[75%-95%] - rata-rata tinggi[50%-75%]
Δx = jarak_cm × 0.20
slope° = atan2(|Δy|, Δx) × 180/π
```

### Fitur 5: Compactness (Kerapatan Bodi)

```
area_terisi    = sum(tinggi_cm semua sampel) × resolusi_cm
area_bounding  = panjang_cm × tinggi_cm_max
compactness    = area_terisi / area_bounding
```

### Fitur 6: RearComp (Compactness Bagian Belakang)

Sama dengan Compactness, namun hanya untuk 40% bagian belakang kendaraan:

```
sampel_belakang = sampel[N×0.6 : N]
rearComp        = compactness(sampel_belakang)
```

Membedakan MPV (atap rata, rearComp tinggi) dari Pickup (bak terbuka, rearComp rendah).

### Fitur 7: FlatRoof (Skor Atap Datar)

```
sampel_tengah  = sampel[N×0.2 : N×0.8]
flatRoof       = 1.0 - (std(tinggi tengah) / tinggi_max)
```

Nilai mendekati 1.0 = atap datar (City Car, MPV), nilai rendah = atap cembung/miring (Sedan, Pickup).

---

## 5. Normalisasi Min-Max

Sebelum masuk ke KNN, setiap fitur dinormalisasi ke rentang [0, 1]:

```
fitur_norm[i] = (fitur[i] - FITUR_MIN[i]) / (FITUR_MAX[i] - FITUR_MIN[i])
```

Batas normalisasi global (dari seluruh dataset latih):

| Fitur | Min | Max |
|---|---|---|
| Panjang | 3.20 m | 5.46 m |
| Tinggi | 1.28 m | 2.05 m |
| StdDev | 0.251 | 0.460 |
| PosMax | 0.23 | 1.03 |
| Slope | 14.6° | 58.0° |
| Compactness | 0.51 | 0.96 |
| RearComp | 0.39 | 1.00 |
| FlatRoof | 0.14 | 0.79 |

---

## 6. Feature-Weighted KNN (FWkNN)

### 6.1 Rumus Jarak Euclidean Terbobot

```
d(q, r) = sqrt( Σᵢ [ w_i × (q_i_norm - r_i_norm)² ] )
```

Dimana:
- `q` = vektor fitur kendaraan uji (query)
- `r` = vektor fitur salah satu data referensi
- `w_i` = bobot fitur ke-i
- `q_i_norm`, `r_i_norm` = nilai fitur yang sudah dinormalisasi

### 6.2 Bobot Fitur

| Fitur | Bobot | Alasan |
|---|:---:|---|
| Panjang | 0.5 | Overlap tinggi SUV/MPV, diturunkan |
| **Tinggi** | **2.0** | Pembeda utama antar kelas, tertinggi |
| StdDev | 1.0 | Standar |
| PosMax | 1.0 | Standar |
| Slope | 1.5 | Pembeda bentuk kap sedan vs MPV |
| Compactness | 1.2 | Pembeda bodi boxy vs melengkung |
| RearComp | 1.0 | Standar |
| FlatRoof | 1.0 | Standar |

### 6.3 Proses Klasifikasi

1. Hitung jarak `d(q, r_i)` ke semua 75 data referensi
2. Urutkan jarak secara ascending
3. Ambil K=3 tetangga terdekat
4. Voting mayoritas → label kelas dengan suara terbanyak menjadi hasil klasifikasi

### 6.4 Implementasi C++

```cpp
// Hitung jarak ke semua data referensi
for (int i = 0; i < JUMLAH_DATA; i++) {
    float dist = 0.0f;
    for (int j = 0; j < JUMLAH_FITUR; j++) {
        float norm_q = (fitur[j] - FITUR_MIN[j]) / (FITUR_MAX[j] - FITUR_MIN[j]);
        float norm_r = (dataset[i].fitur[j] - FITUR_MIN[j]) / (FITUR_MAX[j] - FITUR_MIN[j]);
        float diff = norm_q - norm_r;
        dist += BOBOT_FITUR[j] * diff * diff;
    }
    jarak[i] = sqrt(dist);
}

// Sort & voting K=3
// ... (selection sort untuk K terkecil)
```

---

## 7. Optimasi Bobot dengan LOOCV

Bobot `BOBOT_FITUR` ditentukan empiris menggunakan **Leave-One-Out Cross Validation (LOOCV)**:

1. Untuk setiap sampel dalam dataset (N=75):
   - Keluarkan sampel tersebut sebagai data uji
   - Latih KNN dengan sisa 74 sampel
   - Prediksi label sampel yang dikeluarkan
2. Hitung akurasi keseluruhan
3. Ulangi untuk berbagai kombinasi bobot
4. Pilih bobot dengan akurasi LOOCV tertinggi

Script implementasi: [analysis/hitung_fdr.py](../analysis/hitung_fdr.py)
