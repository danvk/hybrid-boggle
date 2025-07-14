#include <cassert>
#include <tuple>
#include <vector>

#ifndef EQUAL_RANGES_H
#define EQUAL_RANGES_H

// Port of Python equal_ranges(xs, a, b) to C++
// xs must be sorted, [a, b) is the range to process
// Returns vector of (value, start, end) where start/end are indices into xs
template <typename T>
std::vector<std::tuple<T, int, int>> equal_ranges(
    const std::vector<T>& xs, int a, int b
) {
  std::vector<std::tuple<T, int, int>> result;
  if (a >= b) return result;
  T first = xs[a];
  T last = xs[b - 1];
  if (first == last) {
    result.emplace_back(first, a, b);
    return result;
  }
  if (b - a == 2) {
    result.emplace_back(first, a, a + 1);
    result.emplace_back(last, a + 1, b);
    return result;
  }
  int mid_idx = a + ((b - a) / 2);
  T mid = xs[mid_idx];
  if (mid == first) {
    // Find equal_ranges for the second half and add to the first range.
    auto ranges = equal_ranges(xs, mid_idx, b);
    auto& first_range = ranges[0];
    assert(std::get<0>(first_range) == mid);
    assert(std::get<1>(first_range) == mid_idx);
    std::get<1>(first_range) = a;
    result = std::move(ranges);
    return result;
  } else if (mid == last) {
    // Find equal ranges for the back half and add to the last range
    auto ranges = equal_ranges(xs, a, mid_idx + 1);
    auto& last_range = ranges.back();
    assert(std::get<0>(last_range) == mid);
    assert(std::get<2>(last_range) == mid_idx + 1);
    std::get<2>(last_range) = b;
    result = std::move(ranges);
    return result;
  } else {
    // Search both halves and smoosh them together
    auto low_ranges = equal_ranges(xs, a, mid_idx + 1);
    auto hi_ranges = equal_ranges(xs, mid_idx, b);
    assert(mid == std::get<0>(low_ranges.back()));
    assert(std::get<0>(low_ranges.back()) == std::get<0>(hi_ranges.front()));
    assert(std::get<2>(low_ranges.back()) == std::get<1>(hi_ranges.front()) + 1);

    // Merge the last of low_ranges and first of hi_ranges
    std::vector<std::tuple<T, int, int>> merged;
    merged.reserve(low_ranges.size() + hi_ranges.size() - 1);
    merged.insert(merged.end(), low_ranges.begin(), low_ranges.end() - 1);
    merged.emplace_back(
        mid, std::get<1>(low_ranges.back()), std::get<2>(hi_ranges.front())
    );
    merged.insert(merged.end(), hi_ranges.begin() + 1, hi_ranges.end());
    return merged;
  }
}

#endif  // EQUAL_RANGES_H
