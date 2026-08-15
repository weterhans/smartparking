# Referensi API Web Monitor

Dokumen ini menjelaskan API Web Monitor yang disediakan oleh firmware ESP32.

---

## 🌐 Endpoint HTTP

| Method | Path | Deskripsi |
|---|---|---|
| `GET` | `/` | Halaman Web Monitor (HTML) |

### Contoh Request

```
GET http://192.168.4.1/
```

**Response:** Halaman HTML dashboard Web Monitor (lihat `WEB_PAGE` di firmware).

---

## 🔌 WebSocket API

Semua data real-time dikirim via WebSocket di port 81.

### Koneksi

```javascript
const ws = new WebSocket("ws://192.168.4.1:81");
ws.onmessage = (event) => {
    const data = event.data; // String log
};
```

### Format Pesan

ESP32 mengirim pesan dalam format **string teks** (bukan JSON). Setiap pesan diakhiri dengan `\n`.

#### Kategori Pesan

Pesan dibedakan berdasarkan prefiks:

| Prefiks | Warna Dashboard | Contoh |
|---|---|---|
| `[BOOT]`, `[WIFI]`, `[LCD]` | Ungu (header) | `[BOOT] Edge AI v3.0` |
| `[KAL]`, `[OFFSET]` | Biru muda (kalibrasi) | `[KAL] S1=250.1cm` |
| `[OK]`, `[KELAS]` | Hijau | `[OK] CityCar (d=0.142)` |
| `[WARN]`, `[ARAH]` | Kuning | `[WARN] Arah salah` |
| `[ERR]`, `[TIMEOUT]` | Merah | `[ERR] Timeout 30s` |
| `[S1]`, `[S2]`, `[DAT]` | Abu-abu (data) | `[S1] 248.3cm` |
| Lainnya | Abu-abu (default) | `Menunggu kendaraan...` |

#### Pesan Klasifikasi

Saat kendaraan terklasifikasi, pesan mengikuti format:

```
==============================================
KELAS    : CityCar
PANJANG  : 3.52 m
TINGGI   : 1.49 m
SILUET   : 0.378
POSMAX   : 0.586
SLOPE    : 29.0°
COMPACT  : 0.752
REAR     : 0.897
FLAT     : 0.510
V-MASUK  : 38.5 km/h
V-KELUAR : 37.2 km/h
==============================================
```

#### Pesan Sensor Real-time

Selama kendaraan melintas, data sensor dikirim setiap ~10 ms:

```
[DAT] S1=178.3 S2=241.5 t=1234567
```

---

## 📊 Event JavaScript di Dashboard

Dashboard HTML menggunakan event handler berikut untuk memperbarui UI:

```javascript
// Parsing pesan klasifikasi untuk update kartu hasil
if (msg.includes("KELAS")) {
    const kelas = msg.match(/KELAS\s*:\s*(\w+)/)?.[1];
    updateResultCard(kelas);
}

// Update indikator koneksi
ws.onopen  = () => setStatus("Terhubung", "alive");
ws.onclose = () => setStatus("Terputus",  "");
```

---

## 📡 ESP-NOW Protocol

Selain WebSocket, hasil klasifikasi juga dikirim ke ESP32 penerima via ESP-NOW.

### Struktur Data

```cpp
typedef struct struct_message {
    char vehicleType[20];
} struct_message;
```

### Format Nilai `vehicleType`

| Kelas Deteksi | Nilai yang Dikirim |
|---|---|
| CityCar | `"CITY CAR"` |
| Sedan | `"SEDAN"` |
| MPV | `"MPV"` |
| SUV | `"SUV"` |
| Pickup | `"PICKUP"` |

### Konfigurasi ESP-NOW

```cpp
// MAC address penerima (ubah sesuai perangkat Anda)
const uint8_t MAC_PENERIMA[6] = {0xB0, 0xCB, 0xD8, 0xCE, 0xE9, 0x80};
```

Untuk mendapatkan MAC address ESP32 penerima:
```cpp
// Jalankan kode ini di ESP32 penerima
#include <WiFi.h>
void setup() {
    Serial.begin(115200);
    Serial.println(WiFi.macAddress());
}
void loop() {}
```

---

## 🔁 Log History

ESP32 menyimpan 50 pesan log terakhir dalam buffer ring (`logHistory`). Saat client WebSocket baru terhubung, semua log history dikirim ulang secara otomatis, sehingga client tidak kehilangan informasi saat refresh halaman.
