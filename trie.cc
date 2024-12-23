#include "trie.h"
#include <iostream>
#include <stdlib.h>
#include <queue>
#include <utility>
#include <map>

static inline int idx(char x) { return x - 'a'; }

// Initially, this node is empty
Trie::Trie() {
  for (int i=0; i<kNumLetters; i++)
    children_[i] = NULL;
  is_word_ = false;
  mark_ = 0;
}

Trie* Trie::AddWord(const char* wd) {
  if (!wd) return NULL;
  if (!*wd) {
    SetIsWord();
    return this;
  }
  int c = idx(*wd);
  if (!StartsWord(c))
    children_[c] = new Trie;
  return Descend(c)->AddWord(wd+1);
}

Trie::~Trie() {
  for (int i=0; i<kNumLetters; i++) {
    if (children_[i]) delete children_[i];
  }
}

size_t Trie::Size() {
  size_t size = 0;
  if (IsWord()) size++;
  for (int i=0; i<kNumLetters; i++) {
    if (StartsWord(i)) size += Descend(i)->Size();
  }
  return size;
}

size_t Trie::NumNodes() {
  int count = 1;
  for (int i = 0; i < kNumLetters; i++)
    if (StartsWord(i))
      count += Descend(i)->NumNodes();
  return count;
}

// static
bool Trie::ReverseLookup(const Trie* base, const Trie* child,
                         std::string* out) {
  if (base==child) return true;
  for (int i=0; i<kNumLetters; i++) {
    if (base->StartsWord(i) && ReverseLookup(base->Descend(i), child, out)) {
      *out = std::string(1,'a'+i) + *out;
      return true;
    }
  }
  return false;
}

// static
std::string Trie::ReverseLookup(const Trie* base, const Trie* child) {
  std::string out;
  ReverseLookup(base, child, &out);
  return out;
}

void Trie::SetAllMarks(unsigned mark) {
  if (IsWord()) Mark(mark);
  for (int i=0; i<kNumLetters; i++) {
    if (StartsWord(i)) Descend(i)->SetAllMarks(mark);
  }
}

Trie* Trie::FindWord(const char* wd) {
  if (!wd) return NULL;
  if (!*wd) {
    return IsWord() ? this : NULL;
  }
  int c = idx(*wd);
  if (!StartsWord(c)) return NULL;
  return Descend(c)->FindWord(wd + 1);
}

Trie* Trie::CreateFromFile(const char* filename) {
  Trie* t = new Trie;
  char line[80];
  FILE* f = fopen(filename, "r");
  if (!f) {
    fprintf(stderr, "Couldn't open %s\n", filename);
    delete t;
    return NULL;
  }

  while (!feof(f) && fscanf(f, "%s", line)) {
    t->AddWord(line);
  }
  fclose(f);

  return t;
}
