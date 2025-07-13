#include <algorithm>
#include <tuple>
#include <vector>

#ifndef EQUAL_RANGES_H
#define EQUAL_RANGES_H

template <typename Iter, typename Compare>
std::vector<std::tuple<typename std::iterator_traits<Iter>::value_type, Iter, Iter>>
extract_equal_ranges(Iter first, Iter last, Compare comp) {
  using T = typename std::iterator_traits<Iter>::value_type;
  std::vector<std::tuple<T, Iter, Iter>> result;

  while (first != last) {
    const T& value = *first;

    Iter lower = std::lower_bound(first, last, value, comp);
    Iter upper = std::upper_bound(lower, last, value, comp);

    result.emplace_back(value, lower, std::prev(upper));  // inclusive [lower, upper-1]
    first = upper;
  }

  return result;
}

#endif  // EQUAL_RANGES_H
