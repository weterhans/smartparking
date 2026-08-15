# Script Analisis — Edge AI Vehicle Classifier

Direktori ini berisi script Python untuk menganalisis dan memvalidasi hasil klasifikasi sistem.

---

## 📂 Isi Direktori

| File | Deskripsi |
|---|---|
| `confusion_matrix_f1.py` | Membuat confusion matrix dan menghitung F1 Score per kelas |
| `hitung_fdr.py` | Optimasi bobot FWkNN menggunakan Leave-One-Out Cross Validation (LOOCV) |
| `analisis_misklasifikasi.py` | Analisis detail kasus misklasifikasi dengan 3 tetangga terdekat |
| `requirements.txt` | Daftar dependensi Python |

---

## 🚀 Cara Menjalankan

### 1. Install Dependensi

```bash
pip install -r requirements.txt
```

Atau menggunakan virtual environment (direkomendasikan):

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
```

### 2. Jalankan Script

```bash
# Buat confusion matrix + laporan F1 Score
python confusion_matrix_f1.py

# Analisis optimasi bobot dengan LOOCV
python hitung_fdr.py

# Analisis kasus misklasifikasi secara detail
python analisis_misklasifikasi.py
```

---

## 📊 Deskripsi Script

### `confusion_matrix_f1.py`

Menghitung dan memvisualisasikan confusion matrix dari 24 sampel pengujian.

**Output:**
- Gambar confusion matrix berwarna (`.png`)
- Laporan F1 Score, Precision, Recall per kelas
- File Word (`.docx`) berisi tabel metrik (opsional, butuh `python-docx`)

**Kelas yang diuji:**
```python
["City Car", "Sedan", "MPV", "SUV", "Pickup"]
```

---

### `hitung_fdr.py`

Menggunakan LOOCV (Leave-One-Out Cross Validation) untuk mencari kombinasi bobot fitur FWkNN yang menghasilkan akurasi tertinggi.

**Metode:**
- Menguji berbagai kombinasi bobot secara grid search
- Mengukur akurasi KNN (K=3) untuk setiap kombinasi
- Melaporkan bobot terbaik + akurasi LOOCV

**Dataset:** 75 sampel referensi (identik dengan yang tertanam di firmware)

---

### `analisis_misklasifikasi.py`

Menampilkan detail analisis mengapa kendaraan tertentu salah diklasifikasikan.

**Output per kasus misklasifikasi:**
- 3 tetangga terdekat (dengan jarak masing-masing)
- Perbandingan nilai fitur
- Alasan kualitatif misklasifikasi

---

## 📦 Dependensi

Lihat `requirements.txt` untuk versi lengkap. Dependensi utama:

| Package | Kegunaan |
|---|---|
| `numpy` | Komputasi numerik (jarak Euclidean, normalisasi) |
| `matplotlib` | Visualisasi confusion matrix dan grafik |
| `python-docx` | Ekspor tabel ke format Word `.docx` |

---

## 📝 Catatan

- Dataset dalam script Python **identik** dengan dataset yang tertanam di firmware (`vehicle_v3.ino`)
- Normalisasi menggunakan batas global yang sama: `FITUR_MIN` dan `FITUR_MAX`
- Bobot FWkNN yang digunakan: `[0.5, 2.0, 1.0, 1.0, 1.5, 1.2, 1.0, 1.0]`
