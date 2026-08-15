# -*- coding: utf-8 -*-
"""
=============================================================
  PLOTTER SEBARAN DATA KNN — SCATTER PLOT MATRIX
  Skripsi: Sistem Klasifikasi Kendaraan Berbasis KNN
  
  CARA PENGGUNAAN:
  1. Jalankan: python plotter_sebaran_knn.py
  2. Ikuti instruksi di terminal untuk memasukkan 8 nilai fitur
     dari kendaraan uji yang ingin divisualisasikan.
  3. Grafik scatter matrix akan tampil dengan lingkaran K.
=============================================================
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ─────────────────────────────────────────────────────────────
#  DATASET — Diambil persis dari vehicle.ino
#  Format: [Panjang, Tinggi, StdDev, PosMax, Slope, Compact, RearComp, FlatRoof]
#  Label: 0=CityCar, 1=Sedan, 2=MPV, 3=SUV, 4=Pickup
# ─────────────────────────────────────────────────────────────
NAMA_FITUR = ["Panjang\n(m)", "Tinggi\n(m)", "StdDev", "PosMax",
              "Slope\n(deg)", "Compact", "RearComp", "FlatRoof"]
NAMA_KELAS = ["City Car", "Sedan", "MPV", "SUV", "Pickup"]
WARNA_KELAS = {
    0: "#3B82F6",   # Biru  — City Car
    1: "#10B981",   # Hijau — Sedan
    2: "#F59E0B",   # Kuning— MPV
    3: "#EF4444",   # Merah — SUV
    4: "#8B5CF6",   # Ungu  — Pickup
}
MARKER_KELAS = {0: "o", 1: "s", 2: "^", 3: "D", 4: "P"}

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

# ─────────────────────────────────────────────────────────────
#  PARAMETER NORMALISASI — Diambil persis dari vehicle.ino
# ─────────────────────────────────────────────────────────────
FITUR_MIN = [3.20, 1.28, 0.251, 0.23, 14.6, 0.51, 0.39, 0.14]
FITUR_MAX = [5.46, 2.05, 0.460, 1.03, 58.0, 0.96, 1.00, 0.79]
BOBOT     = [0.5,  2.0,  1.0,   1.0,  1.5,  1.2,  1.0,  1.0]

# ─────────────────────────────────────────────────────────────
#  FUNGSI NORMALISASI
# ─────────────────────────────────────────────────────────────
def normalisasi(fitur):
    norm = []
    for i in range(8):
        r = FITUR_MAX[i] - FITUR_MIN[i]
        v = (fitur[i] - FITUR_MIN[i]) / r if r > 0 else 0.0
        norm.append(max(0.0, min(1.0, v)))
    return norm

def jarak_berbobot(a, b):
    return sum(BOBOT[i] * (a[i] - b[i])**2 for i in range(8))

# ─────────────────────────────────────────────────────────────
#  SIAPKAN DATA TERSTRUKTUR
# ─────────────────────────────────────────────────────────────
data_asli  = [row[:8] for row in dataset_raw]
label_data = [int(row[8]) for row in dataset_raw]
data_norm  = [normalisasi(d) for d in data_asli]

# ─────────────────────────────────────────────────────────────
#  INPUT TITIK DATA UJI DARI PENGGUNA
# ─────────────────────────────────────────────────────────────
print("=" * 60)
print("  PLOTTER SEBARAN KNN — INPUT DATA UJI")
print("=" * 60)
print("  Masukkan 8 nilai fitur kendaraan uji yang ingin diplot.")
print("  Format: nilai dipisahkan spasi atau koma")
print()
print("  Contoh MPV    : 4.17 1.57 0.399 0.444 29.3 0.810 0.848 0.540")
print("  Contoh SUV    : 4.27 1.78 0.381 0.909 15.1 0.813 0.897 0.520")
print("  Contoh CityCar: 3.65 1.38 0.384 0.424 29.2 0.808 0.824 0.480")
print("  Contoh Sedan  : 4.40 1.45 0.285 0.500 16.0 0.750 0.800 0.390")
print("  Contoh Pickup : 3.50 1.75 0.362 0.380 34.0 0.580 0.440 0.170")
print()
print("  Urutan fitur: [Panjang, Tinggi, StdDev, PosMax, Slope,")
print("                 Compactness, RearComp, FlatRoof]")
print("-" * 60)

while True:
    raw_input_str = input("  Masukkan 8 nilai fitur: ").strip()
    raw_input_str = raw_input_str.replace(",", " ")
    parts = raw_input_str.split()
    if len(parts) == 8:
        try:
            titik_uji_asli = [float(p) for p in parts]
            break
        except ValueError:
            print("  [!] Format salah. Pastikan semua nilai adalah angka.")
    else:
        print(f"  [!] Butuh tepat 8 nilai, Anda memasukkan {len(parts)}. Coba lagi.")

print()
nama_kendaraan = input("  Kelas kendaraan ini (untuk judul grafik, misal: MPV): ").strip()
print()

# ─────────────────────────────────────────────────────────────
#  HITUNG JARAK & URUTKAN
# ─────────────────────────────────────────────────────────────
titik_uji_norm = normalisasi(titik_uji_asli)

jarak_semua = []
for i, dn in enumerate(data_norm):
    j = jarak_berbobot(titik_uji_norm, dn)
    jarak_semua.append((j, i, label_data[i]))

jarak_semua.sort(key=lambda x: x[0])

# Tentukan radius lingkaran untuk K=1,3,5,7
K_list     = [1, 3, 5, 7]
radius_K   = {}  # radius dalam ruang ternormalisasi
for K in K_list:
    # Radius = jarak ke tetangga terjauh dari K tetangga terdekat
    radius_K[K] = jarak_semua[K-1][0]

# Tentukan prediksi untuk setiap K
def voting(jarak_terurut, K):
    votes = [0] * 5
    for _, _, lbl in jarak_terurut[:K]:
        votes[lbl] += 1
    return votes.index(max(votes))

prediksi_K = {K: voting(jarak_semua, K) for K in K_list}

print("=" * 60)
print(f"  Data uji    : {nama_kendaraan}")
print(f"  Fitur       : {[round(x, 3) for x in titik_uji_asli]}")
print("-" * 60)
for K in K_list:
    tetangga = [NAMA_KELAS[jarak_semua[i][2]] for i in range(K)]
    hasil = NAMA_KELAS[prediksi_K[K]]
    print(f"  K={K}: Prediksi = {hasil:<10} | Tetangga: {tetangga}")
print("=" * 60)
print()

# ─────────────────────────────────────────────────────────────
#  PILIH PASANGAN FITUR PENTING UNTUK SUBPLOT
#  Menampilkan 6 pasangan paling informatif dalam grid 2x3
# ─────────────────────────────────────────────────────────────
# Pasangan fitur: (indeks_x, indeks_y)
pasangan_fitur = [
    (0, 1),   # Panjang vs Tinggi
    (0, 4),   # Panjang vs Slope
    (1, 4),   # Tinggi vs Slope
    (1, 5),   # Tinggi vs Compactness
    (0, 6),   # Panjang vs RearComp
    (3, 7),   # PosMax vs FlatRoof
]

NAMA_FITUR_BERSIH = ["Panjang (m)", "Tinggi (m)", "StdDev",
                     "PosMax", "Slope (deg)", "Compactness",
                     "RearComp", "FlatRoof"]

# ─────────────────────────────────────────────────────────────
#  BUAT SUBPLOT MATRIX (2 baris x 3 kolom)
#  Setiap subplot menampilkan 1 pasangan fitur + lingkaran K
# ─────────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 3, figsize=(16, 10))
fig.patch.set_facecolor("#F8FAFC")
fig.suptitle(
    f"Sebaran Data KNN — Data Uji: {nama_kendaraan}\n"
    f"Fitur: {[round(x,2) for x in titik_uji_asli]}",
    fontsize=13, fontweight="bold", color="#1E293B", y=1.01
)

# Warna & style lingkaran per K
WARNA_LINGKARAN = {1: "#FCD34D", 3: "#34D399", 5: "#60A5FA", 7: "#F87171"}
STYLE_LINGKARAN = {1: "--", 3: "-", 5: "-.", 7: ":"}

for idx, (fx, fy) in enumerate(pasangan_fitur):
    ax = axes[idx // 3][idx % 3]
    ax.set_facecolor("#F1F5F9")

    # --- Plot semua titik dataset ---
    for label in range(5):
        xs = [data_asli[i][fx] for i in range(len(data_asli)) if label_data[i] == label]
        ys = [data_asli[i][fy] for i in range(len(data_asli)) if label_data[i] == label]
        ax.scatter(xs, ys,
                   color=WARNA_KELAS[label],
                   marker=MARKER_KELAS[label],
                   s=60, alpha=0.75,
                   edgecolors="white", linewidths=0.8,
                   label=NAMA_KELAS[label], zorder=3)

    # --- Tandai K tetangga terdekat dari setiap K ---
    # Tandai tetangga K=7 dengan lingkaran hitam tipis
    for k_rank, (_, i_data, lbl) in enumerate(jarak_semua[:7]):
        ax.scatter(data_asli[i_data][fx], data_asli[i_data][fy],
                   color=WARNA_KELAS[lbl], marker=MARKER_KELAS[lbl],
                   s=130, edgecolors="#1E293B", linewidths=1.8,
                   zorder=4)

    # --- Gambar lingkaran radius K (dalam ruang data asli, approx) ---
    # Karena lingkaran dihitung dari jarak berbobot di ruang ternormalisasi,
    # kita konversi radius ke skala data asli untuk sumbu fx dan fy
    range_x = FITUR_MAX[fx] - FITUR_MIN[fx]
    range_y = FITUR_MAX[fy] - FITUR_MIN[fy]

    for K in K_list:
        # Radius approx di sumbu x dan y dari ruang ternormalisasi
        r_norm = np.sqrt(radius_K[K] / (BOBOT[fx] + BOBOT[fy]))
        rx = r_norm * range_x
        ry = r_norm * range_y

        ellipse = mpatches.Ellipse(
            (titik_uji_asli[fx], titik_uji_asli[fy]),
            width=2*rx, height=2*ry,
            linewidth=1.8,
            edgecolor=WARNA_LINGKARAN[K],
            facecolor="none",
            linestyle=STYLE_LINGKARAN[K],
            zorder=5,
            label=f"K={K} ({NAMA_KELAS[prediksi_K[K]]})"
        )
        ax.add_patch(ellipse)

        # Label K di tepi ellipse
        ax.annotate(
            f"K={K}",
            xy=(titik_uji_asli[fx] + rx * 0.7, titik_uji_asli[fy] + ry),
            fontsize=7, color=WARNA_LINGKARAN[K], fontweight="bold",
            ha="center"
        )

    # --- Titik data uji (bintang merah) ---
    ax.scatter(titik_uji_asli[fx], titik_uji_asli[fy],
               marker="*", s=300,
               color="#DC2626", edgecolors="white", linewidths=1.0,
               zorder=6, label="Data Uji")

    # --- Label sumbu ---
    ax.set_xlabel(NAMA_FITUR_BERSIH[fx], fontsize=9)
    ax.set_ylabel(NAMA_FITUR_BERSIH[fy], fontsize=9)
    ax.tick_params(labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor("#CBD5E1")
    ax.yaxis.grid(True, linestyle="--", color="#CBD5E1", alpha=0.5)
    ax.xaxis.grid(True, linestyle="--", color="#CBD5E1", alpha=0.5)
    ax.set_axisbelow(True)

# ─────────────────────────────────────────────────────────────
#  LEGENDA GLOBAL
# ─────────────────────────────────────────────────────────────
legenda_kelas = [
    mpatches.Patch(color=WARNA_KELAS[i], label=NAMA_KELAS[i]) for i in range(5)
]
bintang = plt.Line2D([0], [0], marker="*", color="w", markerfacecolor="#DC2626",
                     markersize=12, label="Data Uji")
legenda_kelas.append(bintang)

legenda_k = [
    mpatches.Patch(facecolor="none", edgecolor=WARNA_LINGKARAN[K],
                   linestyle=STYLE_LINGKARAN[K],
                   label=f"K={K} -> {NAMA_KELAS[prediksi_K[K]]}")
    for K in K_list
]

fig.legend(handles=legenda_kelas, loc="lower left",
           bbox_to_anchor=(0.01, -0.05), ncol=6,
           fontsize=9, framealpha=0.9, title="Kelas Kendaraan")
fig.legend(handles=legenda_k, loc="lower right",
           bbox_to_anchor=(0.99, -0.05), ncol=4,
           fontsize=9, framealpha=0.9, title="Lingkaran K & Prediksi")

plt.tight_layout()

# ─────────────────────────────────────────────────────────────
#  SIMPAN DAN TAMPILKAN
# ─────────────────────────────────────────────────────────────
nama_file = f"sebaran_knn_{nama_kendaraan.replace(' ', '_').lower()}.png"
plt.savefig(nama_file, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"  Grafik disimpan sebagai: {nama_file}")
plt.show()
print("  Program selesai.")
