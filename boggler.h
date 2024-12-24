// A solver for 4x4 Boggle (i.e. the usual type)
#ifndef BOGGLER_4
#define BOGGLER_4

#include "trie.h"

class Boggler {
 public:
  // Assumes ownership of the Trie. No other Boggler may modify the Trie after
  // this Boggler has been constructed using it.
  Boggler(Trie* t);
  virtual ~Boggler();

  int Score(const char* lets);

  // Set a cell on the current board. Must have 0 <= x, y < 4 and 0 <= c < 26.
  // These constraints are NOT checked.
  void SetCell(int x, int y, int c);  // { bd_[(x << 2) + y] = c; }
  int Cell(int x, int y) const;  // { return bd_[(x << 2) + y]; }

 private:
  void DoDFS(int i, int len, Trie* t);
  int InternalScore();
  bool ParseBoard(const char* bd);

  Trie* dict_;
  unsigned int used_;
  int bd_[16];
  int score_;
  unsigned int runs_;
};

#endif
