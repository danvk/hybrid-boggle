#include <cassert>
#include <cstdint>
#include <cstring>

#ifndef PACKED_ARRAY_H
#define PACKED_ARRAY_H

template <size_t N>
struct Packed5Array {
  // Use 6 bits per value (wastes 1 bit) but pack 4 values per 3 bytes
  // This gives perfect memcmp compatibility with reasonable space efficiency
  static constexpr size_t BitsPerValue = 6;
  static constexpr size_t ValuesPerGroup = 4;
  static constexpr size_t BytesPerGroup = 3;  // 4 * 6 = 24 bits = 3 bytes
  static constexpr size_t NumGroups = (N + ValuesPerGroup - 1) / ValuesPerGroup;
  static constexpr size_t TotalBytes = NumGroups * BytesPerGroup;

  uint8_t data[TotalBytes] = {0};

  void set(size_t index, uint8_t value) {
    assert(index < N);
    assert(value < 32);  // Must fit in 5 bits, stored in 6
    
    size_t group = index / ValuesPerGroup;
    size_t pos = index % ValuesPerGroup;
    size_t byte_offset = group * BytesPerGroup;
    
    // Pack 4 values into 3 bytes: [AAAAAA][BBBBBB] [CCCCCC][DDDDDD] [padding][padding]
    // Actually: [AAAAAABB][BBBBCCCC][CCDDDDDD] for better alignment
    switch (pos) {
      case 0:  // bits 7-2 of byte 0
        data[byte_offset] = (data[byte_offset] & 0x03) | (value << 2);
        break;
      case 1:  // bits 1-0 of byte 0, bits 7-4 of byte 1  
        data[byte_offset] = (data[byte_offset] & 0xFC) | (value >> 4);
        data[byte_offset + 1] = (data[byte_offset + 1] & 0x0F) | ((value & 0x0F) << 4);
        break;
      case 2:  // bits 3-0 of byte 1, bits 7-6 of byte 2
        data[byte_offset + 1] = (data[byte_offset + 1] & 0xF0) | (value >> 2);
        data[byte_offset + 2] = (data[byte_offset + 2] & 0x3F) | ((value & 0x03) << 6);
        break;
      case 3:  // bits 5-0 of byte 2
        data[byte_offset + 2] = (data[byte_offset + 2] & 0xC0) | (value & 0x3F);
        break;
    }
  }

  uint8_t get(size_t index) const {
    assert(index < N);
    
    size_t group = index / ValuesPerGroup;
    size_t pos = index % ValuesPerGroup;
    size_t byte_offset = group * BytesPerGroup;
    
    switch (pos) {
      case 0:  // bits 7-2 of byte 0
        return (data[byte_offset] >> 2) & 0x3F;
      case 1:  // bits 1-0 of byte 0, bits 7-4 of byte 1
        return ((data[byte_offset] & 0x03) << 4) | ((data[byte_offset + 1] >> 4) & 0x0F);
      case 2:  // bits 3-0 of byte 1, bits 7-6 of byte 2  
        return ((data[byte_offset + 1] & 0x0F) << 2) | ((data[byte_offset + 2] >> 6) & 0x03);
      case 3:  // bits 5-0 of byte 2
        return data[byte_offset + 2] & 0x3F;
      default:
        return 0;
    }
  }

  int compare(const Packed5Array<N>& other) const {
    return memcmp(data, other.data, TotalBytes);
  }
};

#endif  // PACKED_ARRAY_H
