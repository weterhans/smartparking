# Visualisasi — Edge AI Vehicle Classifier

Direktori ini berisi file HTML interaktif untuk memvisualisasikan berbagai aspek sistem klasifikasi kendaraan. Semua file berjalan langsung di browser tanpa perlu server.

---

## 📂 Isi Direktori

| File | Deskripsi |
|---|---|
| `Simulasi_Siluet_Web.html` | Simulasi interaktif rekonstruksi siluet kendaraan |
| `fitur_visualization.html` | Visualisasi distribusi 8 fitur antar kelas kendaraan |
| `glbb_visualization.html` | Visualisasi model GLBB untuk estimasi kecepatan kendaraan |

---

## 🖥 Cara Membuka

Cukup buka file `.html` menggunakan browser modern (Chrome, Firefox, Edge):

```
# Windows
start Simulasi_Siluet_Web.html

# Atau drag & drop file ke browser
```

Tidak memerlukan koneksi internet atau server lokal.

---

## 📊 Deskripsi Visualisasi

### `Simulasi_Siluet_Web.html`

Simulasi interaktif yang menunjukkan bagaimana profil siluet kendaraan direkonstruksi dari sampel LiDAR.

**Fitur:**
- Animasi kendaraan melintas portal sensor
- Tampilan sampel mentah vs setelah filter REMA
- Overlay profil siluet hasil rekonstruksi spasial
- Kontrol kecepatan dan parameter filter

---

### `fitur_visualization.html`

Visualisasi distribusi nilai 8 fitur untuk setiap kelas kendaraan.

**Fitur:**
- Scatter plot 2D dengan pemilihan fitur sumbu X/Y
- Color coding per kelas kendaraan
- Tampilan batas keputusan KNN

---

### `glbb_visualization.html`

Visualisasi model Gerak Lurus Berubah Beraturan (GLBB) yang digunakan untuk estimasi posisi kendaraan saat masuk dan keluar portal.

**Fitur:**
- Grafik posisi vs waktu
- Estimasi kecepatan dari selisih waktu S1→S2
- Visualisasi lag kompensasi EMA vs REMA

---

## 💡 Tips

- File `Simulasi_Siluet_Web.html` paling berguna untuk presentasi dan demonstrasi
- Gunakan `fitur_visualization.html` untuk memahami mengapa kelas tertentu saling overlap
- `glbb_visualization.html` berguna untuk menjelaskan dasar fisika estimasi kecepatan
