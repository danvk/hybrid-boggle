#include <stdint.h>

#ifndef BOARD_CLASS_BOGGLER_H
#define BOARD_CLASS_BOGGLER_H

template<int M, int N>
class BoardClassBoggler {
 public:
  BoardClassBoggler(Trie* t) : dict_(t) {}
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

  static const int NEIGHBORS[M*N][9];
  static const int SPLIT_ORDER[M*N];

  protected:
   Trie* dict_;
   char bd_[M*N][27];  // null-terminated lists of possible letters
   unsigned int used_;
   char board_rep_[27*M*N];  // for as_string()
};

// For debugging:
static const bool PrintWords  = false;

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
  for (int i = 0; i < M*N; i++)
    reps *= strlen(bd_[i]);
  return reps;
}

template <int M, int N>
const char* BoardClassBoggler<M, N>::as_string() {
  char* c = board_rep_;
  for (int i=0; i<M*N; i++) {
    if (*bd_[i]) {
      strcpy(c, bd_[i]);
      c += strlen(bd_[i]);
    } else {
      strcpy(c++, ".");
    }
    *c++ = (i == (M*N-1) ? '\0' : ' ');
  }
  return board_rep_;
}


// Generated via:
// poetry run python -m boggle.neighbors
// First entry is the number of neighbors in the list.

// 2x2
template<>
const int BoardClassBoggler<2, 2>::NEIGHBORS[2*2][9] = {
  {3, 1, 2, 3},
  {3, 0, 2, 3},
  {3, 0, 1, 3},
  {3, 0, 1, 2},
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

// poetry run python -m boggle.split_order
template<>
const int BoardClassBoggler<2, 2>::SPLIT_ORDER[2*2] = {0, 1, 2, 3};

template<>
const int BoardClassBoggler<3, 3>::SPLIT_ORDER[3*3] = {4, 5, 3, 1, 7, 0, 2, 6, 8};

template<>
const int BoardClassBoggler<3, 4>::SPLIT_ORDER[3*4] = {5, 6, 1, 9, 2, 10, 4, 7, 0, 8, 3, 11};

template<>
const int BoardClassBoggler<4, 4>::SPLIT_ORDER[4*4] = {5, 6, 9, 10, 1, 13, 2, 14, 4, 7, 8, 11, 0, 12, 3, 15};


#endif  // BOARD_CLASS_BOGGLER_H
