#include <cassert>
#include <cstdint>
#include <cstring>

#ifndef PACKED_ARRAY_H
#define PACKED_ARRAY_H

template <size_t N>
struct Packed5Array {
  static constexpr size_t NumBits = 5;
  static constexpr size_t TotalBits = NumBits * N;
  static constexpr size_t TotalBytes = (TotalBits + 7) / 8;

  uint8_t data[TotalBytes] = {0};

  void set(size_t index, uint8_t value) {
    assert(index < N);
    assert(value < 32);  // Must fit in 5 bits

    size_t bit_pos = index * NumBits;
    size_t byte_pos = bit_pos / 8;
    size_t bit_offset = bit_pos % 8;

    uint16_t temp = data[byte_pos];
    if (bit_offset > 3) {
      temp |= static_cast<uint16_t>(data[byte_pos + 1]) << 8;
    }

    temp &= ~(0x1F << bit_offset);         // Clear the 5 bits
    temp |= (value & 0x1F) << bit_offset;  // Set new value

    data[byte_pos] = temp & 0xFF;
    if (bit_offset > 3) {
      data[byte_pos + 1] = (temp >> 8) & 0xFF;
    }
  }

  uint8_t get(size_t index) const {
    assert(index < N);

    size_t bit_pos = index * NumBits;
    size_t byte_pos = bit_pos / 8;
    size_t bit_offset = bit_pos % 8;

    uint16_t temp = data[byte_pos];
    if (bit_offset > 3) {
      temp |= static_cast<uint16_t>(data[byte_pos + 1]) << 8;
    }

    return (temp >> bit_offset) & 0x1F;
  }

  int compare(const Packed5Array<N>& other) const {
    // return memcmp(data, other.data, TotalBytes);
    for (int i = 0; i < N; i++) {
      auto av = get(i);
      auto bv = other.get(i);
      if (av != bv) {
        return av < bv ? -1 : 1;
      }
    }
    return 0;
  }
};

#endif  // PACKED_ARRAY_H
