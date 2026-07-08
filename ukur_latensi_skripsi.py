import requests
import time
import statistics

# --- KONFIGURASI ---
# Ganti dengan username dan password yang biasa Anda gunakan untuk login ke web
USERNAME = "admin"
PASSWORD = "admin123"
JUMLAH_TEST = 20 # Jumlah perulangan testing untuk setiap halaman agar dapat rata-rata yang akurat

def ukur_halaman(ip_address, nama_pengujian):
    print(f"\n{'='*60}")
    print(f"MEMULAI {nama_pengujian}")
    print(f"Target: {ip_address}")
    print(f"{'='*60}")
    
    session = requests.Session()
    login_url = f"{ip_address}/login"
    login_data = {'username': USERNAME, 'password': PASSWORD}
    
    try:
        # Melakukan proses login otomatis
        res = session.post(login_url, data=login_data, timeout=5)
        if "login" in res.url.lower():
            print("GAGAL LOGIN! Silakan cek kembali username/password di dalam script.")
            return
        print("Login Berhasil! Sedang mengumpulkan data latensi halaman...\n")
    except requests.exceptions.ConnectionError:
        print(f"Tidak dapat terhubung ke {ip_address}. Pastikan server berjalan/terhubung.")
        return
    except Exception as e:
        print(f"Terjadi error: {e}")
        return

    # Daftar URL halaman web yang akan diuji
    halaman = {
        "Profil": f"{ip_address}/profile",
        "Dashboard": f"{ip_address}/index",
        "Monitoring Slot": f"{ip_address}/monitoring",
        "Keuangan": f"{ip_address}/finance",
        "Langganan": f"{ip_address}/subscription",
        "Prediksi": f"{ip_address}/prediction"
        
    }

    # Mengukur setiap halaman
    for nama, url in halaman.items():
        waktu_respon = []
        for i in range(JUMLAH_TEST):
            start_time = time.time()
            try:
                response = session.get(url, timeout=5)
                # Durasi dalam milidetik (ms)
                durasi_ms = (time.time() - start_time) * 1000
                waktu_respon.append(durasi_ms)
            except Exception:
                pass
            time.sleep(0.05) # Jeda singkat antar-request
            
        if waktu_respon:
            rata_rata = statistics.mean(waktu_respon)
            mini = min(waktu_respon)
            maks = max(waktu_respon)
            print(f"[{nama}]")
            print(f" -> Rata-rata : {rata_rata:6.2f} ms")
            print(f" -> Tercepat  : {mini:6.2f} ms")
            print(f" -> Terlama   : {maks:6.2f} ms\n")
        else:
            print(f"[{nama}] Gagal merespon!\n")

if __name__ == "__main__":
    # 2. Menguji via IP Jaringan (Hotspot/WiFi)
    # Ini menunjukkan kecepatan REAL yang dirasakan pengguna melalui perantara jaringan WiFi/Kabel
    ukur_halaman("http://10.42.0.1:5000", "PENGUJIAN JARINGAN (Pemrosesan Server + Transmisi Jaringan)")
    
    print("\nPengujian selesai!")
