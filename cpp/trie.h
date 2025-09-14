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
  IndexedTrie* FindWordId(int word_id);

  int NumChildren() const {
    int count = 0;
    for (int i = 0; i < kNumLetters; i++) {
      if (children_[i]) count++;
    }
    return count;
  }
  int BytesNeeded() const;

  void Mark(uintptr_t m) {
    assert(m < (1L << 32));
    mark_ = m;
  }
  uintptr_t Mark() { return mark_; }

  // Trie construction
  // Returns a pointer to the new Trie node at the end of the word.
  IndexedTrie* AddWord(const char* wd);

  static bool ReverseLookup(
      const IndexedTrie* base, const IndexedTrie* child, string* out
  );
  static string ReverseLookup(const IndexedTrie* base, const IndexedTrie* child);

  // Some slower methods that operate on the entire Trie (not just a node).
  size_t Size();
  size_t NumNodes();
  void SetAllMarks(unsigned mark);
  IndexedTrie* FindWord(const char* wd);

  // Trie construction
  static unique_ptr<IndexedTrie> CreateFromFile(const char* filename);
  static unique_ptr<IndexedTrie> CreateFromFileStr(const string& filename);
  static unique_ptr<IndexedTrie> CreateFromWordlist(const vector<string>& words);

 private:
  bool is_word_;
  uint32_t word_id_;
  uint32_t mark_;
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
    return children_ + index;
    // auto child = (char*)this + offset;
    // return (Trie*)child;
  }

  bool IsWord() const { return child_indices_ & (1 << 31); }
  void SetIsWord() { child_indices_ |= (1 << 31); }

  void Mark(uintptr_t m) { mark_ = m; }
  uintptr_t Mark() { return mark_; }

  // Trie construction
  static unique_ptr<Trie> CreateFromFile(const char* filename);
  static unique_ptr<Trie> CreateFromFileStr(const string& filename);
  static unique_ptr<Trie> CreateFromWordlist(const vector<string>& words);

  // Some slower methods that operate on the entire Trie (not just a node).
  size_t Size();
  size_t NumNodes();
  void SetAllMarks(unsigned mark);
  void ResetMarks();
  Trie* FindWord(const char* wd);

  static bool ReverseLookup(const Trie* base, const Trie* child, string* out);
  static string ReverseLookup(const Trie* base, const Trie* child);

  static Trie* CopyFromIndexedTrieBFS(const IndexedTrie& root, char** tip);

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
  uint32_t mark_;
  Trie* children_;
};

/** Wrapper around Trie to manage the underlying buffer. */
class TrieHolder {
 public:
  ~TrieHolder() {
    cout << "freeing:" << (uintptr_t)buf_ << endl;
    free(buf_);
  }

  Trie* GetTrie() { return t_; }

  // Trie construction
  static TrieHolder* CompactTrie(const IndexedTrie& t);
  static unique_ptr<TrieHolder> CreateFromFile(const char* filename);
  static unique_ptr<TrieHolder> CreateFromFileStr(const string& filename);
  static unique_ptr<TrieHolder> CreateFromWordlist(const vector<string>& words);

 private:
  TrieHolder(Trie* t, char* buf) : t_(t), buf_(buf) {
    cout << "buf_: " << (uintptr_t)buf_ << endl;
  }

  Trie* t_;
  char* buf_;
};

#endif
