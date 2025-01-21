// Solver for MxN Boggle
#ifndef BOGGLER_4
#define BOGGLER_4

#include "trie.h"
#include "constants.h"

template <int M, int N>
class Boggler {
 public:
  Boggler(Trie* t) : dict_(t), runs_(0) {}

  int Score(const char* lets);

  unsigned int NumCells() { return M * N; }

  // Set a cell on the current board. Must have 0 <= x < M, 0 <= y < N and 0 <= c < 26.
  // These constraints are NOT checked.
  void SetCell(int x, int y, unsigned int c);
  unsigned int Cell(int x, int y) const;

 private:
  void DoDFS(unsigned int i, unsigned int len, Trie* t);
  unsigned int InternalScore();
  bool ParseBoard(const char* bd);

  Trie* dict_;
  unsigned int used_;
  int bd_[M*N];
  unsigned int score_;
  unsigned int runs_;
};

template <int M, int N>
void Boggler<M, N>::SetCell(int x, int y, unsigned int c) {
  bd_[(x * N) + y] = c;
}

template <int M, int N>
unsigned int Boggler<M, N>::Cell(int x, int y) const {
  return bd_[(x * N) + y];
}

template <int M, int N>
int Boggler<M, N>::Score(const char* lets) {
  if (!ParseBoard(lets)) {
    return -1;
  }
  return InternalScore();
}

template <int M, int N>
bool Boggler<M, N>::ParseBoard(const char* bd) {
  unsigned int expected_len = M * N;
  if (strlen(bd) != expected_len) {
    fprintf(stderr,
            "Board strings must contain %d characters, got %zu ('%s')\n",
            expected_len, strlen(bd), bd);
    return false;
  }

  for (unsigned int i = 0; i < expected_len; i++) {
    if (bd[i] >= 'A' && bd[i] <= 'Z') {
      fprintf(stderr, "Found uppercase letter '%c'\n", bd[i]);
      return false;
    } else if (bd[i] < 'a' || bd[i] > 'z') {
      fprintf(stderr, "Found unexpected letter: '%c'\n", bd[i]);
      return false;
    }
    bd_[i] = bd[i] - 'a';
  }
  return true;
}


template <int M, int N>
unsigned int Boggler<M, N>::InternalScore() {
  runs_ = dict_->Mark() + 1;
  dict_->Mark(runs_);
  used_ = 0;
  score_ = 0;
  for (int i = 0; i < M*N; i++) {
    int c = bd_[i];
    if (dict_->StartsWord(c))
      DoDFS(i, 0, dict_->Descend(c));
  }
  return score_;
}

// 3x3 Boggle

template <>
void Boggler<3, 3>::DoDFS(unsigned int i, unsigned int len, Trie* t) {
  int c = bd_[i];

  used_ ^= (1 << i);
  len += (c==kQ ? 2 : 1);
  if (t->IsWord()) {
    if (t->Mark() != runs_) {
      t->Mark(runs_);
      score_ += kWordScores[len];
    }
  }

  int cc, idx;

#define HIT(x,y) do { idx = (x) * 3 + y; \
                      if ((used_ & (1 << idx)) == 0) { \
                        cc = bd_[idx]; \
                        if (t->StartsWord(cc)) { \
                          DoDFS(idx, len, t->Descend(cc)); \
                        } \
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

  used_ ^= (1 << i);

#undef HIT
#undef HIT3x
#undef HIT3y
#undef HIT8
}

// 3x4 Boggle
template <>
void Boggler<3, 4>::DoDFS(unsigned int i, unsigned int len, Trie* t) {
  int c = bd_[i];

  used_ ^= (1 << i);
  len += (c==kQ ? 2 : 1);
  if (t->IsWord()) {
    if (t->Mark() != runs_) {
      t->Mark(runs_);
      score_ += kWordScores[len];
    }
  }

  int cc, idx;

#define HIT(x,y) do { idx = (x) * 4 + y; \
                      if ((used_ & (1 << idx)) == 0) { \
                        cc = bd_[idx]; \
                        if (t->StartsWord(cc)) { \
                          DoDFS(idx, len, t->Descend(cc)); \
                        } \
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

  used_ ^= (1 << i);

#undef HIT
#undef HIT3x
#undef HIT3y
#undef HIT8
}

// 4x4 Boggle

template <>
void Boggler<4, 4>::DoDFS(unsigned int i, unsigned int len, Trie* t) {
  int c = bd_[i];

  used_ ^= (1 << i);
  len += (c==kQ ? 2 : 1);
  if (t->IsWord()) {
    if (t->Mark() != runs_) {
      t->Mark(runs_);
      score_ += kWordScores[len];
    }
  }

  int cc, idx;

#define HIT(x,y) do { idx = (x) * 4 + y; \
                      if ((used_ & (1 << idx)) == 0) { \
                        cc = bd_[idx]; \
                        if (t->StartsWord(cc)) { \
                          DoDFS(idx, len, t->Descend(cc)); \
                        } \
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
  used_ ^= (1 << i);

#undef HIT
#undef HIT3x
#undef HIT3y
#undef HIT8
}

#endif
