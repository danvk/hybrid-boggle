// Calculate upper bounds on boggle boards with multiple possible letters on
// each square. This can be quite CPU-intensive.
#include <limits.h>
#include <string.h>

#include <algorithm>
#include <iostream>

#include "board_class_boggler.h"
#include "constants.h"
#include "trie.h"

#ifndef BUCKET_H
#define BUCKET_H

// See https://www.danvk.org/wp/2009-08-11/some-maxno-mark-examples/
struct ScoreDetails {
  int max_nomark;    // select the maximizing letter at each juncture.
  int sum_union;     // all words that can be found, counting each once.
  int bailout_cell;  // how many cells were tried before hitting the bailout?
                     // -1=no bailout.
};

template <int M, int N>
class BucketBoggler : public BoardClassBoggler<M, N> {
 public:
  BucketBoggler(Trie* t) : BoardClassBoggler<M, N>(t), runs_(0) {}
  virtual ~BucketBoggler() {}

  // Returns a score >= the score of the best possible board to form with the
  // current possibilities for each cell. For more detailed statistics, call
  // BoundDetails(). Note that setting a bailout_score invalidates the
  // max_delta information in BoundDetails.
  const ScoreDetails& Details() const { return details_; };  // See below.

  // Compute an upper bound without any of the costly statistics.
  unsigned int UpperBound(unsigned int bailout_score = INT_MAX);

  // These are "dependent names", see
  // https://stackoverflow.com/a/1528010/388951.
  using BoardClassBoggler<M, N>::dict_;
  using BoardClassBoggler<M, N>::bd_;
  using BoardClassBoggler<M, N>::used_;

 private:
  uintptr_t runs_;
  ScoreDetails details_;
  unsigned int DoAllDescents(unsigned int idx, unsigned int len, Trie* t);
  unsigned int DoDFS(unsigned int i, unsigned int len, Trie* t);
  unsigned int CountWord(unsigned int i, unsigned int len, Trie* t);
};

template <int M, int N>
unsigned int BucketBoggler<M, N>::UpperBound(unsigned int bailout_score) {
  details_.max_nomark = 0;
  details_.sum_union = 0;
  details_.bailout_cell = -1;

  used_ = 0;
  runs_ = dict_->Mark() + 1;
  dict_->Mark(runs_);
  // TODO: reset marks & runs every 1B calls
  for (int i = 0; i < M * N; i++) {
    int max_score = DoAllDescents(i, 0, dict_);
    details_.max_nomark += max_score;
    // This is "&&" because we're interested in knowing if we've _failed_ to
    // establish a sufficiently-tight upper bound.
    if (details_.max_nomark > bailout_score && details_.sum_union > bailout_score) {
      details_.bailout_cell = i;
      break;
    }
  }

  return std::min(details_.max_nomark, details_.sum_union);
}

template <int M, int N>
inline unsigned int BucketBoggler<M, N>::DoAllDescents(
    unsigned int idx, unsigned int len, Trie* t
) {
  int max_score = 0;
  for (int j = 0; bd_[idx][j]; j++) {
    int cc = bd_[idx][j] - 'a';
    if (t->StartsWord(cc)) {
      int tscore = DoDFS(idx, len + (cc == kQ ? 2 : 1), t->Descend(cc));
      max_score = std::max(tscore, max_score);
    }
  }
  return max_score;
}

template <int M, int N>
unsigned int BucketBoggler<M, N>::DoDFS(unsigned int i, unsigned int len, Trie* t) {
  fprintf(stderr, "Not implemented for %dx%d\n", M, N);
  exit(1);
}

template <int M, int N>
unsigned int BucketBoggler<M, N>::CountWord(unsigned int i, unsigned int len, Trie* t) {
  unsigned int score = 0;
  if (t->IsWord()) {
    unsigned int word_score = kWordScores[len];
    score += word_score;
    if (PrintWords)
      printf(
          " +%2d (%d,%d) %s\n",
          word_score,
          i / 3,
          i % 3,
          Trie::ReverseLookup(dict_, t).c_str()
      );

    if (t->Mark() != runs_) {
      details_.sum_union += word_score;
      t->Mark(runs_);
    }
  }
  return score;
}

#define REC(idx)                           \
  do {                                     \
    if ((used_ & (1 << idx)) == 0) {       \
      score += DoAllDescents(idx, len, t); \
    }                                      \
  } while (0)

#define REC3(a, b, c) \
  REC(a);             \
  REC(b);             \
  REC(c)

#define REC5(a, b, c, d, e) \
  REC3(a, b, c);            \
  REC(d);                   \
  REC(e)

#define REC8(a, b, c, d, e, f, g, h) \
  REC5(a, b, c, d, e);               \
  REC3(f, g, h)

// clang-format off

/*[[[cog
from boggle.neighbors import NEIGHBORS

for (w, h), neighbors in NEIGHBORS.items():
    print(f"""
// {w}x{h}
template<>
unsigned int BucketBoggler<{w}, {h}>::DoDFS(unsigned int i, unsigned int len, Trie* t) {{
  unsigned int score = 0;
  used_ ^= (1 << i);
  switch(i) {{""")
    for i, ns in enumerate(neighbors):
        csv = ", ".join(str(n) for n in ns)
        print(f"    case {i}: REC{len(ns)}({csv}); break;")

    print("""  }
  score += CountWord(i, len, t);
  used_ ^= (1 << i);
  return score;
}""")
]]]*/

// 2x2
template<>
unsigned int BucketBoggler<2, 2>::DoDFS(unsigned int i, unsigned int len, Trie* t) {
  unsigned int score = 0;
  used_ ^= (1 << i);
  switch(i) {
    case 0: REC3(1, 2, 3); break;
    case 1: REC3(0, 2, 3); break;
    case 2: REC3(0, 1, 3); break;
    case 3: REC3(0, 1, 2); break;
  }
  score += CountWord(i, len, t);
  used_ ^= (1 << i);
  return score;
}

// 2x3
template<>
unsigned int BucketBoggler<2, 3>::DoDFS(unsigned int i, unsigned int len, Trie* t) {
  unsigned int score = 0;
  used_ ^= (1 << i);
  switch(i) {
    case 0: REC3(1, 3, 4); break;
    case 1: REC5(0, 2, 3, 4, 5); break;
    case 2: REC3(1, 4, 5); break;
    case 3: REC3(0, 1, 4); break;
    case 4: REC5(0, 1, 2, 3, 5); break;
    case 5: REC3(1, 2, 4); break;
  }
  score += CountWord(i, len, t);
  used_ ^= (1 << i);
  return score;
}

// 3x3
template<>
unsigned int BucketBoggler<3, 3>::DoDFS(unsigned int i, unsigned int len, Trie* t) {
  unsigned int score = 0;
  used_ ^= (1 << i);
  switch(i) {
    case 0: REC3(1, 3, 4); break;
    case 1: REC5(0, 2, 3, 4, 5); break;
    case 2: REC3(1, 4, 5); break;
    case 3: REC5(0, 1, 4, 6, 7); break;
    case 4: REC8(0, 1, 2, 3, 5, 6, 7, 8); break;
    case 5: REC5(1, 2, 4, 7, 8); break;
    case 6: REC3(3, 4, 7); break;
    case 7: REC5(3, 4, 5, 6, 8); break;
    case 8: REC3(4, 5, 7); break;
  }
  score += CountWord(i, len, t);
  used_ ^= (1 << i);
  return score;
}

// 3x4
template<>
unsigned int BucketBoggler<3, 4>::DoDFS(unsigned int i, unsigned int len, Trie* t) {
  unsigned int score = 0;
  used_ ^= (1 << i);
  switch(i) {
    case 0: REC3(1, 4, 5); break;
    case 1: REC5(0, 2, 4, 5, 6); break;
    case 2: REC5(1, 3, 5, 6, 7); break;
    case 3: REC3(2, 6, 7); break;
    case 4: REC5(0, 1, 5, 8, 9); break;
    case 5: REC8(0, 1, 2, 4, 6, 8, 9, 10); break;
    case 6: REC8(1, 2, 3, 5, 7, 9, 10, 11); break;
    case 7: REC5(2, 3, 6, 10, 11); break;
    case 8: REC3(4, 5, 9); break;
    case 9: REC5(4, 5, 6, 8, 10); break;
    case 10: REC5(5, 6, 7, 9, 11); break;
    case 11: REC3(6, 7, 10); break;
  }
  score += CountWord(i, len, t);
  used_ ^= (1 << i);
  return score;
}

// 4x4
template<>
unsigned int BucketBoggler<4, 4>::DoDFS(unsigned int i, unsigned int len, Trie* t) {
  unsigned int score = 0;
  used_ ^= (1 << i);
  switch(i) {
    case 0: REC3(1, 4, 5); break;
    case 1: REC5(0, 2, 4, 5, 6); break;
    case 2: REC5(1, 3, 5, 6, 7); break;
    case 3: REC3(2, 6, 7); break;
    case 4: REC5(0, 1, 5, 8, 9); break;
    case 5: REC8(0, 1, 2, 4, 6, 8, 9, 10); break;
    case 6: REC8(1, 2, 3, 5, 7, 9, 10, 11); break;
    case 7: REC5(2, 3, 6, 10, 11); break;
    case 8: REC5(4, 5, 9, 12, 13); break;
    case 9: REC8(4, 5, 6, 8, 10, 12, 13, 14); break;
    case 10: REC8(5, 6, 7, 9, 11, 13, 14, 15); break;
    case 11: REC5(6, 7, 10, 14, 15); break;
    case 12: REC3(8, 9, 13); break;
    case 13: REC5(8, 9, 10, 12, 14); break;
    case 14: REC5(9, 10, 11, 13, 15); break;
    case 15: REC3(10, 11, 14); break;
  }
  score += CountWord(i, len, t);
  used_ ^= (1 << i);
  return score;
}

// 5x5
template<>
unsigned int BucketBoggler<5, 5>::DoDFS(unsigned int i, unsigned int len, Trie* t) {
  unsigned int score = 0;
  used_ ^= (1 << i);
  switch(i) {
    case 0: REC3(1, 5, 6); break;
    case 1: REC5(0, 2, 5, 6, 7); break;
    case 2: REC5(1, 3, 6, 7, 8); break;
    case 3: REC5(2, 4, 7, 8, 9); break;
    case 4: REC3(3, 8, 9); break;
    case 5: REC5(0, 1, 6, 10, 11); break;
    case 6: REC8(0, 1, 2, 5, 7, 10, 11, 12); break;
    case 7: REC8(1, 2, 3, 6, 8, 11, 12, 13); break;
    case 8: REC8(2, 3, 4, 7, 9, 12, 13, 14); break;
    case 9: REC5(3, 4, 8, 13, 14); break;
    case 10: REC5(5, 6, 11, 15, 16); break;
    case 11: REC8(5, 6, 7, 10, 12, 15, 16, 17); break;
    case 12: REC8(6, 7, 8, 11, 13, 16, 17, 18); break;
    case 13: REC8(7, 8, 9, 12, 14, 17, 18, 19); break;
    case 14: REC5(8, 9, 13, 18, 19); break;
    case 15: REC5(10, 11, 16, 20, 21); break;
    case 16: REC8(10, 11, 12, 15, 17, 20, 21, 22); break;
    case 17: REC8(11, 12, 13, 16, 18, 21, 22, 23); break;
    case 18: REC8(12, 13, 14, 17, 19, 22, 23, 24); break;
    case 19: REC5(13, 14, 18, 23, 24); break;
    case 20: REC3(15, 16, 21); break;
    case 21: REC5(15, 16, 17, 20, 22); break;
    case 22: REC5(16, 17, 18, 21, 23); break;
    case 23: REC5(17, 18, 19, 22, 24); break;
    case 24: REC3(18, 19, 23); break;
  }
  score += CountWord(i, len, t);
  used_ ^= (1 << i);
  return score;
}
// [[[end]]]
// clang-format on

#undef REC
#undef REC3
#undef REC5
#undef REC8
#undef PREFIX
#undef SUFFIX

#endif  // BUCKET_H
