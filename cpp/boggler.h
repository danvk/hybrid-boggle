// Solver for MxN Boggle
#ifndef BOGGLER_4
#define BOGGLER_4

#include <bits/stdc++.h>
#include "board_class_boggler.h"
#include "constants.h"
#include "trie.h"

template <int M, int N>
class Boggler {
 public:
  Boggler(Trie* t) : dict_(t), runs_(0) {
    // Precompute the neighbors for each cell
    // NOTE: we lose information about the order of the neighbors
    for (int i = 0; i < M * N; i++) {
      auto& neighbors = BoardClassBoggler<M, N>::NEIGHBORS[i];
      auto n_neighbors = neighbors[0];
      neighbors_[i] = 0;
      for (int j = 1; j <= n_neighbors; j++) {
        neighbors_[i] |= (1 << neighbors[j]);
      }
    }
  }

  int Score(const char* lets);

  unsigned int NumCells() { return M * N; }

  // Set a cell on the current board. Must have 0 <= x < M, 0 <= y < N and 0 <=
  // c < 26. These constraints are NOT checked.
  void SetCell(int x, int y, unsigned int c);
  unsigned int Cell(int x, int y) const;

  // This is used by the web Boggle UI
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
  uint32_t neighbors_[M * N];
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

template<int M, int N>
void Boggler<M, N>::DoDFS(unsigned int i, unsigned int len, Trie* t) {
  used_ ^= (1 << i);
  int c = bd_[i];

  len += (c == kQ ? 2 : 1); 
  if (t->IsWord()) {
    if (t->Mark() != runs_) {
      t->Mark(runs_);
      score_ += kWordScores[len];
    }
  }

  uint32_t has_children = t->HasChildren();
  uint32_t unused_neighbors = neighbors_[i] & ~used_;
  while (unused_neighbors) {
    int idx = __builtin_ctz(unused_neighbors);
    unused_neighbors &= unused_neighbors - 1;
    int cc = bd_[idx];
    if (has_children & (1 << cc)) {
      DoDFS(idx, len, t->Descend(cc));
    }
  }
  used_ ^= (1 << i);
}

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

// This could be specialized, but it's not as performance-sensitive as DoDFS()
template <int M, int N>
void Boggler<M, N>::FindWordsDFS(
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

  auto& neighbors = BoardClassBoggler<M, N>::NEIGHBORS[i];
  auto n_neighbors = neighbors[0];
  for (int j = 1; j <= n_neighbors; j++) {
    auto idx = neighbors[j];
    if ((used_ & (1 << idx)) == 0) {
      int cc = bd_[idx];
      if (cc != -1 && t->StartsWord(cc)) {
        FindWordsDFS(idx, t->Descend(cc), multiboggle, out);
      }
    }
  }

  used_ ^= (1 << i);
  seq_.pop_back();
}

#endif  // BOGGLER_4
