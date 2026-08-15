import matplotlib.pyplot as plt

def render_equation(eq_str, filename, fontsize=24):
    # Membuat figure kosong
    fig = plt.figure(figsize=(6, 2))
    # Menuliskan rumus LaTeX di tengah (menggunakan mathtext matplotlib)
    fig.text(0.5, 0.5, eq_str, fontsize=fontsize, ha='center', va='center')
    # Menghilangkan axis (garis tepi grafik)
    plt.axis('off')
    # Menyimpan sebagai PNG resolusi tinggi
    plt.savefig(filename, bbox_inches='tight', pad_inches=0.1, dpi=300)
    plt.close()

# Daftar Rumus (Menggunakan format Raw String untuk LaTeX)
eq1 = r"$FDR(j) = \frac{S_{b,j}}{S_{w,j}}$"
eq2 = r"$S_{b,j} = \sum_{c=1}^{C} n_c (\mu_{c,j} - \mu_j)^2$"
eq3 = r"$S_{w,j} = \sum_{c=1}^{C} \sum_{i=1}^{n_c} (x_{c,j}^{(i)} - \mu_{c,j})^2$"

# Memproses dan menyimpan gambar
print("Sedang merender gambar...")
render_equation(eq1, "rumus_1_FDR.png", 36)
render_equation(eq2, "rumus_2_Sb.png", 28)
render_equation(eq3, "rumus_3_Sw.png", 28)
print("Berhasil! Gambar PNG telah dibuat.")
