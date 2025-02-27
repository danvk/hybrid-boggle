#include "trie.h"

#include <stdlib.h>

#include <iostream>
#include <map>
#include <queue>
#include <utility>

using namespace std;

static inline int idx(char x) { return x - 'a'; }

// Initially, this node is empty
Trie::Trie() {
  for (int i = 0; i < kNumLetters; i++) children_[i] = NULL;
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
  if (!StartsWord(c)) children_[c] = new Trie;
  return Descend(c)->AddWord(wd + 1);
}

Trie::~Trie() {
  for (int i = 0; i < kNumLetters; i++) {
    if (children_[i]) delete children_[i];
  }
}

size_t Trie::Size() {
  size_t size = 0;
  if (IsWord()) size++;
  for (int i = 0; i < kNumLetters; i++) {
    if (StartsWord(i)) size += Descend(i)->Size();
  }
  return size;
}

size_t Trie::NumNodes() {
  int count = 1;
  for (int i = 0; i < kNumLetters; i++)
    if (StartsWord(i)) count += Descend(i)->NumNodes();
  return count;
}

// static
bool Trie::ReverseLookup(const Trie* base, const Trie* child, string* out) {
  if (base == child) return true;
  for (int i = 0; i < kNumLetters; i++) {
    if (base->StartsWord(i) && ReverseLookup(base->Descend(i), child, out)) {
      *out = string(1, 'a' + i) + *out;
      return true;
    }
  }
  return false;
}

// static
string Trie::ReverseLookup(const Trie* base, const Trie* child) {
  string out;
  ReverseLookup(base, child, &out);
  return out;
}

void Trie::SetAllMarks(unsigned mark) {
  if (IsWord()) Mark(mark);
  for (int i = 0; i < kNumLetters; i++) {
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

unique_ptr<Trie> Trie::CreateFromFile(const char* filename) {
  char line[80];
  FILE* f = fopen(filename, "r");
  if (!f) {
    fprintf(stderr, "Couldn't open %s\n", filename);
    return NULL;
  }

  unique_ptr<Trie> t(new Trie);
  while (!feof(f) && fscanf(f, "%s", line)) {
    t->AddWord(line);
  }
  fclose(f);

  return t;
}

unique_ptr<Trie> Trie::CreateFromFileWithGrouping(
    const char* filename, unordered_map<char, char> letter_grouping) {
  char line[80];
  FILE* f = fopen(filename, "r");
  if (!f) {
    fprintf(stderr, "Couldn't open %s\n", filename);
    return NULL;
  }

  unique_ptr<Trie> t(new Trie);
  while (!feof(f) && fscanf(f, "%s", line)) {
    for (int i = 0; line[i]; i++) {
      line[i] = letter_grouping[line[i]];
    }
    t->AddWord(line);
  }
  fclose(f);

  return t;
}
