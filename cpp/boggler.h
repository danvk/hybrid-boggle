// Solver for MxN Boggle
#ifndef BOGGLER_4
#define BOGGLER_4

#include "constants.h"
#include "trie.h"

template <int M, int N>
class Boggler {
 public:
  Boggler(Trie* t) : dict_(t), runs_(0) {}

  int Score(const char* lets);

  unsigned int NumCells() { return M * N; }

  // Set a cell on the current board. Must have 0 <= x < M, 0 <= y < N and 0 <=
  // c < 26. These constraints are NOT checked.
  void SetCell(int x, int y, unsigned int c);
  unsigned int Cell(int x, int y) const;

  vector<vector<int>> FindWords(const string& lets, bool multiboggle);

 private:
  void DoDFS(unsigned int i, unsigned int len, Trie* t);
  void FindWordsDFS(
      unsigned int i, Trie* t, bool multiboggle, vector<vector<int>>& out
  );
  unsigned int InternalScore();
  bool ParseBoard(const char* bd);

  Trie* dict_;
  unsigned int used_;
  int bd_[M * N];
  unsigned int score_;
  unsigned int runs_;
  vector<int> seq_;
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
    fprintf(
        stderr,
        "Board strings must contain %d characters, got %zu ('%s')\n",
        expected_len,
        strlen(bd),
        bd
    );
    return false;
  }

  for (unsigned int i = 0; i < expected_len; i++) {
    if (bd[i] == '.') {
      bd_[i] = -1;  // explicit "do not go here"; only supported by FindWords()
      continue;
    }
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
  for (int i = 0; i < M * N; i++) {
    int c = bd_[i];
    if (dict_->StartsWord(c)) DoDFS(i, 0, dict_->Descend(c));
  }
  return score_;
}

#define REC(idx)                         \
  do {                                   \
    if ((used_ & (1 << idx)) == 0) {     \
      cc = bd_[idx];                     \
      if (t->StartsWord(cc)) {           \
        DoDFS(idx, len, t->Descend(cc)); \
      }                                  \
    }                                    \
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

// TODO: this could be an inline method
#define PREFIX()                  \
  int c = bd_[i], cc;             \
  used_ ^= (1 << i);              \
  len += (c == kQ ? 2 : 1);       \
  if (t->IsWord()) {              \
    if (t->Mark() != runs_) {     \
      t->Mark(runs_);             \
      score_ += kWordScores[len]; \
    }                             \
  }

#define SUFFIX() used_ ^= (1 << i)

// TODO: codegen specialized bogglers
// clang-format off

/*[[[cog
from boggle.neighbors import NEIGHBORS

for (w, h), neighbors in NEIGHBORS.items():
    print(f"""
// {w}x{h}
template<>
const int Boggler<{w}, {h}>::DoDFS(unsigned int i, unsigned int len, Trie* t) {{
  PREFIX();
  switch(i) {{""")
    for i, ns in enumerate(NEIGHBORS[(3, 3)]):
        csv = ", ".join(str(n) for n in ns)
        print(f"    case {i}: REC{len(ns)}({csv});")

    print(f"""  }
  SUFFIX();
}""")
]]]*/

// [[[end]]]
// clang-format on

template <int M, int N>
vector<vector<int>> Boggler<M, N>::FindWords(const string& lets, bool multiboggle) {
  seq_.clear();
  seq_.reserve(M * N);
  vector<vector<int>> out;
  if (!ParseBoard(lets.c_str())) {
    out.push_back({-1});
    return out;
  }

  runs_ = dict_->Mark() + 1;
  dict_->Mark(runs_);
  used_ = 0;
  score_ = 0;
  for (int i = 0; i < M * N; i++) {
    int c = bd_[i];
    if (c != -1 && dict_->StartsWord(c)) {
      FindWordsDFS(i, dict_->Descend(c), multiboggle, out);
    }
  }
  return out;
}

template <>
void Boggler<4, 4>::FindWordsDFS(
    unsigned int i, Trie* t, bool multiboggle, vector<vector<int>>& out
) {
  used_ ^= (1 << i);
  seq_.push_back(i);
  if (t->IsWord()) {
    if (t->Mark() != runs_ || multiboggle) {
      t->Mark(runs_);
      out.push_back(seq_);
    }
  }

  int cc, idx;

  // clang-format off
#define HIT(x,y) do { idx = (x) * 4 + y; \
  if ((used_ & (1 << idx)) == 0) { \
    cc = bd_[idx]; \
    if (cc != -1 && t->StartsWord(cc)) { \
      FindWordsDFS(idx, t->Descend(cc), multiboggle, out); \
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

#undef HIT
#undef HIT3x
#undef HIT3y
#undef HIT8
  // clang-format on
  used_ ^= (1 << i);
  seq_.pop_back();
}

#endif
