#ifndef TRIE_H__
#define TRIE_H__

#include <stdint.h>
#include <sys/types.h>

#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

using namespace std;

const int kNumLetters = 26;
const int kQ = 'q' - 'a';

class Trie {
 public:
  Trie();
  ~Trie();

  // Fast operations
  bool StartsWord(int i) const { return children_[i]; }
  Trie* Descend(int i) const { return children_[i]; }

  bool IsWord() const { return is_word_; }
  void SetIsWord() { is_word_ = true; }
  // Bitmap of children, 1 << 0..25
  uint32_t HasChildren() const { return has_children_; }

  void Mark(uintptr_t m) { mark_ = m; }
  uintptr_t Mark() { return mark_; }

  // Trie construction
  // Returns a pointer to the new Trie node at the end of the word.
  Trie* AddWord(const char* wd);
  static unique_ptr<Trie> CreateFromFile(const char* filename);
  static unique_ptr<Trie> CreateFromFileStr(const string& filename);

  // Some slower methods that operate on the entire Trie (not just a node).
  size_t Size();
  size_t NumNodes();
  void SetAllMarks(unsigned mark);
  Trie* FindWord(const char* wd);

  static bool ReverseLookup(const Trie* base, const Trie* child, string* out);
  static string ReverseLookup(const Trie* base, const Trie* child);

  // Replaces "qu" with "q" in-place; returns true if the word is a valid boggle word
  // (IsBoggleWord).
  static bool BogglifyWord(char* word);
  static bool IsBoggleWord(const char* word);

 private:
  bool is_word_;
  uintptr_t mark_;
  Trie* children_[26];
  uint32_t has_children_;
};

#endif
