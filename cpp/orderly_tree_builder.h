#ifndef ORDERLY_TREE_BUILDER_H
#define ORDERLY_TREE_BUILDER_H

#include <array>

#include "constants.h"
#include "eval_node.h"
#include "ibuckets.h"

using namespace std;

template <int M, int N>
class OrderlyTreeBuilder : public BoardClassBoggler<M, N> {
 public:
  OrderlyTreeBuilder(Trie* t) : BoardClassBoggler<M, N>(t) {
    for (int i = 0; i < M * N; i++) {
      cell_to_order_[BucketBoggler<M, N>::SPLIT_ORDER[i]] = i;
    }
    used_ordered_ = 0;
  }
  virtual ~OrderlyTreeBuilder() {}

  // These are "dependent names", see
  // https://stackoverflow.com/a/1528010/388951.
  using BoardClassBoggler<M, N>::dict_;
  using BoardClassBoggler<M, N>::bd_;
  using BoardClassBoggler<M, N>::used_;

  /** Build an EvalTree for the current board. */
  const SumNode* BuildTree(EvalNodeArena& arena);

  unique_ptr<EvalNodeArena> CreateArena() { return create_eval_node_arena(); }

  // TODO: bitpack
  struct WordPath {
    array<uint8_t, 2 * M * N> path;
    uint32_t word_id;
    uint8_t points;
  };

 private:
  SumNode* root_;
  int cell_to_order_[M * N];
  unsigned int used_ordered_;  // used cells mapped to their split order
  int choices_[M * N];         // cell order -> letter index
  int num_letters_[M * N];
  int letter_counts_[26];  // TODO: don't need the count here, a 52-bit mask would work
  uint32_t dupe_mask_;
  vector<vector<uint32_t>> word_lists_;
  unsigned int num_overflow_;
  vector<WordPath> words_;

  void DoAllDescents(int cell, int n, int length, Trie* t, EvalNodeArena& arena);
  void DoDFS(int cell, int n, int length, Trie* t, EvalNodeArena& arena);
  void AddWord(int* choices, unsigned int used_ordered, uint32_t word_id, int length);

  static bool WordComparator(const WordPath& a, const WordPath& b);
};

template <int M, int N>
const SumNode* OrderlyTreeBuilder<M, N>::BuildTree(EvalNodeArena& arena) {
  auto start = chrono::high_resolution_clock::now();
  // cout << "alignment_of<EvalNode>=" << alignment_of<EvalNode>() << endl;
  root_ = arena.NewRootNodeWithCapacity(M * N);  // this will never be reallocated
  used_ = 0;

  word_lists_.clear();
  // word_lists_.reserve(1000);
  for (int i = 0; i < 26; i++) {
    letter_counts_[i] = 0;
  }
  dupe_mask_ = 0;
  num_overflow_ = 0;
  for (int cell = 0; cell < M * N; cell++) {
    num_letters_[cell] = strlen(bd_[cell]);
  }
  // word_lists_.push_back({});  // start with 1

  words_.clear();
  // words_.reserve(2 << 24);  // 16M word paths
  words_.reserve(36'000'000);

  for (int cell = 0; cell < M * N; cell++) {
    DoAllDescents(cell, 0, 0, dict_, arena);
  }
  auto root = root_;
  root_ = NULL;
  auto end1 = chrono::high_resolution_clock::now();
  auto duration = chrono::duration_cast<chrono::milliseconds>(end1 - start).count();
  cout << "Build word list: " << duration << " ms" << endl;

  sort(words_.begin(), words_.end(), WordComparator);
  auto end2 = chrono::high_resolution_clock::now();
  duration = chrono::duration_cast<chrono::milliseconds>(end2 - end1).count();
  cout << "sort list: " << duration << " ms" << endl;
  cout << "words_.size() = " << words_.size() << endl;

  auto unique_end =
      unique(words_.begin(), words_.end(), [](const auto& a, const auto& b) {
        return !WordComparator(a, b) && !WordComparator(b, a);
      });
  words_.erase(unique_end, words_.end());
  auto end3 = chrono::high_resolution_clock::now();
  duration = chrono::duration_cast<chrono::milliseconds>(end3 - end2).count();

  cout << "unique list: " << duration << " ms" << endl;
  cout << "unique words_.size() = " << words_.size() << endl;

  // cout << "Number of nodes: " << word_lists_.size() << endl;
  // unordered_map<int, int> counts;
  // int max_count = 0;
  // for (auto& wl : word_lists_) {
  //   int count = wl.size();
  //   counts[count] += 1;
  //   max_count = max(max_count, count);
  // }
  // for (int i = 0; i <= max_count; i++) {
  //   cout << i << "\t" << counts[i] << endl;
  // }

  // root->DecodePointsAndBound(word_lists_);
  // word_lists_.clear();

  // arena.PrintStats();

  // This can be used to investigate the layout of EvalNode.
  /*
  cout << "sizeof(SumNode) = " << sizeof(SumNode) << endl;
  cout << "sizeof(ChoiceNode) = " << sizeof(ChoiceNode) << endl;
  cout << "root: " << (uintptr_t)root << endl;
  auto r = (uintptr_t)root;
  cout << "root->letter_: " << (uintptr_t)(&root->letter_) - r << endl;
  cout << "root->cell_: " << (uintptr_t)&root->cell_ - r << endl;
  cout << "root->points_: " << (uintptr_t)&root->points_ - r << endl;
  cout << "root->num_children_: " << (uintptr_t)&root->num_children_ - r << endl;
  cout << "root->capacity_: " << (uintptr_t)&root->capacity_ - r << endl;
  cout << "root->bound_: " << (uintptr_t)&root->bound_ - r << endl;
  cout << "root->children_: " << (uintptr_t)&root->children_ - r << endl;
  */
  return root;
}

template <int M, int N>
void OrderlyTreeBuilder<M, N>::DoAllDescents(
    int cell, int n, int length, Trie* t, EvalNodeArena& arena
) {
  auto old_mask = dupe_mask_;
  char* c = &bd_[cell][0];
  int j = 0;
  while (*c) {
    auto cc = *c - 'a';
    if (t->StartsWord(cc)) {
      int cell_order = cell_to_order_[cell];
      choices_[cell_order] = j;
      used_ ^= (1 << cell);
      used_ordered_ ^= (1 << cell_order);

      auto old_count = letter_counts_[cc]++;
      if (old_count == 1) {
        dupe_mask_ |= (1 << cc);
      }

      DoDFS(cell, n + 1, length + (cc == kQ ? 2 : 1), t->Descend(cc), arena);

      letter_counts_[cc]--;
      dupe_mask_ = old_mask;

      used_ordered_ ^= (1 << cell_order);
      used_ ^= (1 << cell);
    }
    c++;
    j++;
  }
}

// We want to avoid double-counting words that use the exact same cells. To do so with
// minimal overhead, we use a binary encoding in the SumNodes during tree building.
// Since most SumNodes have zero or one words on them, it greatly reduces overhead to
// store a single word inline on the SumNode. Space is limited there, so we repurpose
// the bound_ field and fill it in later (DecodePointsAndBound).
//
// - If the path to the SumNode does not contain a repeated letter (e.g. RISE):
//   - points_ = number of points scored for all words on this SumNode.
//   - bound_ = 0
// - If it does contain a repeat letter (e.g. SERE):
//   - points_ = number of points scored for _each_ word
//   - if bound_ = 0 -> no words on this SumNode
//   - if bound_ & FRESH_MASK:
//     - There is one word on this SumNode.
//     - It has WordId = bound_ & (FRESH_MASK - 1)
//   - otherwise:
//     - There are multiple distinct words on this SumNode.
//     - They're listed in word_lists_[bound_].
//
// After tree construction, this all needs to be decoded to set points_ and bound_ to
// their proper values. This is done with SumNode::DecodePointsAndBound().
// See https://github.com/danvk/hybrid-boggle/issues/117 and linked PRs.

static const uint32_t FRESH_MASK = 1 << 23;

void EncodeWordInSumNode(
    SumNode* word_node, Trie* t, int word_score, vector<vector<uint32_t>>& word_lists
) {
  auto slot = word_node->bound_;
  if (slot == 0) {
    // Fresh find! Inline the word into word_node->bound_ and mark it.
    // All words on a SumNode have the same score, which is convenient to store here.
    word_node->points_ = word_score;
    word_node->bound_ = t->WordId() | FRESH_MASK;
  } else if (slot & FRESH_MASK) {
    // The previous word was the first and is inlined into word_node->bound_.
    uint32_t old_word_id = slot & (FRESH_MASK - 1);
    uint32_t new_word_id = t->WordId();
    if (old_word_id != new_word_id) {
      // This is the first collision; move everything to a word_list.
      slot = word_lists.size();
      // assert(slot > 0);
      word_lists.push_back({old_word_id, new_word_id});
      assert(slot < FRESH_MASK);
      word_node->bound_ = slot;
    } else {
      // It's a duplicate with the previous word.
    }
  } else {
    // There are already 2+ words on this node; maybe there should be a third.
    // This search is O(N), but I've never seen N>6 and it's usually 2.
    auto& word_list = word_lists[slot];
    auto word_id = t->WordId();
    if (find(word_list.begin(), word_list.end(), word_id) == word_list.end()) {
      word_list.push_back(word_id);
    } else {
      // duplicate
    }
  }
}

template <int M, int N>
void OrderlyTreeBuilder<M, N>::DoDFS(
    int i, int n, int length, Trie* t, EvalNodeArena& arena
) {
  auto& neighbors = BucketBoggler<M, N>::NEIGHBORS[i];
  auto n_neighbors = neighbors[0];
  for (int j = 1; j <= n_neighbors; j++) {
    auto idx = neighbors[j];
    if ((used_ & (1 << idx)) == 0) {
      DoAllDescents(idx, n, length, t, arena);
    }
  }

  if (t->IsWord()) {
    AddWord(choices_, used_ordered_, t->WordId(), length);
  }
}

template <int M, int N>
void OrderlyTreeBuilder<M, N>::AddWord(
    int* choices, unsigned int used_ordered, uint32_t word_id, int length
) {
  // TODO: construct this in-place in the vector
  WordPath word;
  const auto& split_order = BucketBoggler<M, N>::SPLIT_ORDER;

  int idx = 0;
  while (used_ordered) {
    int order_index = std::countr_zero(used_ordered);
    int cell = split_order[order_index];
    int letter = choices[order_index];
    word.path[idx++] = 1 + cell;
    word.path[idx++] = 1 + letter;
    used_ordered &= used_ordered - 1;
  }
  if (idx < 2 * M * N) {
    word.path[idx++] = '\0';
  }
  word.points = kWordScores[length];
  word.word_id = word_id;
  words_.push_back(word);
}

template <int M, int N>
bool OrderlyTreeBuilder<M, N>::WordComparator(const WordPath& a, const WordPath& b) {
  const auto& ap = a.path;
  const auto& bp = b.path;

  // Compare the word arrays lexicographically
  for (int i = 0; i < 2 * M * N; ++i) {
    if (ap[i] != bp[i]) return ap[i] < bp[i];
    if (ap[i] == '\0' || bp[i] == '\0') break;
  }

  return a.word_id < b.word_id;
}

#endif  // ORDERLY_TREE_BUILDER_H
