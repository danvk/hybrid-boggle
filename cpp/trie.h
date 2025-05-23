#ifndef TRIE_H__
#define TRIE_H__

#include <stdint.h>
#include <sys/types.h>

#include <cassert>
#include <iostream>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

using namespace std;

const int kNumLetters = 26;
const int kQ = 'q' - 'a';

// Simple Trie used for boostrapping the more compact variety.
class IndexedTrie {
 public:
  IndexedTrie();
  ~IndexedTrie();

  // Fast operations
  bool StartsWord(int i) const { return children_[i]; }
  IndexedTrie* Descend(int i) const { return children_[i]; }

  bool IsWord() const { return is_word_; }
  void SetIsWord() { is_word_ = true; }

  void SetWordId(uint32_t word_id) { word_id_ = word_id; }
  uint32_t WordId() const { return word_id_; }

  int NumChildren() {
    int count = 0;
    for (int i = 0; i < kNumLetters; i++) {
      if (children_[i]) count++;
    }
    return count;
  }
  int BytesNeeded();

  // Trie construction
  // Returns a pointer to the new Trie node at the end of the word.
  IndexedTrie* AddWord(const char* wd);

 private:
  bool is_word_;
  uint32_t word_id_;
  IndexedTrie* children_[26];
};

class Trie {
 public:
  Trie();
  ~Trie();

  // Fast operations
  bool StartsWord(int i) const { return (1 << i) & child_indices_; }

  // Requires: StartsWord(i)
  Trie* Descend(int i) const {
    // TODO: move the popcount to the boggler?
    auto index = std::popcount(child_indices_ & ((1 << i) - 1));
    // return children_[index];
    // return children_[i];
    auto offset = children_ + index * sizeof(Trie);
    auto child = (char*)this + offset;
    return (Trie*)child;
  }

  bool IsWord() const { return child_indices_ & (1 << 31); }
  void SetIsWord() { child_indices_ |= (1 << 31); }

  void SetWordId(uint32_t word_id) { word_id_ = word_id; }
  uint32_t WordId() const { return word_id_; }

  void Mark(uintptr_t m) { mark_ = m; }
  uintptr_t Mark() { return mark_; }

  // Trie construction
  static unique_ptr<Trie> CreateFromFile(const char* filename);
  static unique_ptr<Trie> CreateFromFileStr(const string& filename);

  // Some slower methods that operate on the entire Trie (not just a node).
  size_t Size();
  size_t NumNodes();
  void SetAllMarks(unsigned mark);
  void ResetMarks();
  Trie* FindWord(const char* wd);

  void CopyFromIndexedTrie(IndexedTrie& t, char** tip);
  static unique_ptr<Trie> CopyFromIndexedTrieBFS(IndexedTrie& root, char** tip);

  static bool ReverseLookup(const Trie* base, const Trie* child, string* out);
  static string ReverseLookup(const Trie* base, const Trie* child);

  // Replaces "qu" with "q" in-place; returns true if the word is a valid boggle word
  // (IsBoggleWord).
  static bool BogglifyWord(char* word);
  static bool IsBoggleWord(const char* word);

  static size_t SizeForNode(int num_children) {
    auto size = sizeof(Trie);
    // + num_children * sizeof(Trie::children_);
    auto offset = size % alignment_of<Trie>();
    if (offset) {
      size += (alignment_of<Trie>() - offset);
    }
    assert(size % alignment_of<Trie>() == 0);
    return size;
  }

// TODO: add back
//  private:
  uint32_t child_indices_;
  uint32_t word_id_;
  uint32_t children_;
  uintptr_t mark_;
};

#endif
