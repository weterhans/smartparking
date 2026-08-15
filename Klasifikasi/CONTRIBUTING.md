# Panduan Kontribusi

Terima kasih telah berminat berkontribusi pada proyek ini! 🎉

Dokumen ini menjelaskan cara yang benar untuk berkontribusi agar semua perubahan dapat diterima dengan lancar.

---

## 📋 Daftar Isi

- [Kode Etik](#kode-etik)
- [Cara Melaporkan Bug](#cara-melaporkan-bug)
- [Cara Mengusulkan Fitur](#cara-mengusulkan-fitur)
- [Cara Berkontribusi Kode](#cara-berkontribusi-kode)
- [Standar Kode](#standar-kode)
- [Proses Pull Request](#proses-pull-request)
- [Struktur Commit](#struktur-commit)

---

## 🤝 Kode Etik

Proyek ini mengadopsi prinsip keterbukaan dan rasa hormat. Harap:
- Gunakan bahasa yang sopan dan inklusif
- Hormati perbedaan sudut pandang dan pengalaman
- Terima kritik konstruktif dengan lapang dada
- Fokus pada apa yang terbaik untuk komunitas dan proyek

---

## 🐛 Cara Melaporkan Bug

Sebelum melaporkan bug, pastikan:
1. Bug belum dilaporkan di [Issues](../../issues)
2. Anda menggunakan versi firmware terbaru (v3.0)

Saat membuat issue bug, gunakan template yang tersedia dan sertakan:
- **Versi firmware** yang digunakan
- **Perangkat keras**: tipe ESP32, versi board package
- **Langkah reproduksi**: langkah-langkah detail untuk mereproduksi bug
- **Perilaku yang diharapkan** vs **perilaku yang terjadi**
- **Log Serial / Web Monitor** jika ada
- **Foto atau video** jika membantu

---

## 💡 Cara Mengusulkan Fitur

Ide-ide baru sangat disambut! Buat issue baru dengan label `enhancement` dan jelaskan:
- **Masalah** yang ingin diselesaikan
- **Solusi yang diusulkan**
- **Alternatif** yang sudah dipertimbangkan
- **Konteks tambahan** (apakah untuk penelitian, produksi, dll)

---

## 🔧 Cara Berkontribusi Kode

### Setup Pengembangan

```bash
# 1. Fork dan clone repositori
git clone https://github.com/USERNAME/tf-luna-vehicle-classifier.git
cd tf-luna-vehicle-classifier

# 2. Buat branch baru dari main
git checkout -b fitur/nama-fitur-anda
# atau untuk perbaikan bug:
git checkout -b fix/nama-bug-yang-diperbaiki
```

### Area Kontribusi yang Disambut

| Area | Contoh Kontribusi |
|---|---|
| 🧠 Algoritma | Bobot FWkNN yang lebih optimal, alternatif classifier |
| 📡 Sensor | Dukungan sensor LiDAR lain, kalibrasi otomatis |
| 🌐 Web Monitor | Fitur baru dashboard, export data CSV |
| 📊 Analisis | Script analisis baru, visualisasi tambahan |
| 📖 Dokumentasi | Perbaikan typo, panduan lebih jelas |
| 🐛 Bug Fix | Perbaikan bug yang sudah dilaporkan |

---

## 📐 Standar Kode

### Firmware Arduino (C++)

- Gunakan **komentar Bahasa Indonesia** yang konsisten dengan kode existing
- Ikuti konvensi penamaan yang sudah ada:
  - variabel: `camelCase` (contoh: `jarakMulus`)
  - konstanta: `UPPER_SNAKE_CASE` (contoh: `REMA_ALPHA`)
  - fungsi: `camelCase` (contoh: `hitungFitur()`)
- Tambahkan komentar di atas setiap fungsi yang menjelaskan tujuannya
- Jangan hapus komentar yang sudah ada kecuali memang sudah tidak relevan
- Pastikan tidak ada warning compiler yang baru muncul

### Python

- Ikuti [PEP 8](https://pep8.org/) untuk style kode
- Gunakan **Bahasa Indonesia** untuk komentar dan docstring
- Tambahkan docstring di setiap fungsi:
  ```python
  def hitung_fitur(siluet):
      """
      Menghitung 8 fitur geometri dari profil siluet kendaraan.
      
      Args:
          siluet (list): List pasangan (posisi_cm, tinggi_cm)
      
      Returns:
          dict: Dictionary berisi 8 nilai fitur
      """
  ```
- Gunakan `requirements.txt` untuk mendaftar semua dependensi baru

---

## 🔄 Proses Pull Request

1. **Pastikan** semua perubahan sudah diuji
2. **Update dokumentasi** jika diperlukan (README, docs/)
3. **Update CHANGELOG.md** dengan deskripsi perubahan di bagian `[Unreleased]`
4. Buat Pull Request ke branch `main`
5. Isi template PR yang disediakan
6. Tunggu review dari maintainer

### Kriteria Penerimaan PR

- ✅ Kode berjalan tanpa error di Arduino IDE (firmware)
- ✅ Script Python berjalan tanpa error
- ✅ Perubahan telah diuji dengan hardware nyata (untuk perubahan firmware)
- ✅ Dokumentasi diperbarui jika ada perubahan API atau perilaku
- ✅ CHANGELOG.md diperbarui

---

## 📝 Struktur Commit

Gunakan format **Conventional Commits**:

```
<tipe>(<lingkup>): <deskripsi singkat>

[isi opsional]

[footer opsional]
```

### Tipe Commit

| Tipe | Keterangan | Contoh |
|---|---|---|
| `feat` | Fitur baru | `feat(firmware): tambah dukungan sensor TF-Mini` |
| `fix` | Perbaikan bug | `fix(rema): perbaiki overflow saat nilai alpha=1` |
| `docs` | Perubahan dokumentasi | `docs(readme): tambah diagram pin ESP32` |
| `refactor` | Refaktor kode | `refactor(knn): pisahkan fungsi normalisasi` |
| `test` | Tambah/ubah test | `test(analysis): tambah unit test FWkNN` |
| `chore` | Perubahan non-fungsional | `chore: update .gitignore` |

### Contoh Commit yang Baik

```
feat(firmware): tambah mode debug via Serial Monitor

- Tambah flag DEBUG_MODE yang bisa diaktifkan saat kompilasi
- Saat DEBUG_MODE aktif, print detail fitur ke Serial setiap deteksi
- Tidak mempengaruhi performa saat DEBUG_MODE=false

Closes #12
```

---

Pertanyaan? Buka [Discussion](../../discussions) atau hubungi maintainer via issue.

Terima kasih sudah berkontribusi! 🚀
