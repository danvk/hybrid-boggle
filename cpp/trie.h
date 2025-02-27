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

  void Mark(uintptr_t m) { mark_ = m; }
  uintptr_t Mark() { return mark_; }

  // Trie construction
  // Returns a pointer to the new Trie node at the end of the word.
  Trie* AddWord(const char* wd);
  static unique_ptr<Trie> CreateFromFile(const char* filename);
  static unique_ptr<Trie> CreateFromFileWithGrouping(
      const char* filename, unordered_map<char, char> letter_grouping
  );

  // Some slower methods that operate on the entire Trie (not just a node).
  size_t Size();
  size_t NumNodes();
  void SetAllMarks(unsigned mark);
  Trie* FindWord(const char* wd);

  static bool ReverseLookup(const Trie* base, const Trie* child, string* out);
  static string ReverseLookup(const Trie* base, const Trie* child);

 private:
  bool is_word_;
  uintptr_t mark_;
  Trie* children_[26];
};

#endif
