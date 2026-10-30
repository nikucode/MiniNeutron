// MiniNeutron optical bench protocol v1. Reference target: Arduino Uno R3.
// Development firmware: must be compiled/flashed and measured on hardware.
// A0: phototransistor collector, 10 kohm pull-up to +5 V, emitter to GND.
// This is sampled telemetry, NOT servo control or a precision TOF trigger.
#include <Arduino.h>

const uint32_t PERIOD_US = 2000;  // nominal 500 samples/s
const uint32_t MAX_SLOTS = 10000;  // bounded 20 s session, restart with s
bool running = false;
uint32_t sequence = 0;
uint32_t nextSample = 0;

void setup() {
  Serial.begin(115200);
  analogReference(DEFAULT);
}

void loop() {
  if (Serial.available()) {
    const char command = Serial.read();
    if (command == 's') {
      running = true;
      sequence = 0;
      Serial.println(F("sample,timestamp_us,adc_raw"));
      nextSample = micros() + PERIOD_US;
    } else if (command == 'x') {
      running = false;
    }
  }
  if (!running) return;
  const uint32_t now = micros();
  if ((int32_t)(now - nextSample) < 0) return;
  // Skip missed slots rather than producing a burst of fictitious samples.
  // Gaps in sequence make scheduler/serial overruns visible downstream.
  const uint32_t missedSlots = (now - nextSample) / PERIOD_US;
  sequence += missedSlots;
  if (sequence >= MAX_SLOTS) {
    running = false;
    return;
  }
  nextSample += (missedSlots + 1) * PERIOD_US;
  const uint32_t timestamp = micros();  // start of analogRead, not exact ADC aperture
  const uint16_t value = analogRead(A0);
  char line[40];
  const int length = snprintf(line, sizeof(line), "%lu,%lu,%u\n",
                             (unsigned long)sequence,
                             (unsigned long)timestamp, (unsigned int)value);
  if (length > 0 && length < (int)sizeof(line) && Serial.availableForWrite() >= length) {
    Serial.write((const uint8_t*)line, length);
  }
  ++sequence;  // dropped transmission also leaves a visible gap
}
