// Minimal host test double, not an Arduino core or electrical simulation.
#pragma once
#include <cstdint>
#include <cstdio>
#include <string>
#define A0 0
#define DEFAULT 1
#define F(x) x
inline uint32_t hostTime = 0;
inline uint32_t micros() { return hostTime; }
inline void analogReference(int) {}
inline uint16_t analogRead(int) { return 512; }
struct SerialDouble {
  std::string input, output;
  int capacity = 64;
  void begin(int) {}
  int available() { return input.size(); }
  char read() { char c = input.front(); input.erase(0, 1); return c; }
  void println(const char* text) { output += std::string(text) + "\n"; }
  int availableForWrite() { return capacity; }
  void write(const uint8_t* text, int length) { output.append((const char*)text, length); }
};
inline SerialDouble Serial;
