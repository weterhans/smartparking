#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h> // Tambahan untuk mengunci channel

// MAC Address Spesifik (Hanya mengirim ke Master ini saja sesuai permintaan
// Anda)
uint8_t nodeAddress[] = {0xB0, 0xCB, 0xD8, 0xCE, 0xE9, 0x80};

// Struktur pesan ESP-NOW (Dimaksimalkan ke 250 byte agar kompatibel dengan data
// Struktur pesan ESP-NOW (SAMA PERSIS 64 byte dengan MASTER)
typedef struct struct_message {
  char text[64];
} struct_message;

struct_message myDataIn;
struct_message myDataOut;

esp_now_peer_info_t peerInfo;

// Callback saat Gateway berhasil mengirim ke Node
void OnDataSent(const wifi_tx_info_t *pi, esp_now_send_status_t status) {
  // Hanya print jika butuh debugging
  Serial.print("Status Pengiriman ke Node: ");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Berhasil" : "Gagal");
}

// Callback saat data diterima dari udara (ESP32 Core 3.x)
void OnDataRecv(const esp_now_recv_info_t *esp_now_info,
                const uint8_t *incomingData, int len) {
  // Hanya proses jika panjang datanya persis 64 byte (Data dari Joko Master)
  // Ini mencegah Gateway salah membaca data dari Sensor Ultrasonik (24 byte) 
  // yang bisa menghasilkan huruf acak/sampah.
  if (len == sizeof(myDataIn)) {
    memcpy(&myDataIn, incomingData, sizeof(myDataIn));
    // LANGSUNG CETAK KE SERIAL (Diteruskan ke Web / Raspberry Pi via kabel USB)
    Serial.println(myDataIn.text);
  }
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);

  // SANGAT PENTING: Kunci channel WiFi ke 1 agar sama persis dengan Master
  // Anda. Jika tidak dikunci, ESP Joko dan ESP Master bisa berada di channel
  // berbeda sehingga pesan (seperti PAID:1) bisa gagal terkirim/diterima.
  esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);

  if (esp_now_init() != ESP_OK) {
    Serial.println("Error menginisialisasi ESP-NOW");
    return;
  }

  // Daftarkan Callback
  esp_now_register_recv_cb(OnDataRecv);

  // Daftarkan callback kirim secara standar
  esp_now_register_send_cb(OnDataSent);

  // Daftarkan Node Pengirim sebagai Peer (Spesifik)
  memset(&peerInfo, 0, sizeof(peerInfo)); // Pastikan memori bersih
  memcpy(peerInfo.peer_addr, nodeAddress, 6);
  peerInfo.channel = 1; // Sesuaikan dengan channel yang dikunci
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Gagal mendaftarkan Node Peer");
    return;
  }

  Serial.println("GATEWAY ESP-NOW (DUA ARAH) AKTIF. CHANNEL 1");
}

void loop() {
  // Jika Web / Raspberry Pi Joko mengirim data via Serial (seperti PAID:1 atau
  // MEMBER_IN:2), Gateway akan mengirimkannya langsung ke Master Anda via
  // ESP-NOW
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    if (command.length() > 0) {
      strncpy(myDataOut.text, command.c_str(), sizeof(myDataOut.text) - 1);
      myDataOut.text[sizeof(myDataOut.text) - 1] =
          '\0'; // Pastikan string tertutup
      esp_now_send(nodeAddress, (uint8_t *)&myDataOut, sizeof(myDataOut));
    }
  }
}
