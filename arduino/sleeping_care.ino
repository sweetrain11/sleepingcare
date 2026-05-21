// =============================================
// SleepingCare - 전체 센서 통합 스케치
// 센서: DHT11, CDS, PIR, 사운드, RTC(DS1302), HC-06
// 출력: JSON 포맷 (시리얼 + 블루투스)
// =============================================

#include <DHT.h>
#include <ThreeWire.h>                      // DS1302 의존 라이브러리
#include <RtcDS1302.h>                      // DS1302 전용 라이브러리
#include <SoftwareSerial.h>

// ---- 핀 설정 ----
#define DHT_PIN     4       // DHT11 DATA → D2
#define PIR_PIN     3       // PIR OUT   → D3
#define LIGHT_PIN   A0      // CDS AO    → A0
#define SOUND_PIN   A1      // 사운드 AO  → A1
#define BT_RX_PIN   10      // HC-06 TX  → D10
#define BT_TX_PIN   11      // HC-06 RX  → D11 (분압회로 필수)
#define RTC_CLK     6       // DS1302 CLK → D6
#define RTC_DAT     7       // DS1302 DAT → D7
#define RTC_RST     8       // DS1302 RST → D8

// ---- 센서 객체 ----
#define DHTTYPE DHT11
DHT dht(DHT_PIN, DHTTYPE);
ThreeWire myWire(RTC_DAT, RTC_CLK, RTC_RST);
RtcDS1302<ThreeWire> rtc(myWire);
SoftwareSerial bluetooth(BT_RX_PIN, BT_TX_PIN);

// ---- 읽기 주기 ----
const unsigned long INTERVAL = 2000;        // 2초마다 측정
unsigned long lastTime = 0;

void setup() {
  Serial.begin(9600);
  bluetooth.begin(9600);

  pinMode(PIR_PIN, INPUT);

  dht.begin();
  delay(2000);

  // RTC 초기화
  rtc.Begin();
  // 시간이 유효하지 않으면 컴파일 시각으로 초기화
  RtcDateTime compiled = RtcDateTime(__DATE__, __TIME__);
  if (!rtc.IsDateTimeValid() || !rtc.GetIsRunning()) {
    rtc.SetIsRunning(true);
    rtc.SetDateTime(compiled);
  }
}

void loop() {
  unsigned long now = millis();
  if (now - lastTime < INTERVAL) return;
  lastTime = now;

  // ---- 센서 값 읽기 ----
  float temp     = dht.readTemperature();
  float humidity = dht.readHumidity();
  int   light    = analogRead(LIGHT_PIN);   // 0(밝음) ~ 1023(어두움)
  int   sound    = analogRead(SOUND_PIN);   // 0 ~ 1023
  int   motion   = digitalRead(PIR_PIN);    // 0 or 1

  // DHT11 읽기 실패 시 재시도
  if (isnan(temp) || isnan(humidity)) {
    Serial.println("{\"error\":\"DHT read failed\"}");
    return;
  }

  // ---- RTC 시각 읽기 ----
  RtcDateTime now_dt = rtc.GetDateTime();
  char timeStr[20];
  // 형식: 2026-05-04T23:10:00
  snprintf(timeStr, sizeof(timeStr),
    "%04d-%02d-%02dT%02d:%02d:%02d",
    now_dt.Year(), now_dt.Month(),  now_dt.Day(),
    now_dt.Hour(), now_dt.Minute(), now_dt.Second()
  );

  // ---- JSON 조립 ----
  // 소수점 처리를 위해 직접 문자열 조합
  char jsonBuf[120];
  snprintf(jsonBuf, sizeof(jsonBuf),
    "{\"temp\":%.1f,\"humidity\":%.1f,\"light\":%d,\"sound\":%d,\"motion\":%d,\"time\":\"%s\"}",
    temp, humidity, light, sound, motion, timeStr
  );

  // ---- 출력 (시리얼 + 블루투스) ----
  Serial.println(jsonBuf);
  bluetooth.println(jsonBuf);
}