const int trigPin = 16; 
const int echoPin = 17; 

long durasi;
int jarakCm;

void setup() {
  Serial.begin(9600);
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
}

void loop() {
  // Bersihkan pin Trig
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  
  // Kirim sinyal ultrasonik
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  // Baca waktu pantulan gelombang (ditambah timeout 30000 mikrodetik agar tidak stuck)
  durasi = pulseIn(echoPin, HIGH, 30000);
  
  // Hitung jarak dalam cm
  jarakCm = durasi * 0.034 / 2;
  
  // Validasi: JSN-SR04T akurat di atas 20 cm dan di bawah 600 cm
  if (jarakCm < 20 || jarakCm > 600) {
    Serial.println("Jarak di luar jangkauan sensor!");
  } else {
    Serial.print("Jarak: ");
    Serial.print(jarakCm);
    Serial.println(" cm");
  }
  
  delay(500);
}
