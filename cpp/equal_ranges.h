#include <cassert>
#include <tuple>
#include <vector>

#ifndef EQUAL_RANGES_H
#define EQUAL_RANGES_H

// Port of Python equal_ranges(xs, a, b) to C++
// xs must be sorted, [a, b) is the range to process
// Returns vector of (value, start, end) where start/end are indices into xs
template <typename T>
std::vector<std::tuple<int, int, int>> equal_ranges(
    const std::vector<T>& xs, int offset, int a, int b
) {
  if (a >= b) return {};
  int first = xs[a].path[offset];
  int last = xs[b - 1].path[offset];

  if (first == last) {
    return {{first, a, b}};
  }
  if (b - a == 2) {
    return {{first, a, a + 1}, {last, a + 1, b}};
  }
  if (b - a < 128) {
    vector<tuple<int, int, int>> ranges;
    ranges.reserve(last - first + 1);
    int last_val = -1;
    for (int i = a; i < b; i++) {
      int v = xs[i].path[offset];
      if (v != last_val) {
        ranges.push_back({v, i, i + 1});
        last_val = v;
      } else {
        std::get<2>(*ranges.rbegin()) = i + 1;
      }
    }
    return ranges;
  }

  int mid_idx = a + ((b - a) / 2);
  int mid = xs[mid_idx].path[offset];
  if (mid == first) {
    // Find equal_ranges for the second half and add to the first range.
    auto ranges = equal_ranges(xs, offset, mid_idx, b);
    auto& first_range = ranges[0];
    assert(std::get<0>(first_range) == mid);
    assert(std::get<1>(first_range) == mid_idx);
    std::get<1>(first_range) = a;
    return ranges;
  } else if (mid == last) {
    // Find equal ranges for the back half and add to the last range
    auto ranges = equal_ranges(xs, offset, a, mid_idx + 1);
    auto& last_range = ranges.back();
    assert(std::get<0>(last_range) == mid);
    assert(std::get<2>(last_range) == mid_idx + 1);
    std::get<2>(last_range) = b;
    return ranges;
  } else {
    // Search both halves and smoosh them together
    auto low_ranges = equal_ranges(xs, offset, a, mid_idx + 1);
    auto hi_ranges = equal_ranges(xs, offset, mid_idx, b);
    assert(mid == std::get<0>(low_ranges.back()));
    assert(std::get<0>(low_ranges.back()) == std::get<0>(hi_ranges.front()));
    assert(std::get<2>(low_ranges.back()) == std::get<1>(hi_ranges.front()) + 1);

    // Merge the last of low_ranges and first of hi_ranges
    low_ranges.reserve(low_ranges.size() + hi_ranges.size() - 1);
    auto& last_range = low_ranges.back();
    std::get<2>(last_range) = std::get<2>(hi_ranges.front());
    low_ranges.insert(low_ranges.end(), hi_ranges.begin() + 1, hi_ranges.end());
    return low_ranges;
  }
}

#endif  // EQUAL_RANGES_H
