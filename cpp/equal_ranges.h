#include <algorithm>
#include <tuple>
#include <vector>

#ifndef EQUAL_RANGES_H
#define EQUAL_RANGES_H

template <typename T, typename Compare>
std::vector<std::tuple<T, size_t, size_t>> extract_equal_ranges(
    const std::vector<T>& sorted_vec, Compare comp
) {
  std::vector<std::tuple<T, size_t, size_t>> result;
  size_t n = sorted_vec.size();
  size_t i = 0;

  while (i < n) {
    const T& value = sorted_vec[i];

    // Lower bound: first element >= value
    auto lower =
        std::lower_bound(sorted_vec.begin() + i, sorted_vec.end(), value, comp);

    // Upper bound: first element > value
    auto upper = std::upper_bound(lower, sorted_vec.end(), value, comp);

    size_t first_index = std::distance(sorted_vec.begin(), lower);
    size_t last_index = std::distance(sorted_vec.begin(), upper) - 1;

    result.emplace_back(value, first_index, last_index);
    i = last_index + 1;
  }

  return result;
}

#endif  // EQUAL_RANGES_H
