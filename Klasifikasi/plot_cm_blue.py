import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

# Confusion Matrix K=3 dari hasil pengujian 24 data uji
# Urutan kelas: City Car, Sedan, MPV, SUV, Pickup
# True label di baris, Predicted label di kolom
cm = np.array([
    [5, 0, 0, 0, 0],  # City Car
    [0, 4, 0, 0, 0],  # Sedan
    [1, 0, 4, 0, 0],  # MPV (1 salah diprediksi City Car)
    [0, 0, 1, 4, 0],  # SUV (1 salah diprediksi MPV)
    [0, 0, 0, 0, 5]   # Pickup
])

classes = ['City Car', 'Sedan', 'MPV', 'SUV', 'Pickup']

fig, ax = plt.subplots(figsize=(7, 5.5))

# Plot heatmap menggunakan colormap 'Blues'
cmap = plt.cm.Blues
im = ax.imshow(cm, interpolation='nearest', cmap=cmap)

# Tambahkan Colorbar
cbar = ax.figure.colorbar(im, ax=ax)

# Setup axis labels and ticks
ax.set_xticks(np.arange(len(classes)))
ax.set_yticks(np.arange(len(classes)))
ax.set_xticklabels(classes)
ax.set_yticklabels(classes)

# Label X dan Y
ax.set_ylabel('True label', fontsize=11)
ax.set_xlabel('Predicted label', fontsize=11)

# Judul Grafik
ax.set_title('Confusion Matrix Klasifikasi Kendaraan (K=3)', fontsize=12, pad=15)

# Teks di dalam sel (warna biru gelap untuk sel terang, putih untuk sel sangat gelap)
thresh = cm.max() / 2.
for i in range(len(classes)):
    for j in range(len(classes)):
        color = "white" if cm[i, j] > thresh else "#1f497d"
        ax.text(j, i, format(cm[i, j], 'd'),
                ha="center", va="center",
                color=color, fontsize=11)

# Estetika layout
fig.tight_layout()

# Simpan ke PNG
output_filename = "Confusion_Matrix_K3_Biru.png"
plt.savefig(output_filename, dpi=200, bbox_inches='tight')
print(f"Berhasil menyimpan {output_filename}")
