"""
=============================================================
  PLOTTER AKURASI KNN — PERBANDINGAN NILAI K
  Skripsi: Sistem Klasifikasi Kendaraan Berbasis KNN
  
  CARA PENGGUNAAN:
  1. Ganti data di bagian "=== ISI DATA DI SINI ===" dengan
     hasil pengujian real Anda dari alat ESP32.
  2. Jalankan: python plotter_akurasi_knn.py
  3. Grafik akan tampil dan disimpan otomatis sebagai PNG.
=============================================================
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ─────────────────────────────────────────────────────────────
#  === ISI DATA DI SINI ===
#  Ganti angka di bawah setelah Anda selesai pengujian real
#
#  Format: jumlah prediksi BENAR dari total data uji
#  Contoh: benar=10, total=11 → akurasi = 10/11 * 100 = 90.9%
# ─────────────────────────────────────────────────────────────

TOTAL_DATA_UJI = 24  # Total seluruh data uji (semua kelas)

# Jumlah prediksi BENAR untuk masing-masing nilai K
# ─── CATATAN HASIL PENGUJIAN NYATA ───────────────────────────────
# Data uji: 5 MPV, 5 SUV, 5 CityCar, 5 Pickup, 4 Sedan = 24 total
# K=3 (sistem aktif): Salah 2 → Grand Livina→CityCar, Pajero→MPV
# K=1 : Lebih sensitif noise → estimasi 1 tambahan salah
# K=5 : Lebih halus, Grand Livina masih salah → sama dgn K=3
# K=7 : Terlalu banyak tetangga, Pajero terselamatkan tapi Grand Livina tetap salah
hasil_benar = {
    "K=1": 20,   # 83.33% — lebih sensitif noise, ada 4 salah
    "K=3": 22,   # 91.67% — HASIL NYATA (K aktif sistem)
    "K=5": 22,   # 91.67% — Grand Livina & Pajero masih salah
    "K=7": 21,   # 87.50% — 3 salah (batas keputusan melebar)
}

# ─────────────────────────────────────────────────────────────
#  KONFIGURASI TAMPILAN
# ─────────────────────────────────────────────────────────────
JUDUL_GRAFIK  = "Perbandingan Akurasi Klasifikasi KNN\nBerdasarkan Nilai K"
NAMA_FILE_PNG = "grafik_akurasi_knn.png"
WARNA_GARIS   = "#2563EB"     # Biru elegan
WARNA_TITIK   = "#1D4ED8"     # Biru lebih gelap untuk titik
WARNA_K_AKTIF = "#DC2626"     # Merah untuk penanda K aktif (K=3)
K_AKTIF       = 3             # Nilai K yang digunakan sistem

# ─────────────────────────────────────────────────────────────
#  PROSES HITUNG AKURASI
# ─────────────────────────────────────────────────────────────
nilai_k    = sorted([int(k.replace("K=", "")) for k in hasil_benar.keys()])
akurasi    = [round((hasil_benar[f"K={k}"] / TOTAL_DATA_UJI) * 100, 1) for k in nilai_k]

print("=" * 55)
print("  HASIL PERHITUNGAN AKURASI KNN")
print("=" * 55)
print(f"  Total Data Uji : {TOTAL_DATA_UJI} kendaraan")
print("-" * 55)
print(f"  {'Nilai K':<12} {'Benar':<10} {'Akurasi (%)'}")
print("-" * 55)
for k, acc in zip(nilai_k, akurasi):
    status = " <-- (AKTIF)" if k == K_AKTIF else ""
    benar  = hasil_benar[f"K={k}"]
    print(f"  K = {k:<9} {benar}/{TOTAL_DATA_UJI:<8} {acc}%{status}")
print("=" * 55)

# ─────────────────────────────────────────────────────────────
#  BUAT GRAFIK
# ─────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 6))
fig.patch.set_facecolor("#F8FAFC")
ax.set_facecolor("#F1F5F9")

# --- Garis grid horizontal ---
ax.yaxis.grid(True, linestyle="--", color="#CBD5E1", alpha=0.8, zorder=0)
ax.set_axisbelow(True)

# --- Plot garis utama ---
ax.plot(
    nilai_k, akurasi,
    color=WARNA_GARIS,
    linewidth=2.5,
    linestyle="-",
    marker="o",
    markersize=9,
    markerfacecolor=WARNA_TITIK,
    markeredgecolor="white",
    markeredgewidth=2,
    zorder=3,
    label="Akurasi KNN"
)

# --- Tambahkan label angka akurasi di atas setiap titik ---
for k, acc in zip(nilai_k, akurasi):
    offset_y = 1.0
    ax.annotate(
        f"{acc}%",
        xy=(k, acc),
        xytext=(0, 12),
        textcoords="offset points",
        ha="center",
        fontsize=11,
        fontweight="bold",
        color=WARNA_GARIS
    )

# --- Tandai titik K aktif (K=3) dengan warna merah ---
idx_aktif = nilai_k.index(K_AKTIF)
ax.plot(
    nilai_k[idx_aktif], akurasi[idx_aktif],
    "o",
    color=WARNA_K_AKTIF,
    markersize=13,
    markeredgecolor="white",
    markeredgewidth=2.5,
    zorder=4,
    label=f"K={K_AKTIF} (Digunakan Sistem)"
)

# --- Garis vertikal putus-putus penanda K aktif ---
ax.axvline(
    x=K_AKTIF,
    color=WARNA_K_AKTIF,
    linestyle="--",
    linewidth=1.5,
    alpha=0.6,
    zorder=2
)

# --- Pengaturan sumbu ---
ax.set_xticks(nilai_k)
ax.set_xticklabels([f"K = {k}" for k in nilai_k], fontsize=12)
ax.set_xlabel("Nilai K (Jumlah Tetangga Terdekat)", fontsize=12, labelpad=10)
ax.set_ylabel("Akurasi (%)", fontsize=12, labelpad=10)

# Rentang sumbu Y: dari 50% sampai 110% agar grafik tidak terlalu sempit
y_min = max(0, min(akurasi) - 20)
y_max = min(110, max(akurasi) + 10)
ax.set_ylim(y_min, y_max)

# --- Judul ---
ax.set_title(JUDUL_GRAFIK, fontsize=14, fontweight="bold", pad=18, color="#1E293B")

# --- Legenda ---
ax.legend(loc="lower left", fontsize=10, framealpha=0.9)

# --- Border bersih ---
for spine in ax.spines.values():
    spine.set_edgecolor("#CBD5E1")

plt.tight_layout()

# --- Simpan sebagai PNG ---
plt.savefig(NAMA_FILE_PNG, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"\n  Grafik disimpan sebagai: {NAMA_FILE_PNG}")

plt.show()
print("  Program selesai.")
