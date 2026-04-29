const int PIN_R = 8, PIN_Y = 9, PIN_G = 10;

void setTL(char c) {
  digitalWrite(PIN_R, c == 'R');
  digitalWrite(PIN_Y, c == 'Y');
  digitalWrite(PIN_G, c == 'G');
}

void setup() {
  Serial.begin(9600);
  pinMode(PIN_R, OUTPUT);
  pinMode(PIN_Y, OUTPUT);
  pinMode(PIN_G, OUTPUT);
}

void loop() {
  if (Serial.available() > 0) {
    char c = Serial.read();
    if (c == 'R' || c == 'Y' || c == 'G') setTL(c);
  }
}
