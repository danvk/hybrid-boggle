#include <stdint.h>

#ifndef BOARD_CLASS_BOGGLER_H
#define BOARD_CLASS_BOGGLER_H

#include "trie.h"

// TODO: templating on M, N probably isn't that helpful here, or on any
// implementations except BucketBoggler.
template <int M, int N>
class BoardClassBoggler {
 public:
  BoardClassBoggler(Trie* t) : dict_(t), used_(0) {}
  virtual ~BoardClassBoggler() {}

  // bd is a class of boards with cells delimited by spaces.
  // examples:
  // "a b c d e f g h i j k l m n o p"
  // "aeiou bcdfghjklmnprstvwxyz aeiou ..."
  // NOTE: "qu" gets interpreted as "qu" or "u".
  bool ParseBoard(const char* bd);
  const char* as_string();

  // Returns the number of individual boards in the current board class. This
  // isn't guaranteed to fit in a uint64_t, but will for any class you care to
  // evaluate.
  uint64_t NumReps() const;

  // TODO: move these into a new, standalone header file
  static const int NEIGHBORS[M * N][9];
  static const int SPLIT_ORDER[M * N];

 protected:
  Trie* dict_;
  char bd_[M * N][27];  // null-terminated lists of possible letters
  unsigned int used_;
  char board_rep_[27 * M * N];  // for as_string()
};

// For debugging:
static const bool PrintWords = false;

template <int M, int N>
bool BoardClassBoggler<M, N>::ParseBoard(const char* bd) {
  int max_len = M * N - 1;
  int cell = 0;
  int cell_pos = 0;
  while (char c = *bd++) {
    if (c == ' ') {
      if (cell_pos == 0) return false;  // empty cell
      bd_[cell][cell_pos] = '\0';
      cell += 1;
      cell_pos = 0;
      if (cell > max_len) return false;  // too many cells
    } else if (c == '.') {
      // explicit "don't go here" cell, useful for tests
      bd_[cell][0] = '\0';
      cell_pos = 1;
    } else {
      if (c < 'a' || c > 'z') return false;  // invalid letter
      bd_[cell][cell_pos++] = c;
      if (cell_pos >= 27) return false;  // too many letters on a cell
    }
  }
  bd_[cell][cell_pos] = '\0';
  return (cell_pos > 0 && cell == max_len);
}

template <int M, int N>
uint64_t BoardClassBoggler<M, N>::NumReps() const {
  uint64_t reps = 1;
  for (int i = 0; i < M * N; i++) reps *= strlen(bd_[i]);
  return reps;
}

template <int M, int N>
const char* BoardClassBoggler<M, N>::as_string() {
  char* c = board_rep_;
  for (int i = 0; i < M * N; i++) {
    if (*bd_[i]) {
      strcpy(c, bd_[i]);
      c += strlen(bd_[i]);
    } else {
      strcpy(c++, ".");
    }
    *c++ = (i == (M * N - 1) ? '\0' : ' ');
  }
  return board_rep_;
}

// Update the blocks below via
// poetry run cog -r -P cpp/board_class_boggler.h

// First entry is the number of neighbors in the list.
// TODO: make these null-terminated rather than "pascal arrays" (may be faster).

// clang-format off

/*[[[cog
from boggle.neighbors import NEIGHBORS

for (w, h), neighbors in NEIGHBORS.items():
    print(f"""
// {w}x{h}
template<>
const int BoardClassBoggler<{w}, {h}>::NEIGHBORS[{w}*{h}][9] = {{""")
    for ns in neighbors:
        ns_str = ", ".join(str(n) for n in ns)
        print(f"  {{{len(ns)}, {ns_str}}},")

    print("};")
]]]*/

// 2x2
template<>
const int BoardClassBoggler<2, 2>::NEIGHBORS[2*2][9] = {
  {3, 1, 2, 3},
  {3, 0, 2, 3},
  {3, 0, 1, 3},
  {3, 0, 1, 2},
};

// 2x3
template<>
const int BoardClassBoggler<2, 3>::NEIGHBORS[2*3][9] = {
  {3, 1, 3, 4},
  {5, 0, 2, 3, 4, 5},
  {3, 1, 4, 5},
  {3, 0, 1, 4},
  {5, 0, 1, 2, 3, 5},
  {3, 1, 2, 4},
};

// 3x3
template<>
const int BoardClassBoggler<3, 3>::NEIGHBORS[3*3][9] = {
  {3, 1, 3, 4},
  {5, 0, 2, 3, 4, 5},
  {3, 1, 4, 5},
  {5, 0, 1, 4, 6, 7},
  {8, 0, 1, 2, 3, 5, 6, 7, 8},
  {5, 1, 2, 4, 7, 8},
  {3, 3, 4, 7},
  {5, 3, 4, 5, 6, 8},
  {3, 4, 5, 7},
};

// 3x4
template<>
const int BoardClassBoggler<3, 4>::NEIGHBORS[3*4][9] = {
  {3, 1, 4, 5},
  {5, 0, 2, 4, 5, 6},
  {5, 1, 3, 5, 6, 7},
  {3, 2, 6, 7},
  {5, 0, 1, 5, 8, 9},
  {8, 0, 1, 2, 4, 6, 8, 9, 10},
  {8, 1, 2, 3, 5, 7, 9, 10, 11},
  {5, 2, 3, 6, 10, 11},
  {3, 4, 5, 9},
  {5, 4, 5, 6, 8, 10},
  {5, 5, 6, 7, 9, 11},
  {3, 6, 7, 10},
};

// 4x4
template<>
const int BoardClassBoggler<4, 4>::NEIGHBORS[4*4][9] = {
  {3, 1, 4, 5},
  {5, 0, 2, 4, 5, 6},
  {5, 1, 3, 5, 6, 7},
  {3, 2, 6, 7},
  {5, 0, 1, 5, 8, 9},
  {8, 0, 1, 2, 4, 6, 8, 9, 10},
  {8, 1, 2, 3, 5, 7, 9, 10, 11},
  {5, 2, 3, 6, 10, 11},
  {5, 4, 5, 9, 12, 13},
  {8, 4, 5, 6, 8, 10, 12, 13, 14},
  {8, 5, 6, 7, 9, 11, 13, 14, 15},
  {5, 6, 7, 10, 14, 15},
  {3, 8, 9, 13},
  {5, 8, 9, 10, 12, 14},
  {5, 9, 10, 11, 13, 15},
  {3, 10, 11, 14},
};

// 4x5
template<>
const int BoardClassBoggler<4, 5>::NEIGHBORS[4*5][9] = {
  {3, 1, 5, 6},
  {5, 0, 2, 5, 6, 7},
  {5, 1, 3, 6, 7, 8},
  {5, 2, 4, 7, 8, 9},
  {3, 3, 8, 9},
  {5, 0, 1, 6, 10, 11},
  {8, 0, 1, 2, 5, 7, 10, 11, 12},
  {8, 1, 2, 3, 6, 8, 11, 12, 13},
  {8, 2, 3, 4, 7, 9, 12, 13, 14},
  {5, 3, 4, 8, 13, 14},
  {5, 5, 6, 11, 15, 16},
  {8, 5, 6, 7, 10, 12, 15, 16, 17},
  {8, 6, 7, 8, 11, 13, 16, 17, 18},
  {8, 7, 8, 9, 12, 14, 17, 18, 19},
  {5, 8, 9, 13, 18, 19},
  {3, 10, 11, 16},
  {5, 10, 11, 12, 15, 17},
  {5, 11, 12, 13, 16, 18},
  {5, 12, 13, 14, 17, 19},
  {3, 13, 14, 18},
};

// 5x5
template<>
const int BoardClassBoggler<5, 5>::NEIGHBORS[5*5][9] = {
  {3, 1, 5, 6},
  {5, 0, 2, 5, 6, 7},
  {5, 1, 3, 6, 7, 8},
  {5, 2, 4, 7, 8, 9},
  {3, 3, 8, 9},
  {5, 0, 1, 6, 10, 11},
  {8, 0, 1, 2, 5, 7, 10, 11, 12},
  {8, 1, 2, 3, 6, 8, 11, 12, 13},
  {8, 2, 3, 4, 7, 9, 12, 13, 14},
  {5, 3, 4, 8, 13, 14},
  {5, 5, 6, 11, 15, 16},
  {8, 5, 6, 7, 10, 12, 15, 16, 17},
  {8, 6, 7, 8, 11, 13, 16, 17, 18},
  {8, 7, 8, 9, 12, 14, 17, 18, 19},
  {5, 8, 9, 13, 18, 19},
  {5, 10, 11, 16, 20, 21},
  {8, 10, 11, 12, 15, 17, 20, 21, 22},
  {8, 11, 12, 13, 16, 18, 21, 22, 23},
  {8, 12, 13, 14, 17, 19, 22, 23, 24},
  {5, 13, 14, 18, 23, 24},
  {3, 15, 16, 21},
  {5, 15, 16, 17, 20, 22},
  {5, 16, 17, 18, 21, 23},
  {5, 17, 18, 19, 22, 24},
  {3, 18, 19, 23},
};
// [[[end]]]


/*[[[cog
from boggle.split_order import SPLIT_ORDER

for (w, h), split_order in SPLIT_ORDER.items():
    print(
        f"""
template<>
const int BoardClassBoggler<{w}, {h}>::SPLIT_ORDER[{w}*{h}] = {{%s}};"""
        % ", ".join(str(x) for x in split_order)
    )
]]]*/

template<>
const int BoardClassBoggler<2, 2>::SPLIT_ORDER[2*2] = {0, 1, 2, 3};

template<>
const int BoardClassBoggler<2, 3>::SPLIT_ORDER[2*3] = {0, 1, 2, 3, 4, 5};

template<>
const int BoardClassBoggler<3, 3>::SPLIT_ORDER[3*3] = {4, 5, 3, 1, 7, 0, 2, 6, 8};

template<>
const int BoardClassBoggler<3, 4>::SPLIT_ORDER[3*4] = {5, 6, 1, 9, 2, 10, 4, 7, 0, 8, 3, 11};

template<>
const int BoardClassBoggler<4, 4>::SPLIT_ORDER[4*4] = {5, 6, 9, 10, 1, 13, 2, 14, 4, 7, 8, 11, 0, 12, 3, 15};

template<>
const int BoardClassBoggler<4, 5>::SPLIT_ORDER[4*5] = {7, 12, 6, 11, 8, 13, 2, 17, 5, 10, 1, 3, 16, 18, 9, 14, 0, 15, 4, 19};

template<>
const int BoardClassBoggler<5, 5>::SPLIT_ORDER[5*5] = {12, 7, 11, 17, 13, 6, 8, 16, 18, 2, 10, 22, 14, 5, 15, 1, 3, 9, 19, 21, 23, 0, 20, 4, 24};
//[[[end]]]

// clang-format on

#endif  // BOARD_CLASS_BOGGLER_H
