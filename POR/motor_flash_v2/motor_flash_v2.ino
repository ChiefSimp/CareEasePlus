// Arduino: 2x BTS7960 serial motor control
// Commands over Serial:
//   M1 <value>\n   where value is -255..255
//   M2 <value>\n   where value is -255..255
// Example: "M1 -120" "M2 200" "M1 0" "M2 0"

#define M1_RPWM 5
#define M1_LPWM 6
#define M1_REN  7
#define M1_LEN  8

#define M2_RPWM 9
#define M2_LPWM 10
#define M2_REN  11
#define M2_LEN  12

#define M3_IN1 2
#define M3_IN2 3


void setMotor(int rpwmPin, int lpwmPin, int cmd) {
  cmd = constrain(cmd, -255, 255);

  if (cmd > 0) {
    analogWrite(rpwmPin, 0);
    analogWrite(lpwmPin, cmd);
  } else if (cmd < 0) {
    analogWrite(rpwmPin, -cmd);
    analogWrite(lpwmPin, 0);
  } else {
    analogWrite(rpwmPin, 0);
    analogWrite(lpwmPin, 0);
  }
}

void setConveyorMotor(int in1Pin, int in2Pin, int cmd){
  cmd = constrain(cmd, -255, 255);
  if(cmd > 0){
    analogWrite(in1Pin, cmd); //forward
    analogWrite(in2Pin, 0);
  } else if (cmd < 0) {
    analogWrite(in1Pin, 0);
    analogWrite(in2Pin, -cmd); //Reverse
  } else {
    analogWrite(in1Pin, 0);
    analogWrite(in2Pin, 0);
  }
}

void setup() {
  
  // Motor 1 Pins
  pinMode(M1_RPWM, OUTPUT); pinMode(M1_LPWM, OUTPUT);
  pinMode(M1_REN, OUTPUT);  pinMode(M1_LEN, OUTPUT);

  // Motor 2 Pins
  pinMode(M2_RPWM, OUTPUT); pinMode(M2_LPWM, OUTPUT);
  pinMode(M2_REN, OUTPUT);  pinMode(M2_LEN, OUTPUT);

  // Motor 3 Pins
  pinMode(M3_IN1, OUTPUT); pinMode(M3_IN2, OUTPUT);

  digitalWrite(M1_REN, HIGH); digitalWrite(M1_LEN, HIGH);
  digitalWrite(M2_REN, HIGH); digitalWrite(M2_LEN, HIGH);

  Serial.begin(115200);
  Serial.setTimeout(10);

  setMotor(M1_RPWM, M1_LPWM, 0);
  setMotor(M2_RPWM, M2_LPWM, 0);
  setMotor(M3_IN1, M3_IN2, 0);

  Serial.println("Ready: send 'M1 -255..255' and 'M2 -255..255'");
}

void loop() {
  if (!Serial.available()) return;

  String line = Serial.readStringUntil('\n');
  line.trim();

  if (line == "STOP"){
    setMotor(M1_RPWM, M1_LPWM, 0);
    setMotor(M2_RPWM, M2_LPWM, 0);
    setMotor(M3_IN1, M3_IN2, 0);
    Serial.println("OK ALL STOP");
    return;
  }

  if (line.length() < 3) return;

  int spaceIdx = line.indexOf(' ');
  if (spaceIdx < 0) return;

  String motor = line.substring(0, spaceIdx);
  int cmd = line.substring(spaceIdx + 1).toInt();
  cmd = constrain(cmd, -255, 255);

  if (motor == "M1") {
    setMotor(M1_RPWM, M1_LPWM, cmd);
    Serial.print("OK M1 "); Serial.println(cmd);
  } else if (motor == "M2") {
    setMotor(M2_RPWM, M2_LPWM, cmd);
    Serial.print("OK M2 "); Serial.println(cmd);
  } else if (motor == "M3") {
    setMotor(M3_IN1, M3_IN2, cmd);
    Serial.print("OK M3"); Serial.println(cmd);
  } else {
    Serial.print("ERR Unknown motor: "); Serial.println(motor);
  }
}
