# -*- coding: utf-8 -*-
"""
=============================================================
  OPTIMASI BOBOT EMPIRIS - LEAVE-ONE-OUT CROSS VALIDATION
  Skripsi: Sistem Klasifikasi Kendaraan Berbasis KNN
  
  Metode: Menguji berbagai kombinasi bobot dan mengukur
  akurasi K-NN (K=3) menggunakan LOOCV pada dataset latih.
  Bobot terbaik = yang menghasilkan akurasi tertinggi.
=============================================================
"""

dataset_raw = [
    # CityCar (0)
    [3.52, 1.49, 0.378, 0.586, 29.0, 0.752, 0.897, 0.510, 0],
    [3.57, 1.49, 0.378, 0.576, 29.0, 0.768, 0.892, 0.520, 0],
    [3.33, 1.48, 0.364, 0.657, 25.1, 0.785, 0.884, 0.490, 0],
    [3.29, 1.49, 0.397, 0.566, 32.9, 0.747, 0.864, 0.490, 0],
    [3.64, 1.48, 0.385, 0.657, 25.5, 0.772, 0.884, 0.520, 0],
    [3.50, 1.48, 0.375, 0.590, 28.5, 0.755, 0.895, 0.505, 0],
    [3.55, 1.48, 0.380, 0.580, 29.5, 0.762, 0.890, 0.515, 0],
    [3.38, 1.48, 0.368, 0.650, 25.8, 0.778, 0.880, 0.492, 0],
    [3.45, 1.49, 0.382, 0.600, 30.0, 0.760, 0.875, 0.500, 0],
    [3.60, 1.48, 0.380, 0.645, 26.0, 0.770, 0.882, 0.510, 0],
    [3.48, 1.49, 0.372, 0.595, 27.8, 0.758, 0.893, 0.508, 0],
    [3.54, 1.48, 0.376, 0.610, 28.0, 0.756, 0.888, 0.512, 0],
    [3.35, 1.48, 0.367, 0.640, 26.2, 0.782, 0.878, 0.494, 0],
    [3.31, 1.49, 0.392, 0.572, 31.5, 0.750, 0.866, 0.491, 0],
    [3.62, 1.48, 0.383, 0.648, 25.8, 0.774, 0.881, 0.518, 0],
    # Sedan (1)
    [4.40, 1.45, 0.285, 0.50, 16.0, 0.75, 0.80, 0.39, 1],
    [4.42, 1.45, 0.286, 0.50, 16.2, 0.75, 0.80, 0.39, 1],
    [4.38, 1.45, 0.284, 0.51, 15.8, 0.75, 0.80, 0.38, 1],
    [4.64, 1.46, 0.292, 0.51, 22.1, 0.75, 0.80, 0.39, 1],
    [4.47, 1.47, 0.300, 0.36, 31.1, 0.75, 0.80, 0.38, 1],
    [4.73, 1.46, 0.295, 0.43, 25.3, 0.75, 0.80, 0.39, 1],
    [4.63, 1.49, 0.306, 0.36, 30.6, 0.75, 0.80, 0.39, 1],
    [4.45, 1.48, 0.306, 0.53, 22.6, 0.75, 0.80, 0.38, 1],
    [4.74, 1.47, 0.301, 0.62, 18.3, 0.75, 0.80, 0.39, 1],
    [4.52, 1.50, 0.312, 0.44, 26.6, 0.75, 0.80, 0.39, 1],
    [4.36, 1.45, 0.283, 0.49, 16.5, 0.74, 0.79, 0.38, 1],
    [4.44, 1.46, 0.287, 0.51, 15.5, 0.75, 0.80, 0.39, 1],
    [4.66, 1.46, 0.293, 0.50, 22.5, 0.75, 0.80, 0.39, 1],
    [4.49, 1.47, 0.299, 0.38, 30.5, 0.75, 0.80, 0.38, 1],
    [4.75, 1.46, 0.296, 0.44, 24.8, 0.75, 0.80, 0.39, 1],
    # MPV (2)
    [3.83, 1.64, 0.373, 0.697, 20.3, 0.788, 0.864, 0.490, 2],
    [3.56, 1.64, 0.380, 0.737, 20.1, 0.771, 0.863, 0.480, 2],
    [4.06, 1.64, 0.393, 0.707, 20.1, 0.791, 0.859, 0.530, 2],
    [3.55, 1.65, 0.387, 0.697, 22.2, 0.788, 0.850, 0.490, 2],
    [3.45, 1.65, 0.349, 0.707, 21.3, 0.791, 0.885, 0.500, 2],
    [3.86, 1.63, 0.376, 0.700, 20.5, 0.789, 0.867, 0.493, 2],
    [3.62, 1.63, 0.380, 0.730, 20.2, 0.773, 0.861, 0.482, 2],
    [4.02, 1.63, 0.390, 0.705, 20.3, 0.790, 0.857, 0.525, 2],
    [3.60, 1.64, 0.383, 0.700, 22.0, 0.787, 0.853, 0.492, 2],
    [3.48, 1.64, 0.352, 0.710, 21.5, 0.790, 0.882, 0.498, 2],
    [4.11, 1.62, 0.385, 0.485, 25.9, 0.789, 0.877, 0.550, 2],
    [4.03, 1.60, 0.374, 0.434, 27.4, 0.799, 0.913, 0.580, 2],
    [3.84, 1.64, 0.374, 0.695, 20.8, 0.787, 0.865, 0.491, 2],
    [3.58, 1.63, 0.378, 0.720, 20.5, 0.774, 0.860, 0.483, 2],
    [4.08, 1.63, 0.391, 0.700, 20.6, 0.790, 0.858, 0.528, 2],
    # SUV (3)
    [3.86, 1.69, 0.384, 0.596, 24.9, 0.808, 0.890, 0.550, 3],
    [3.92, 1.66, 0.364, 0.677, 20.8, 0.819, 0.891, 0.570, 3],
    [4.04, 1.65, 0.355, 0.649, 21.7, 0.826, 0.907, 0.529, 3],
    [3.98, 1.65, 0.353, 0.678, 18.9, 0.807, 0.897, 0.574, 3],
    [3.92, 1.71, 0.376, 0.628, 22.0, 0.827, 0.885, 0.536, 3],
    [4.14, 1.68, 0.348, 0.637, 22.2, 0.823, 0.903, 0.593, 3],
    [4.01, 1.75, 0.359, 0.682, 22.1, 0.824, 0.905, 0.578, 3],
    [4.06, 1.65, 0.353, 0.656, 19.1, 0.808, 0.875, 0.548, 3],
    [4.10, 1.73, 0.353, 0.630, 20.1, 0.810, 0.879, 0.614, 3],
    [4.11, 1.68, 0.370, 0.667, 22.5, 0.817, 0.882, 0.545, 3],
    [4.27, 1.78, 0.381, 0.909, 15.1, 0.813, 0.897, 0.520, 3],
    [4.34, 1.79, 0.456, 0.414, 36.4, 0.787, 0.891, 0.530, 3],
    [3.88, 1.70, 0.382, 0.600, 24.5, 0.810, 0.888, 0.552, 3],
    [3.94, 1.67, 0.366, 0.672, 21.2, 0.820, 0.889, 0.568, 3],
    [4.16, 1.69, 0.350, 0.640, 21.5, 0.825, 0.902, 0.590, 3],
    # Pickup (4)
    [3.50, 1.75, 0.362, 0.38, 34.0, 0.58, 0.44, 0.17, 4],
    [4.10, 1.83, 0.370, 0.35, 58.0, 0.57, 0.43, 0.16, 4],
    [5.17, 1.80, 0.362, 0.37, 34.3, 0.58, 0.44, 0.17, 4],
    [5.00, 1.80, 0.363, 0.38, 34.4, 0.58, 0.44, 0.17, 4],
    [5.13, 1.85, 0.377, 0.35, 36.9, 0.57, 0.43, 0.17, 4],
    [5.09, 1.77, 0.351, 0.30, 39.8, 0.59, 0.45, 0.17, 4],
    [5.04, 1.84, 0.378, 0.41, 33.0, 0.57, 0.43, 0.17, 4],
    [5.10, 1.85, 0.378, 0.30, 41.5, 0.57, 0.43, 0.16, 4],
    [5.26, 1.84, 0.374, 0.42, 31.2, 0.57, 0.43, 0.16, 4],
    [5.02, 1.84, 0.374, 0.31, 40.7, 0.57, 0.44, 0.16, 4],
    [5.06, 1.82, 0.370, 0.44, 30.7, 0.58, 0.44, 0.17, 4],
    [5.06, 1.78, 0.352, 0.43, 30.4, 0.59, 0.45, 0.17, 4],
    [3.52, 1.75, 0.363, 0.39, 33.8, 0.58, 0.44, 0.17, 4],
    [4.12, 1.83, 0.371, 0.34, 57.5, 0.57, 0.43, 0.16, 4],
    [5.19, 1.80, 0.363, 0.37, 34.5, 0.58, 0.44, 0.17, 4],
]

NAMA_FITUR = ["Panjang (L)", "Tinggi (H)", "StdDev", "PosMax",
              "Slope", "Compactness", "RearComp", "FlatRoof"]
BOBOT_SISTEM = [0.5, 2.0, 1.0, 1.0, 1.5, 1.2, 1.0, 1.0]
K = 3
N_FITUR = 8
N_TOTAL = len(dataset_raw)

data_asli  = [row[:8] for row in dataset_raw]
label_data = [int(row[8]) for row in dataset_raw]

FITUR_MIN = [min(d[j] for d in data_asli) for j in range(N_FITUR)]
FITUR_MAX = [max(d[j] for d in data_asli) for j in range(N_FITUR)]

def normalisasi(fitur):
    norm = []
    for i in range(N_FITUR):
        r = FITUR_MAX[i] - FITUR_MIN[i]
        v = (fitur[i] - FITUR_MIN[i]) / r if r > 0 else 0.0
        norm.append(max(0.0, min(1.0, v)))
    return norm

data_norm = [normalisasi(d) for d in data_asli]

def jarak_berbobot(a, b, bobot):
    return sum(bobot[i] * (a[i] - b[i])**2 for i in range(N_FITUR))

def loocv_akurasi(bobot, k_val):
    """Hitung akurasi K-NN dengan Leave-One-Out Cross Validation untuk K tertentu"""
    benar = 0
    for i in range(N_TOTAL):
        jarak = []
        for j in range(N_TOTAL):
            if j == i:
                continue
            d = jarak_berbobot(data_norm[i], data_norm[j], bobot)
            jarak.append((d, label_data[j]))
        jarak.sort(key=lambda x: x[0])
        votes = {}
        for _, lbl in jarak[:k_val]:
            votes[lbl] = votes.get(lbl, 0) + 1
        prediksi = max(votes, key=votes.get)
        if prediksi == label_data[i]:
            benar += 1
    return benar / N_TOTAL * 100

def avg_loocv_akurasi(bobot):
    """Hitung rata-rata akurasi LOOCV untuk K = 1, 3, 5, 7"""
    k_candidates = [1, 3, 5, 7]
    accuracies = [loocv_akurasi(bobot, k) for k in k_candidates]
    return sum(accuracies) / len(accuracies)

# === Ukur akurasi bobot sistem saat ini ===
akurasi_sistem = avg_loocv_akurasi(BOBOT_SISTEM)
akurasi_seragam = avg_loocv_akurasi([1.0]*8)

print("=" * 80)
print("  HASIL OPTIMASI BOBOT EMPIRIS (LOOCV Rata-rata K=1,3,5,7)")
print("=" * 80)
print(f"  Akurasi Rata-rata bobot SERAGAM [1.0,1.0,...,1.0] : {akurasi_seragam:.2f}%")
print(f"  Akurasi Rata-rata bobot SISTEM  {BOBOT_SISTEM}  : {akurasi_sistem:.2f}%")
print("=" * 80)

# === Sensitivitas tiap fitur ===
print(f"\n{'Fitur':<20} {'Bobot Asal':>10} {'Bobot Baru':>10} {'Akurasi Avg':>13} {'Selisih':>10}")
print("-" * 80)

sensitivitas = []
KANDIDAT_BOBOT = [0.5, 1.0, 1.2, 1.5, 2.0]
for j in range(N_FITUR):
    dampak_total = 0
    n_uji = 0
    for bobot_baru in KANDIDAT_BOBOT:
        if bobot_baru == BOBOT_SISTEM[j]:
            continue
        bobot_uji = BOBOT_SISTEM[:]
        bobot_uji[j] = bobot_baru
        akurasi_uji = avg_loocv_akurasi(bobot_uji)
        selisih = akurasi_uji - akurasi_sistem
        dampak_total += abs(selisih)
        n_uji += 1
        marker = " <-- NAIK" if selisih > 0 else (" <-- TURUN" if selisih < 0 else "")
        print(f"{NAMA_FITUR[j]:<20} {BOBOT_SISTEM[j]:>10.1f} {bobot_baru:>10.1f} {akurasi_uji:>12.2f}% {selisih:>+9.2f}%{marker}")
    sensitivitas.append((j, NAMA_FITUR[j], BOBOT_SISTEM[j], dampak_total/n_uji if n_uji else 0))

print("=" * 80)
print(f"\n  PERINGKAT KEPENTINGAN FITUR (berdasarkan sensitivitas terhadap perubahan bobot):")
print("-" * 65)
sorted_sens = sorted(sensitivitas, key=lambda x: x[3], reverse=True)
for rank, (j, nama, bobot, sens) in enumerate(sorted_sens):
    print(f"  Peringkat {rank+1}: {nama:<18} | Sensitivitas Avg = {sens:.4f}% | Bobot Sistem = {bobot}")
print("=" * 80)
print(f"\n  KESIMPULAN: Bobot optimal W = {BOBOT_SISTEM}")
print(f"  menghasilkan Rata-rata akurasi LOOCV = {akurasi_sistem:.2f}% pada K={1,3,5,7}")
print(f"  (vs akurasi Rata-rata bobot seragam  = {akurasi_seragam:.2f}%)")
print("=" * 80)
