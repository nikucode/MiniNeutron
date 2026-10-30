#include <cassert>
#include "../../daq/hardware/optical_bench/optical_bench.ino"

int main() {
  setup();
  loop();
  assert(Serial.output.empty());  // no stream before explicit start
  Serial.input = "s";
  loop();
  assert(Serial.output == "sample,timestamp_us,adc_raw\n");
  Serial.output.clear();
  hostTime = 1999;
  loop();
  assert(Serial.output.empty());
  hostTime = 2000;
  loop();
  assert(Serial.output == "0,2000,512\n");
  hostTime = 8000;  // skip two slots, no burst/catch-up samples
  loop();
  assert(Serial.output.ends_with("3,8000,512\n"));
  Serial.capacity = 0;
  hostTime = 10000;
  loop();
  assert(Serial.output.ends_with("3,8000,512\n"));
  Serial.capacity = 64;
  hostTime = 12000;
  loop();
  assert(Serial.output.ends_with("5,12000,512\n"));
  Serial.input = "x";
  loop();
  assert(!running);
  hostTime = UINT32_MAX - 999;  // wrap next schedule to 1000
  Serial.input = "s";
  loop();
  Serial.output.clear();
  hostTime = 1000;
  loop();
  assert(Serial.output == "0,1000,512\n");
  hostTime = 20001000;  // reached bounded-session limit
  loop();
  assert(!running);
  assert(sequence >= MAX_SLOTS);
}
