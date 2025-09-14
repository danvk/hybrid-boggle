#include "trie.h"

#include <stdlib.h>

#include <cassert>
#include <cstring>
#include <iostream>
#include <map>
#include <queue>
#include <type_traits>
#include <utility>

using namespace std;

static inline int idx(char x) { return x - 'a'; }

// Initially, this node is empty
Trie::Trie() { mark_ = 0; }

Trie::~Trie() {}

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
bool IndexedTrie::ReverseLookup(
    const IndexedTrie* base, const IndexedTrie* child, string* out
) {
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

void Trie::ResetMarks() { SetAllMarks(0); }

static int bytes_allocated = 0;

Trie* Trie::CopyFromIndexedTrieBFS(const IndexedTrie& root, char** tip) {
  // copy from one tree to another in BFS
  // (current node, parent pointer, child index)
  queue<tuple<const IndexedTrie*, Trie*, int>> q;
  q.push({&root, nullptr, -1});
  Trie* compact_root = nullptr;
  while (!q.empty()) {
    // iterate layer by layer
    auto [node, parent, child_index] = q.front();
    q.pop();
    if (node == 0) {
      continue;
    }
    // copy the node to the new tree
    auto size = Trie::SizeForNode(node->NumChildren());
    bytes_allocated += size;
    auto compact_node = new (*tip) Trie;
    *tip += size;
    if (parent && child_index == 0) {  // Record the first child offset when it's added
      parent->children_ = (char*)compact_node - (char*)parent;
    }
    if (!parent) {
      compact_root = compact_node;
    }
    // add the children to the queue for the next level
    int num_children = 0;
    for (int i = 0; i < kNumLetters; i++) {
      if (node->StartsWord(i)) {
        compact_node->child_indices_ |= (1 << i);
        q.push(make_tuple(node->Descend(i), compact_node, num_children++));
      } else {
        // compact_node->children_[i] = 0;
        // q.push(make_tuple(nullptr, compact_node, num_children++));
      }
    }
    // compact_node->SetWordId(node->WordId());
    if (node->IsWord()) {
      compact_node->SetIsWord();
    }
  }

  return compact_root;
}

// static
string IndexedTrie::ReverseLookup(const IndexedTrie* base, const IndexedTrie* child) {
  string out;
  ReverseLookup(base, child, &out);
  return out;
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

IndexedTrie* IndexedTrie::FindWordId(int word_id) {
  if (IsWord() && word_id_ == word_id) {
    return this;
  }
  for (const auto& c : children_) {
    if (!c) continue;
    auto t = c->FindWordId(word_id);
    if (t) {
      return t;
    }
  }
  return nullptr;
}

unique_ptr<IndexedTrie> IndexedTrie::CreateFromFile(const char* filename) {
  char line[80];
  FILE* f = fopen(filename, "r");
  if (!f) {
    fprintf(stderr, "Couldn't open %s\n", filename);
    return NULL;
  }

  int count = 0;
  unique_ptr<IndexedTrie> t(new IndexedTrie);
  while (!feof(f) && fscanf(f, "%s", line)) {
    if (Trie::BogglifyWord(line)) {
      t->AddWord(line)->SetWordId(count++);
    }
  }
  fclose(f);

  return t;
}

unique_ptr<IndexedTrie> IndexedTrie::CreateFromFileStr(const string& filename) {
  return CreateFromFile(filename.c_str());
}

/* static */ bool Trie::IsBoggleWord(const char* wd) {
  int size = strlen(wd);
  if (size < 3) return false;
  for (int i = 0; i < size; ++i) {
    int c = wd[i];
    if (c < 'a' || c > 'z') return false;
    if (c == 'q' && (i + 1 >= size || wd[1 + i] != 'u')) return false;
  }
  return true;
}

/* static */ bool Trie::BogglifyWord(char* word) {
  if (!IsBoggleWord(word)) return false;
  int src, dst;
  for (src = 0, dst = 0; word[src]; src++, dst++) {
    word[dst] = word[src];
    if (word[src] == 'q') src += 1;
  }
  word[dst] = word[src];
  return true;
}

/* static */ unique_ptr<IndexedTrie> IndexedTrie::CreateFromWordlist(
    const vector<string>& words
) {
  int count = 0;
  unique_ptr<IndexedTrie> t(new IndexedTrie);
  for (const auto& word : words) {
    t->AddWord(word.c_str())->SetWordId(count++);  // words are pre-"bogglified"
  }
  return t;
}

// Initially, this node is empty
IndexedTrie::IndexedTrie() {
  for (int i = 0; i < kNumLetters; i++) children_[i] = NULL;
  is_word_ = false;
}

IndexedTrie* IndexedTrie::AddWord(const char* wd) {
  if (!wd) return NULL;
  if (!*wd) {
    SetIsWord();
    return this;
  }
  int c = idx(*wd);
  if (!StartsWord(c)) children_[c] = new IndexedTrie;
  return Descend(c)->AddWord(wd + 1);
}

IndexedTrie::~IndexedTrie() {
  // for (int i = 0; i < kNumLetters; i++) {
  //   if (children_[i]) delete children_[i];
  // }
}

int IndexedTrie::BytesNeeded() const {
  int bytes_needed = Trie::SizeForNode(NumChildren());
  // int bytes_needed = Trie::SizeForNode(26);
  for (int i = 0; i < kNumLetters; i++) {
    if (StartsWord(i)) bytes_needed += Descend(i)->BytesNeeded();
  }
  return bytes_needed;
}

/* static */ TrieHolder* TrieHolder::CompactTrie(const IndexedTrie& t) {
  auto bytes_needed = t.BytesNeeded();
  cout << "bytes_needed=" << bytes_needed << endl;
  auto buf = (char*)malloc(bytes_needed);
  auto base = buf;
  bytes_allocated = 0;

  auto compact_trie = Trie::CopyFromIndexedTrieBFS(t, &buf);
  cout << "allocated " << bytes_allocated << " bytes; sizeof(Trie) = " << sizeof(Trie)
       << "; alignment_of(Trie) = " << alignment_of<Trie>() << endl;

  cout << (uintptr_t)buf << endl;
  cout << (uintptr_t)(base + bytes_needed) << endl;
  assert(buf == base + bytes_needed);

  return new TrieHolder(compact_trie, buf);
}

/* static */ unique_ptr<TrieHolder> TrieHolder::CreateFromFile(const char* filename) {
  auto t = IndexedTrie::CreateFromFile(filename);
  return unique_ptr<TrieHolder>(CompactTrie(*t));
}

/* static */ unique_ptr<TrieHolder> TrieHolder::CreateFromFileStr(const string& filename
) {
  auto t = IndexedTrie::CreateFromFileStr(filename);
  return unique_ptr<TrieHolder>(CompactTrie(*t));
}

/* static */ unique_ptr<TrieHolder> TrieHolder::CreateFromWordlist(
    const vector<string>& words
) {
  auto t = IndexedTrie::CreateFromWordlist(words);
  return unique_ptr<TrieHolder>(CompactTrie(*t));
}
