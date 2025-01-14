// Calculate upper bounds on boggle boards with multiple possible letters on
// each square. This can be quite CPU-intensive.
#include <limits.h>
#include "trie.h"

#ifndef BUCKET_H
#define BUCKET_H

// See https://www.danvk.org/wp/2009-08-11/some-maxno-mark-examples/
struct ScoreDetails {
  int max_nomark;  // select the maximizing letter at each juncture.
  int sum_union;   // all words that can be found, counting each once.
  int bailout_cell;  // how many cells were tried before hitting the bailout? -1=no bailout.
};

template <int M, int N>
class BucketBoggler {
 public:
  BucketBoggler(Trie* t) : dict_(t), runs_(0) {}
  virtual ~BucketBoggler() {}

  int NumCells() { return M * N; }

  // bd is a class of boards with cells delimited by spaces.
  // examples:
  // "a b c d e f g h i j k l m n o p"
  // "aeiou bcdfghjklmnprstvwxyz aeiou ..."
  // NOTE: "qu" gets interpreted as "qu" or "u".
  bool ParseBoard(const char* bd);
  const char* as_string();

  // Returns the possible characters in this cell. The result can be modified.
  char* Cell(unsigned int idx) { return bd_[idx]; }

  void SetCell(unsigned int idx, char* val);

  // Returns the number of individual boards in the current board class. This
  // isn't guaranteed to fit in a uint64_t, but will for any class you care to
  // evaluate.
  uint64_t NumReps() const;

  // Returns a score >= the score of the best possible board to form with the
  // current possibilities for each cell. For more detailed statistics, call
  // BoundDetails(). Note that setting a bailout_score invalidates the
  // max_delta information in BoundDetails.
  const ScoreDetails& Details() const { return details_; };  // See below.

  // Compute an upper bound without any of the costly statistics.
  unsigned int UpperBound(unsigned int bailout_score = INT_MAX);


  void PrintNeighbors() {
    for (int i = 0; i < M * N; i++) {
      printf("%d: ", i);
      for (int j = 1; j <= BucketBoggler<M, N>::NEIGHBORS[i][0]; j++) {
        printf("%d ", BucketBoggler<M, N>::NEIGHBORS[i][j]);
      }
      printf("\n");
    }
  }

 protected:
  Trie* dict_;
  uintptr_t runs_;
  char bd_[M*N][27];  // null-terminated lists of possible letters
  unsigned int used_;
  ScoreDetails details_;

  static const int NEIGHBORS[M*N][9];

 private:
  unsigned int DoAllDescents(unsigned int idx, unsigned int len, Trie* t);
  unsigned int DoDFS(unsigned int i, unsigned int len, Trie* t);

  char board_rep_[27*M*N];  // for as_string()
};

#include <algorithm>
#include <iostream>
#include <string.h>
using std::min;
using std::max;

// For debugging:
static const bool PrintWords  = false;

// There's only one "Qu" die, but we allow a board with many of Qus.
// This prevents reading uninitialized memory on words with lots of Qus, which
// can cause spuriously high scores.
const unsigned int kWordScores[] =
      //0, 1, 2, 3, 4, 5, 6, 7,  8,  9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20
      { 0, 0, 0, 1, 1, 2, 3, 5, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11 };

template <int M, int N>
bool BucketBoggler<M, N>::ParseBoard(const char* bd) {
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
uint64_t BucketBoggler<M, N>::NumReps() const {
  uint64_t reps = 1;
  for (int i = 0; i < M*N; i++)
    reps *= strlen(bd_[i]);
  return reps;
}

template <int M, int N>
const char* BucketBoggler<M, N>::as_string() {
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

template <int M, int N>
void BucketBoggler<M, N>::SetCell(unsigned int idx, char* val) {
  strcpy(bd_[idx], val);
}

template <int M, int N>
unsigned int BucketBoggler<M, N>::UpperBound(unsigned int bailout_score) {
  details_.max_nomark = 0;
  details_.sum_union = 0;
  details_.bailout_cell = -1;

  used_ = 0;
  // TODO:
  // - Reset marks & runs_ every 1B runs.
  // - Use the convention of marking the root node with the run count.
  runs_ += 1;
  for (int i = 0; i < M*N; i++) {
    int max_score = DoAllDescents(i, 0, dict_);
    details_.max_nomark += max_score;
    // This is "&&" because we're interested in knowing if we've _failed_ to
    // establish a sufficiently-tight upper bound.
    if (details_.max_nomark > bailout_score &&
        details_.sum_union > bailout_score) {
      details_.bailout_cell = i;
      break;
    }
  }

  return min(details_.max_nomark, details_.sum_union);
}

template <int M, int N>
inline unsigned int BucketBoggler<M, N>::DoAllDescents(unsigned int idx, unsigned int len, Trie* t) {
  int max_score = 0;
  for (int j = 0; bd_[idx][j]; j++) {
    int cc = bd_[idx][j] - 'a';
    if (t->StartsWord(cc)) {
      int tscore = DoDFS(idx, len + (cc==kQ ? 2 : 1), t->Descend(cc));
      max_score = max(tscore, max_score);
    }
  }
  return max_score;
}

template <int M, int N>
unsigned int BucketBoggler<M, N>::DoDFS(unsigned int i, unsigned int len, Trie* t) {
  fprintf(stderr, "Not implemented for %dx%d\n", M, N);
  exit(1);
}

// 3x3 Boggle

template<>
unsigned int BucketBoggler<3, 3>::DoDFS(unsigned int i, unsigned int len, Trie* t) {
  unsigned int score = 0;
  used_ ^= (1 << i);

// Using these macros avoids all kinds of branching.
  unsigned int idx;
#define HIT(x,y) do { idx = (x) * 3 + y; \
                      if ((used_ & (1 << idx)) == 0) { \
                        score += DoAllDescents(idx, len, t); \
                      } \
                    } while(0)
#define HIT3x(x,y) HIT(x,y); HIT(x+1,y); HIT(x+2,y)
#define HIT3y(x,y) HIT(x,y); HIT(x,y+1); HIT(x,y+2)
#define HIT8(x,y) HIT3x(x-1,y-1); HIT(x-1,y); HIT(x+1,y); HIT3x(x-1,y+1)

  // x*3 + y
  switch (i) {
    case 0*3 + 0: HIT(0, 1); HIT(1, 0); HIT(1, 1); break;
    case 0*3 + 1: HIT(0, 0); HIT3y(1, 0); HIT(0, 2); break;
    case 0*3 + 2: HIT(0, 1); HIT(1, 1); HIT(1, 2); break;

    case 1*3 + 0: HIT(0, 0); HIT(2, 0); HIT3x(0, 1); break;
    case 1*3 + 1: HIT8(1, 1); break;
    case 1*3 + 2: HIT3x(0, 1); HIT(0, 2); HIT(2, 2); break;

    case 2*3 + 0: HIT(1, 0); HIT(1, 1); HIT(2, 1); break;
    case 2*3 + 1: HIT3y(1, 0); HIT(2, 0); HIT(2, 2); break;
    case 2*3 + 2: HIT(1, 2); HIT(1, 1); HIT(2, 1); break;
  }

#undef HIT
#undef HIT3x
#undef HIT3y
#undef HIT8

  if (t->IsWord()) {
    unsigned int word_score = kWordScores[len];
    score += word_score;
    if (PrintWords)
      printf(" +%2d (%d,%d) %s\n", word_score, i/3, i%3,
            Trie::ReverseLookup(dict_, t).c_str());

    if (t->Mark() != runs_) {
      details_.sum_union += word_score;
      t->Mark(runs_);
    }
  }

  used_ ^= (1 << i);
  return score;
}

// 3x4 Boggle

template<>
unsigned int BucketBoggler<3, 4>::DoDFS(unsigned int i, unsigned int len, Trie* t) {
  unsigned int score = 0;
  used_ ^= (1 << i);

// Using these macros avoids all kinds of branching.
  unsigned int idx;
#define HIT(x,y) do { idx = (x) * 4 + y; \
                      if ((used_ & (1 << idx)) == 0) { \
                        score += DoAllDescents(idx, len, t); \
                      } \
                    } while(0)
#define HIT3x(x,y) HIT(x,y); HIT(x+1,y); HIT(x+2,y)
#define HIT3y(x,y) HIT(x,y); HIT(x,y+1); HIT(x,y+2)
#define HIT8(x,y) HIT3x(x-1,y-1); HIT(x-1,y); HIT(x+1,y); HIT3x(x-1,y+1)

  // x*4 + y
  switch (i) {
    case 0*4 + 0: HIT(0, 1); HIT(1, 0); HIT(1, 1); break;
    case 0*4 + 1: HIT(0, 0); HIT3y(1, 0); HIT(0, 2); break;
    case 0*4 + 2: HIT(0, 1); HIT3y(1, 1); HIT(0, 3); break;
    case 0*4 + 3: HIT(0, 2); HIT(1, 2); HIT(1, 3); break;

    case 1*4 + 0: HIT(0, 0); HIT(2, 0); HIT3x(0, 1); break;
    case 1*4 + 1: HIT8(1, 1); break;
    case 1*4 + 2: HIT8(1, 2); break;
    case 1*4 + 3: HIT3x(0, 2); HIT(0, 3); HIT(2, 3); break;

    case 2*4 + 0: HIT(1, 0); HIT(1, 1); HIT(2, 1); break;
    case 2*4 + 1: HIT3y(1, 0); HIT(2, 0); HIT(2, 2); break;
    case 2*4 + 2: HIT3y(1, 1); HIT(2, 1); HIT(2, 3); break;
    case 2*4 + 3: HIT(1, 3); HIT(1, 2); HIT(2, 2); break;
  }

#undef HIT
#undef HIT3x
#undef HIT3y
#undef HIT8

  if (t->IsWord()) {
    unsigned int word_score = kWordScores[len];
    score += word_score;
    if (PrintWords)
      printf(" +%2d (%d,%d) %s\n", word_score, i/4, i%4,
            Trie::ReverseLookup(dict_, t).c_str());

    if (t->Mark() != runs_) {
      details_.sum_union += word_score;
      t->Mark(runs_);
    }
  }

  used_ ^= (1 << i);
  return score;
}

// 4x4 Boggle

template<>
unsigned int BucketBoggler<4, 4>::DoDFS(unsigned int i, unsigned int len, Trie* t) {
  unsigned int score = 0;
  used_ ^= (1 << i);

  unsigned int idx;
#define HIT(x,y) do { idx = (x) * 4 + y; \
                      if ((used_ & (1 << idx)) == 0) { \
                        score += DoAllDescents(idx, len, t); \
                      } \
		                } while(0)
#define HIT3x(x,y) HIT(x,y); HIT(x+1,y); HIT(x+2,y)
#define HIT3y(x,y) HIT(x,y); HIT(x,y+1); HIT(x,y+2)
#define HIT8(x,y) HIT3x(x-1,y-1); HIT(x-1,y); HIT(x+1,y); HIT3x(x-1,y+1)

  switch (i) {
    case 0*4 + 0: HIT(0, 1); HIT(1, 0); HIT(1, 1); break;
    case 0*4 + 1: HIT(0, 0); HIT3y(1, 0); HIT(0, 2); break;
    case 0*4 + 2: HIT(0, 1); HIT3y(1, 1); HIT(0, 3); break;
    case 0*4 + 3: HIT(0, 2); HIT(1, 2); HIT(1, 3); break;

    case 1*4 + 0: HIT(0, 0); HIT(2, 0); HIT3x(0, 1); break;
    case 1*4 + 1: HIT8(1, 1); break;
    case 1*4 + 2: HIT8(1, 2); break;
    case 1*4 + 3: HIT3x(0, 2); HIT(0, 3); HIT(2, 3); break;

    case 2*4 + 0: HIT(1, 0); HIT(3, 0); HIT3x(1, 1); break;
    case 2*4 + 1: HIT8(2, 1); break;
    case 2*4 + 2: HIT8(2, 2); break;
    case 2*4 + 3: HIT3x(1, 2); HIT(1, 3); HIT(3, 3); break;

    case 3*4 + 0: HIT(2, 0); HIT(2, 1); HIT(3, 1); break;
    case 3*4 + 1: HIT3y(2, 0); HIT(3, 0); HIT(3, 2); break;
    case 3*4 + 2: HIT3y(2, 1); HIT(3, 1); HIT(3, 3); break;
    case 3*4 + 3: HIT(2, 2); HIT(3, 2); HIT(2, 3); break;
  }
#undef HIT
#undef HIT3x
#undef HIT3y
#undef HIT8

  if (t->IsWord()) {
    unsigned int word_score = kWordScores[len];
    score += word_score;
    if (PrintWords)
      printf(" +%2d (%d,%d) %s\n", word_score, i/4, i%4,
            Trie::ReverseLookup(dict_, t).c_str());

    if (t->Mark() != runs_) {
      details_.sum_union += word_score;
      t->Mark(runs_);
    }
  }

  used_ ^= (1 << i);
  return score;
}
// Generated via:
// poetry run python -m boggle.neighbors
// First entry is the number of neighbors in the list.

// 3x3
template<>
const int BucketBoggler<3, 3>::NEIGHBORS[3*3][9] = {
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
const int BucketBoggler<3, 4>::NEIGHBORS[3*4][9] = {
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
const int BucketBoggler<4, 4>::NEIGHBORS[4*4][9] = {
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

#endif  // BUCKET_H
