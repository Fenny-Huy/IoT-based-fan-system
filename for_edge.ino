#include <DHT.h>
#include <U8x8lib.h>
#include <IRremote.h>

//—— DHT22 ——
#define DHTPIN   2
#define DHTTYPE  DHT22
DHT dht(DHTPIN, DHTTYPE);

//—— IR Receiver ——
#define IR_PIN   3

//—— Analog inputs ——
#define LDR_PIN    A0
#define POT_PIN    A1

//—— PWM & outputs ——
#define FAN_PIN      5
#define LED_OFF      6
#define LED_AUTO     7
#define LED_MANUAL   8
#define RGB_R        9
#define RGB_G        10
#define RGB_B        11
#define BUZZER_PIN   12

//—— Display ——
U8X8_SSD1306_128X64_NONAME_SW_I2C lcd(SCL, SDA, U8X8_PIN_NONE);

//—— System state ——
enum Mode { OFF, AUTO, MANUAL };
Mode mode = OFF;
int fixedSpeeds[5] = {51,102,153,204,255};
int fixedIndex = 0;
int potOverrideThreshold = 50;

//—— Timing ——
unsigned long lastRead = 0;
const unsigned long interval = 500;

//—— IR codes ——
const unsigned long IR_POWER =    4278238976UL;
const unsigned long IR_MODE =     4060987136UL;
const unsigned long IR_NEXT =     4177968896UL;
const unsigned long IR_PREV =     4211392256UL;
const unsigned long IR_1 =        4010852096UL;
const unsigned long IR_2 =        3994140416UL;
const unsigned long IR_3 =        3977428736UL;
const unsigned long IR_4 =        3944005376UL;
const unsigned long IR_5 =        3927293696UL;

void setup(){
  Serial.begin(9600);
  dht.begin();
  IrReceiver.begin(IR_PIN, ENABLE_LED_FEEDBACK);

  lcd.begin();
  lcd.setFont(u8x8_font_amstrad_cpc_extended_f);
  lcd.clear();

  pinMode(FAN_PIN, OUTPUT);
  pinMode(LED_OFF, OUTPUT);
  pinMode(LED_AUTO, OUTPUT);
  pinMode(LED_MANUAL, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(RGB_R, OUTPUT);
  pinMode(RGB_G, OUTPUT);
  pinMode(RGB_B, OUTPUT);
}

void loop(){
  // --- 1) IR handling ---
  if (IrReceiver.decode()) {
    unsigned long code = IrReceiver.decodedIRData.decodedRawData;
    Serial.print("IR code: ");
    Serial.println(code);
    handleIR(code);
    IrReceiver.resume();
  }

  // --- 2) Periodic sensor & actuator update ---
  if (millis() - lastRead >= interval) {
    lastRead = millis();
    updateSystem();
  }

  if (Serial.available()) {
  String command = Serial.readStringUntil('\n');
  command.trim();

  if (command == "BUZZ:ON") {
    digitalWrite(BUZZER_PIN, HIGH);
  } else if (command == "BUZZ:OFF") {
    digitalWrite(BUZZER_PIN, LOW);
  }
}
}

void handleIR(unsigned long code){
  switch(code){
    case IR_POWER:
      Serial.println("→ POWER");
      mode = (mode == OFF ? AUTO : OFF);
      break;
    case IR_MODE:
      Serial.println("→ MODE toggle");
      mode = (Mode)((mode + 1) % 3);
      break;
    case IR_NEXT:
      Serial.println("→ NEXT");
      if(mode == MANUAL) fixedIndex = (fixedIndex + 1) % 5;
      break;
    case IR_PREV:
      Serial.println("→ PREV");
      if(mode == MANUAL) fixedIndex = (fixedIndex + 4) % 5;
      break;
    case IR_1: Serial.println("→ 1"); if(mode==MANUAL) fixedIndex=0; break;
    case IR_2: Serial.println("→ 2"); if(mode==MANUAL) fixedIndex=1; break;
    case IR_3: Serial.println("→ 3"); if(mode==MANUAL) fixedIndex=2; break;
    case IR_4: Serial.println("→ 4"); if(mode==MANUAL) fixedIndex=3; break;
    case IR_5: Serial.println("→ 5"); if(mode==MANUAL) fixedIndex=4; break;
    default:
      Serial.println("→ Unknown IR, ignored");
      break;
  }
}

void updateSystem(){
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  int light = analogRead(LDR_PIN);
  int pot = analogRead(POT_PIN);
  int fanP = 0;


  static Mode lastMode = OFF;



  // Mode LEDs
  digitalWrite(LED_OFF,    mode==OFF);
  digitalWrite(LED_AUTO,   mode==AUTO);
  digitalWrite(LED_MANUAL, mode==MANUAL);

  // Fan logic
  if (mode == OFF) {
    fanP = 0;
  }
  else if (mode == AUTO) {
    fanP = map(constrain((int)t,20,40),20,40,0,255);
    if (light>600) fanP = min(255,fanP+50);
    if (light<200) fanP = max(0,fanP-50);
    fanP = min(255,fanP + map((int)h,20,80,0,30));
  }
  else { // MANUAL
    fanP = fixedSpeeds[fixedIndex];
    if (pot > potOverrideThreshold) {
      fanP = map(pot,0,1023,0,255);
      Serial.print("MANUAL POT: "); Serial.println(fanP);
    } else {
      Serial.print("MANUAL FIXED: "); Serial.println(fanP);
    }
  }
  analogWrite(FAN_PIN, fanP);

  // RGB by temp
  int r = map(constrain((int)t,20,40),20,40,0,255);
  int g = 255 - r;
  analogWrite(RGB_R,r);
  analogWrite(RGB_G,g);
  analogWrite(RGB_B,0);



  // OLED display
  //lcd.clear();
  lcd.setCursor(0,0); lcd.print("Temp:"); lcd.print((int)t); lcd.print("C");
  lcd.setCursor(0,1); lcd.print("Hum: "); lcd.print((int)h); lcd.print("%");
  lcd.clearLine(2);
  lcd.setCursor(0,2); lcd.print("Fan: "); lcd.print(map(fanP,0,255,0,100)); lcd.print("%");
  lcd.clearLine(3);
  lcd.setCursor(0,3); lcd.print("Light: "); lcd.print(map(light,0,1023,0,100)); lcd.print("%");
  lcd.setCursor(0,4); 
  lcd.print("Mode:");
  if (mode==OFF)    lcd.print("OFFL");
  if (mode==AUTO)   lcd.print("AUTO");
  if (mode==MANUAL) lcd.print("MANL");


  Serial.print("MODE:");
  if (mode==OFF) Serial.println("OFF");
  else if (mode==AUTO) {
  Serial.println("AUTO");

  int tempVal = (int)t;
  int humVal = (int)h;
  int lightVal = map(light,0,1023,0,100);
  int fanVal = map(fanP,0,255,0,100);

  Serial.print("TEMP:"); Serial.print(tempVal); Serial.println("C");
  Serial.print("HUM:"); Serial.print(humVal); Serial.println("%");
  Serial.print("LIGHT:"); Serial.print(lightVal); Serial.println("%");
  Serial.print("FAN:"); Serial.print(fanVal); Serial.println("%");
}

  else if (mode==MANUAL) {
    Serial.println("MANUAL");
    int fanVal = map(fanP,0,255,0,100);
    if (pot > potOverrideThreshold) {
      Serial.print("FAN:POT="); Serial.print(fanVal); Serial.println("%");
    } else {
      Serial.print("FAN:FIXED="); Serial.print(fanVal); Serial.println("%");
    }
  }
}
