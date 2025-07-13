#include <algorithm>
#include <tuple>
#include <vector>

#ifndef EQUAL_RANGES_H
#define EQUAL_RANGES_H

template <typename T, typename Compare>
std::vector<std::tuple<
    T,
    typename std::vector<T>::const_iterator,
    typename std::vector<T>::const_iterator>>
extract_equal_ranges(const std::vector<T>& sorted_vec, Compare comp) {
  using Iter = typename std::vector<T>::const_iterator;
  std::vector<std::tuple<T, Iter, Iter>> result;

  Iter current = sorted_vec.begin();
  Iter end = sorted_vec.end();

  while (current != end) {
    const T& value = *current;

    Iter lower = std::lower_bound(current, end, value, comp);
    Iter upper = std::upper_bound(lower, end, value, comp);

    result.emplace_back(value, lower, upper - 1);  // inclusive last iterator
    current = upper;
  }

  return result;
}

#endif  // EQUAL_RANGES_H
