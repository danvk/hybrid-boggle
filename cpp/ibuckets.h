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
inline unsigned int BucketBoggler<M, N>::DoAllDescents(unsigned int idx,
                                                       unsigned int len, Trie* t) {
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

// TODO: codegen specialized bogglers
// clang-format off

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

// clang-format on

#endif  // BUCKET_H
