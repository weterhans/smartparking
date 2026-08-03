import time
import board
import busio
import digitalio
import serial
import requests
import json
from PIL import Image, ImageDraw, ImageFont

import os
os.environ["GPIOZERO_PIN_FACTORY"] = "rpigpio"
from gpiozero import Button

import adafruit_rgb_display.ili9341 as ili9341
from adafruit_pn532.i2c import PN532_I2C

# ==========================================
# KONFIGURASI ALAMAT API FLASK
# ==========================================
API_BASE_URL = "http://127.0.0.1:5000/api/hardware"

# ==========================================
# KONFIGURASI SERIAL (KONEKSI ESP32 GATEWAY)
# ==========================================
# BUNUH PAKSA SILUMAN TTY (GETTY) YANG MEMBAJAK PORT USB SAAT BOOTING
os.system("sudo systemctl stop serial-getty@ttyUSB0.service > /dev/null 2>&1")
os.system("sudo systemctl stop getty@ttyUSB0.service > /dev/null 2>&1")
os.system("sudo killall agetty > /dev/null 2>&1")
time.sleep(1)

# Inisialisasi awal sebagai None agar ditangani oleh fitur Auto-Reconnect di dalam loop utama
ser_gateway = None

# ==========================================
# KONFIGURASI PUSH BUTTON
# ==========================================
tombol = Button(17, pull_up=True)

# ==========================================
# KONFIGURASI LCD TFT (SPI)
# ==========================================
cs_pin = digitalio.DigitalInOut(board.D22) # Diubah dari D8 ke D22 untuk menghindari 'GPIO busy'
dc_pin = digitalio.DigitalInOut(board.D24)
reset_pin = digitalio.DigitalInOut(board.D25)
spi = board.SPI()

disp = ili9341.ILI9341(
    spi,
    rotation=90,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=24000000,
)

if disp.rotation % 180 == 90:
    width = disp.height
    height = disp.width
else:
    width = disp.width
    height = disp.height

image = Image.new("RGB", (width, height))
draw = ImageDraw.Draw(image)
try:
    font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    font_xsmall = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
except IOError:
    # Jika font tidak ada, pakai default (kecil)
    font_title = ImageFont.load_default()
    font_large = ImageFont.load_default()
    font_medium = ImageFont.load_default()
    font_small = ImageFont.load_default()
    font_xsmall = ImageFont.load_default()

def perbarui_layar(teks1, teks2="", teks3=""):
    # 1. Warna Latar Belakang (PUTIH TERANG - High Contrast Siang Hari)
    bg_color = (255, 255, 255) # Putih Murni
    draw.rectangle((0, 0, width, height), outline=0, fill=bg_color)
    
    # 2. Header Bar (HITAM PEKAT - Kontras Tinggi)
    header_h = 45
    draw.rectangle((0, 0, width, header_h), outline=0, fill=(0, 0, 0)) # Hitam Murni
    # Judul Aplikasi di Header
    try:
        draw.text((width//2, header_h//2), "SMART PARKING", font=font_title, fill=(255, 255, 255), anchor="mm")
    except TypeError:
        # Jika versi Pillow lama tidak mendukung anchor="mm"
        draw.text((60, 12), "SMART PARKING", font=font_title, fill=(255, 255, 255))
    
    # 3. Card Putih di Tengah (Sebagai Kolom Utama)
    margin_x = 15
    margin_y = 60
    card_w = width - (margin_x * 2)
    card_h = height - margin_y - 15
    
    # Efek Bayangan Card dihapus agar lebih tegas di siang hari
    
    # Body Card (Putih) dengan border HITAM TEBAL
    draw.rectangle((margin_x, margin_y, margin_x+card_w, margin_y+card_h), outline=(0, 0, 0), width=4, fill=(255, 255, 255))
    
    # 4. Mencetak Teks di dalam Card
    try:
        # Teks 1: Judul Status Utama (Tebal, HITAM PEKAT)
        draw.text((width//2, margin_y + 35), teks1, font=font_large, fill=(0, 0, 0), anchor="mm")
        
        # Teks 2: Isi/Informasi (Tebal, BIRU TUA GELAP agar berbeda sedikit)
        f2 = font_medium
        if len(teks2) > 26:
            f2 = font_xsmall
        elif len(teks2) > 18:
            f2 = font_small
        draw.text((width//2, margin_y + 80), teks2, font=f2, fill=(0, 0, 150), anchor="mm")
        
        # Teks 3: Instruksi Tambahan (Tebal, MERAH TUA PEKAT untuk perhatian)
        f3 = font_small
        if len(teks3) > 25:
            f3 = font_xsmall
        draw.text((width//2, margin_y + 125), teks3, font=f3, fill=(180, 0, 0), anchor="mm")
    except TypeError:
        # Fallback untuk Pillow versi sangat lama (tidak di tengah secara sempurna)
        draw.text((margin_x + 10, margin_y + 20), teks1, font=font_large, fill=(44, 62, 80))
        draw.text((margin_x + 10, margin_y + 60), teks2, font=font_medium, fill=(22, 160, 133))
        draw.text((margin_x + 10, margin_y + 100), teks3, font=font_small, fill=(127, 140, 141))
        
    disp.image(image)

# ==========================================
# KONFIGURASI NFC PN532 (I2C)
# ==========================================
i2c = busio.I2C(board.SCL, board.SDA)
try:
    pn532 = PN532_I2C(i2c, debug=False)
    ic, ver, rev, support = pn532.firmware_version
    pn532.SAM_configuration()
    print("NFC Aktif")
except Exception as e:
    print("NFC Error:", e)
    pn532 = None

# ==========================================
# STATE MACHINE VARIABLES
# ==========================================
menunggu_pembayaran = None # Menyimpan ID Slot yang antre checkout, contoh: 'Slot_A1'

perbarui_layar("Silakan Masuk", "Tap Kartu NFC Anda", "Atau Tunggu Arahan")
print("Program Hardware Berjalan...")

# Variabel untuk menahan pesan error agar tidak spam
serial_error_printed = False

# Variabel pewaktu untuk mengecek status reservasi member secara berkala
last_reserved_check = 0
last_sim_check = 0

try:
    while True:
        # 0. AUTO RECONNECT SERIAL JIKA TERPUTUS / GAGAL DI AWAL B00T
        if ser_gateway is None:
            try:
                # Tambahkan exclusive=True agar tidak ada program Linux lain (seperti getty) yang bisa membajak port ini!
                ser_gateway = serial.Serial('/dev/ttyUSB0', 115200, timeout=1, exclusive=True)
                
                # --- FIX KERNEL BAUDRATE CACHE BUG ---
                # Memaksa pyserial menembakkan ulang perintah system-call (tcsetattr) ke Linux
                ser_gateway.baudrate = 9600
                time.sleep(0.1)
                ser_gateway.baudrate = 115200
                time.sleep(0.1)
                # -------------------------------------
                
                # --- HARD RESET ESP32 VIA DTR/RTS ---
                # Memaksa ESP32 untuk restart dari awal agar terhindar dari glitch saat cold-boot
                ser_gateway.dtr = True
                ser_gateway.rts = False
                time.sleep(0.1)
                ser_gateway.dtr = False
                ser_gateway.rts = False
                time.sleep(0.5)
                ser_gateway.reset_input_buffer()
                # ------------------------------------

                print("Serial USB0 BERHASIL Terhubung & ESP32 di-Reset!")
                serial_error_printed = False
            except Exception as e:
                if not serial_error_printed:
                    print(f"Menunggu Serial USB0: {e}")
                    serial_error_printed = True
                time.sleep(2)
                continue # Jangan lanjut baca kalau serial belum ada

        # 1. BACA SERIAL GATEWAY (Dari Master via ESP-NOW)
        try:
            if ser_gateway and ser_gateway.in_waiting > 0:
                data_masuk = ser_gateway.readline().decode('utf-8', errors='ignore').strip()
                if data_masuk:
                    print(f"[DEBUG] Gateway Menerima: {data_masuk}")
                    
                    # Cek STAT:0,K,B,0,M,0 (Toleransi 'TAT:' jika huruf S terpotong)
                    if data_masuk.startswith("STAT:") or data_masuk.startswith("TAT:"):
                        # Ambil data setelah titik dua
                        if ":" in data_masuk:
                            stat_str = data_masuk.split(":", 1)[1].strip()
                            try:
                                res = requests.post(f"{API_BASE_URL}/update_stat", json={"stat_str": stat_str}, timeout=2)
                                print(f"Update Web: {res.status_code}")
                            except Exception as e:
                                print(f"Gagal Update Web: {e}")
                        
                    # Cek PAYREQ:X (Toleransi 'AYREQ:' jika huruf P terpotong)
                    elif data_masuk.startswith("PAYREQ:") or data_masuk.startswith("AYREQ:"):
                        if ":" in data_masuk:
                            angka_slot = data_masuk.split(":", 1)[1].strip()
                            slot_target = f"Slot_A{angka_slot}"
                            menunggu_pembayaran = slot_target
                            print(f"Permintaan Keluar {slot_target}. Menunggu Push Button.")
                            try:
                                res_fee = requests.post(f"{API_BASE_URL}/calculate_fee", json={"slot_key": slot_target}, timeout=2)
                                if res_fee.ok and res_fee.json().get("success"):
                                    data_fee = res_fee.json()
                                    perbarui_layar(f"A{angka_slot} - Rp {data_fee.get('fee_formatted')}", f"Durasi: {data_fee.get('duration')}", "Tekan Tombol Bayar")
                                else:
                                    perbarui_layar("Kendaraan Keluar", f"Slot A{angka_slot}", "Tekan Tombol Bayar")
                            except Exception as e:
                                print(f"Gagal Hit API Fee: {e}")
                                perbarui_layar("Kendaraan Keluar", f"Slot A{angka_slot}", "Tekan Tombol Bayar")
        except serial.SerialException as e:
            print("Koneksi Serial Terputus:", e)
            ser_gateway.close()
            ser_gateway = None

        # 2. BACA PUSH BUTTON (KONFIRMASI CHECKOUT REGULER)
        if tombol.is_pressed and menunggu_pembayaran is not None:
            angka_slot = menunggu_pembayaran.replace("Slot_A", "")
            print(f"Tombol Ditekan! Memproses Checkout untuk {menunggu_pembayaran}")
            perbarui_layar("Memproses...", "Menghitung Biaya", "Tunggu Sebentar")
            
            payload = {"slot_key": menunggu_pembayaran}
            try:
                res = requests.post(f"{API_BASE_URL}/checkout", json=payload, timeout=3)
                data_respon = res.json()
                if data_respon.get("success"):
                    perbarui_layar("SAMPAI JUMPA", "Terima Kasih, Hati-hati di Jalan", "Semoga Selamat Sampai Tujuan")
                    # Kirim perintah PAID ke Master untuk buka palang
                    if ser_gateway:
                        ser_gateway.write(f"PAID:{angka_slot}\n".encode('utf-8'))
                else:
                    perbarui_layar("Gagal Checkout", data_respon.get("error", ""), "Lapor ke Admin")
            except Exception as e:
                print("Gagal hubungi API Web:", e)
                perbarui_layar("ERROR KONEKSI", "Web Server Mati?", "")
                
            menunggu_pembayaran = None
            time.sleep(4)
            perbarui_layar("Silakan Masuk", "Tap Kartu NFC Anda", "Atau Tunggu Arahan")

        # 3. BACA NFC (LANGGANAN MASUK & KELUAR)
        if pn532:
            try:
                uid = pn532.read_passive_target(timeout=0.05)
            except RuntimeError:
                uid = None
            except Exception:
                uid = None
                
            if uid:
                uid_string = "".join([hex(i)[2:].zfill(2) for i in uid]).upper()
                print(f"NFC Terdeteksi: {uid_string}")
                perbarui_layar("Memproses NFC...", f"UID: {uid_string}", "Tunggu Sebentar")
                
                payload = {"card_uid": uid_string}
                try:
                    res = requests.post(f"{API_BASE_URL}/nfc_tap", json=payload, timeout=3)
                    data_respon = res.json()
                    if data_respon.get("success"):
                        aksi = data_respon.get("action")
                        pesan = data_respon.get("message")
                        
                        # API nfc_tap mengembalikan slot_key member (misal: "Slot_A2" atau "Silakan ke Slot_A2")
                        slot_key_raw = data_respon.get("slot", "")
                        angka_slot = slot_key_raw.replace("Slot_A", "").replace("Silakan ke ", "").strip()
                        
                        if aksi == "checkin":
                            perbarui_layar("SELAMAT DATANG", pesan, slot_key_raw)
                            # Kirim perintah buka gerbang masuk ke Master
                            if ser_gateway:
                                ser_gateway.write(f"MEMBER_IN:{angka_slot}\n".encode('utf-8'))
                        else:
                            perbarui_layar("SAMPAI JUMPA", "Terima Kasih, Hati-hati di Jalan", "Semoga Selamat Sampai Tujuan")
                            # Kirim perintah buka gerbang keluar ke Master
                            if ser_gateway:
                                ser_gateway.write(f"MEMBER_OUT:{angka_slot}\n".encode('utf-8'))
                    else:
                        perbarui_layar("AKSES DITOLAK", data_respon.get("message", ""), "Silakan Lapor Admin")
                except Exception as e:
                    print("Gagal hubungi API Web:", e)
                    perbarui_layar("ERROR KONEKSI", "Web Server Mati?", str(e))
                    
                time.sleep(4)
                perbarui_layar("Silakan Masuk", "Tap Kartu NFC Anda", "Atau Tunggu Arahan")
                
        # 4. SINKRONISASI SLOT RESERVASI MEMBER (Setiap 10 Detik)
        current_time = time.time()
        if current_time - last_reserved_check > 10:
            last_reserved_check = current_time
            try:
                # Memanggil API web Joko untuk mengambil status slot
                # Contoh Return JSON: {"success": true, "reserved": "0,1,0,0,0,0"}
                res = requests.get(f"{API_BASE_URL}/get_reserved", timeout=2)
                if res.ok:
                    data_res = res.json()
                    if data_res.get("success"):
                        reserved_str = data_res.get("reserved", "0,0,0,0,0,0")
                        if ser_gateway:
                            ser_gateway.write(f"RESERVED:{reserved_str}\n".encode('utf-8'))
            except Exception as e:
                pass # Abaikan error agar tidak spam (coba lagi 10 detik kemudian)

        # 5. CEK SIMULASI DARI WEB (Setiap 1.5 Detik)

        if current_time - last_sim_check > 1.5:
            last_sim_check = current_time
            try:
                res_sim = requests.get(f"{API_BASE_URL}/get_simulations", timeout=2)
                if res_sim.ok:
                    data_sim = res_sim.json()
                    if data_sim.get("action") == "OUT":
                        slot_target = data_sim.get("slot_id") # e.g. Slot_A1
                        angka_slot = slot_target.replace("Slot_A", "")
                        menunggu_pembayaran = slot_target
                        print(f"[SIMULASI] Permintaan Keluar {slot_target}. Menunggu Push Button.")
                        try:
                            res_fee = requests.post(f"{API_BASE_URL}/calculate_fee", json={"slot_key": slot_target}, timeout=2)
                            if res_fee.ok and res_fee.json().get("success"):
                                data_fee = res_fee.json()
                                perbarui_layar(f"A{angka_slot} - Rp {data_fee.get('fee_formatted')}", f"Durasi: {data_fee.get('duration')}", "Tekan Tombol Bayar")
                            else:
                                perbarui_layar("Kendaraan Keluar", f"Slot A{angka_slot}", "Tekan Tombol Bayar")
                        except Exception as e:
                            print(f"Gagal Hit API Fee: {e}")
                            perbarui_layar("Kendaraan Keluar", f"Slot A{angka_slot}", "Tekan Tombol Bayar")
            except Exception as e:
                pass # Silently ignore connection errors to avoid spam

                
        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nProgram dihentikan oleh pengguna.")
    perbarui_layar("Sistem Mati", "Dimatikan Manual", "")
finally:
    if ser_gateway:
        ser_gateway.close()

