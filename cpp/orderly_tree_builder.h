#ifndef ORDERLY_TREE_BUILDER_H
#define ORDERLY_TREE_BUILDER_H

#include <array>
#include <iomanip>

#include "constants.h"
#include "equal_ranges.h"
#include "eval_node.h"
#include "ibuckets.h"

using namespace std;

struct TreeBuilderStats {
  float collect_s;
  float sort_s;
  // float uniq_s; -- too fast, not worth tracking
  float build_s;
  uint32_t n_paths;
  uint32_t n_uniq;
};

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

  struct WordPath {
    array<uint8_t, 2 * M * N> path;
    uint32_t word_id : 24;
    uint8_t points : 8;
  };

  TreeBuilderStats GetStats() const { return stats_; }

 private:
  SumNode* root_;
  int cell_to_order_[M * N];
  unsigned int used_ordered_;  // used cells mapped to their split order
  int choices_[M * N];         // cell order -> letter index
  int num_paths_;
  vector<WordPath> words_;
  TreeBuilderStats stats_;

  // For interning zero-child SumNodes
  SumNode* canonical_nodes_[128];  // canonical nodes for 1-128 points

  void DoAllDescents(int cell, int n, int length, Trie* t, EvalNodeArena& arena);
  void DoDFS(int cell, int n, int length, Trie* t, EvalNodeArena& arena);
  void AddWord(int* choices, unsigned int used_ordered, uint32_t word_id, int length);

  static bool WordComparator(const WordPath& a, const WordPath& b);
  static void UniqueWordList(vector<WordPath>& words);

  // TODO: doesn't C++ have a range API now?
  SumNode* RangeToSumNode(
      const vector<WordPath>& words,
      pair<int, int> range,
      int depth,
      EvalNodeArena& arena
  );
  ChoiceNode* RangeToChoiceNode(
      int cell,
      const vector<WordPath>& words,
      pair<int, int> range,
      int depth,
      EvalNodeArena& arena
  );

  void PrintWordList();
};

template <int M, int N>
const SumNode* OrderlyTreeBuilder<M, N>::BuildTree(EvalNodeArena& arena) {
  TreeBuilderStats stats;
  auto start = chrono::high_resolution_clock::now();
  // cout << "alignment_of<EvalNode>=" << alignment_of<EvalNode>() << endl;
  // cout << "sizeof<WordPath>=" << sizeof(WordPath) << endl;
  // cout << "sizeof(WordPath.data)=" << sizeof(words_[0].path.data()) << endl;
  // cout << "alignment_of<WordPath>=" << alignment_of<WordPath>() << endl;

  // This allows perfect sizing of words_, but is almost as slow as building the list.
  // int count = CountPaths();
  // auto end0 = chrono::high_resolution_clock::now();
  // auto duration = chrono::duration_cast<chrono::milliseconds>(end0 - start).count();
  // cout << "Count paths: " << duration << " ms" << endl;

  // TODO: make the arena own these and re-use them when merging
  for (int points = 1; points <= 128; points++) {
    auto node = arena.NewSumNodeWithCapacity(0);
    node->points_ = points;
    node->bound_ = points;  // For zero-child nodes, bound equals points
    canonical_nodes_[points - 1] = node;
  }

  // 20M is large enough to fit the word list for almost all boards.
  // This is ~700MB for a 4x4 board, and only held temporarily.
  words_.clear();
  words_.reserve(20'000'000);

  for (int cell = 0; cell < M * N; cell++) {
    DoAllDescents(cell, 0, 0, dict_, arena);
  }
  auto end1 = chrono::high_resolution_clock::now();
  auto duration = chrono::duration_cast<chrono::milliseconds>(end1 - start).count();
  stats.collect_s = duration / 1000.0;

  sort(words_.begin(), words_.end(), WordComparator);
  auto end2 = chrono::high_resolution_clock::now();
  duration = chrono::duration_cast<chrono::milliseconds>(end2 - end1).count();
  stats.sort_s = duration / 1000.0;
  stats.n_paths = words_.size();
  // PrintWordList();

  UniqueWordList(words_);
  auto end3 = chrono::high_resolution_clock::now();
  duration = chrono::duration_cast<chrono::milliseconds>(end3 - end2).count();
  // stats.uniq_secs = duration / 1000.0;
  stats.n_uniq = words_.size();
  // PrintWordList();

  auto root = RangeToSumNode(words_, {0, words_.size()}, 0, arena);

  auto end4 = chrono::high_resolution_clock::now();
  duration = chrono::duration_cast<chrono::milliseconds>(end4 - end3).count();
  stats.build_s = duration / 1000.0;

  words_.clear();
  words_.shrink_to_fit();  // release memory ASAP
  stats_ = stats;

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
  char* c = &bd_[cell][0];
  int j = 0;
  while (*c) {
    auto cc = *c - 'a';
    if (t->StartsWord(cc)) {
      int cell_order = cell_to_order_[cell];
      choices_[cell_order] = j;
      used_ ^= (1 << cell);
      used_ordered_ ^= (1 << cell_order);

      DoDFS(cell, n + 1, length + (cc == kQ ? 2 : 1), t->Descend(cc), arena);

      used_ordered_ ^= (1 << cell_order);
      used_ ^= (1 << cell);
    }
    c++;
    j++;
  }
}

#define REC(idx)                               \
  do {                                         \
    if ((used_ & (1 << idx)) == 0) {           \
      DoAllDescents(idx, n, length, t, arena); \
    }                                          \
  } while (0)

#define REC3(a, b, c) \
  REC(a);             \
  REC(b);             \
  REC(c)

#define REC5(a, b, c, d, e) \
  REC3(a, b, c);            \
  REC(d);                   \
  REC(e)

#define REC8(a, b, c, d, e, f, g, h) \
  REC5(a, b, c, d, e);               \
  REC3(f, g, h)

// clang-format off

/*[[[cog
from boggle.neighbors import NEIGHBORS

for (w, h), neighbors in NEIGHBORS.items():
    print(f"""
// {w}x{h}
template<>
void OrderlyTreeBuilder<{w}, {h}>::DoDFS(
    int i, int n, int length, Trie* t, EvalNodeArena& arena
) {{
  if (t->IsWord()) {{
    AddWord(choices_, used_ordered_, t->WordId(), length);
  }}
  switch(i) {{""")
    for i, ns in enumerate(neighbors):
        csv = ", ".join(str(n) for n in ns)
        print(f"    case {i}: REC{len(ns)}({csv}); break;")

    print("""  }
}""")
]]]*/

// 2x2
template<>
void OrderlyTreeBuilder<2, 2>::DoDFS(
    int i, int n, int length, Trie* t, EvalNodeArena& arena
) {
  if (t->IsWord()) {
    AddWord(choices_, used_ordered_, t->WordId(), length);
  }
  switch(i) {
    case 0: REC3(1, 2, 3); break;
    case 1: REC3(0, 2, 3); break;
    case 2: REC3(0, 1, 3); break;
    case 3: REC3(0, 1, 2); break;
  }
}

// 2x3
template<>
void OrderlyTreeBuilder<2, 3>::DoDFS(
    int i, int n, int length, Trie* t, EvalNodeArena& arena
) {
  if (t->IsWord()) {
    AddWord(choices_, used_ordered_, t->WordId(), length);
  }
  switch(i) {
    case 0: REC3(1, 3, 4); break;
    case 1: REC5(0, 2, 3, 4, 5); break;
    case 2: REC3(1, 4, 5); break;
    case 3: REC3(0, 1, 4); break;
    case 4: REC5(0, 1, 2, 3, 5); break;
    case 5: REC3(1, 2, 4); break;
  }
}

// 3x3
template<>
void OrderlyTreeBuilder<3, 3>::DoDFS(
    int i, int n, int length, Trie* t, EvalNodeArena& arena
) {
  if (t->IsWord()) {
    AddWord(choices_, used_ordered_, t->WordId(), length);
  }
  switch(i) {
    case 0: REC3(1, 3, 4); break;
    case 1: REC5(0, 2, 3, 4, 5); break;
    case 2: REC3(1, 4, 5); break;
    case 3: REC5(0, 1, 4, 6, 7); break;
    case 4: REC8(0, 1, 2, 3, 5, 6, 7, 8); break;
    case 5: REC5(1, 2, 4, 7, 8); break;
    case 6: REC3(3, 4, 7); break;
    case 7: REC5(3, 4, 5, 6, 8); break;
    case 8: REC3(4, 5, 7); break;
  }
}

// 3x4
template<>
void OrderlyTreeBuilder<3, 4>::DoDFS(
    int i, int n, int length, Trie* t, EvalNodeArena& arena
) {
  if (t->IsWord()) {
    AddWord(choices_, used_ordered_, t->WordId(), length);
  }
  switch(i) {
    case 0: REC3(1, 4, 5); break;
    case 1: REC5(0, 2, 4, 5, 6); break;
    case 2: REC5(1, 3, 5, 6, 7); break;
    case 3: REC3(2, 6, 7); break;
    case 4: REC5(0, 1, 5, 8, 9); break;
    case 5: REC8(0, 1, 2, 4, 6, 8, 9, 10); break;
    case 6: REC8(1, 2, 3, 5, 7, 9, 10, 11); break;
    case 7: REC5(2, 3, 6, 10, 11); break;
    case 8: REC3(4, 5, 9); break;
    case 9: REC5(4, 5, 6, 8, 10); break;
    case 10: REC5(5, 6, 7, 9, 11); break;
    case 11: REC3(6, 7, 10); break;
  }
}

// 4x4
template<>
void OrderlyTreeBuilder<4, 4>::DoDFS(
    int i, int n, int length, Trie* t, EvalNodeArena& arena
) {
  if (t->IsWord()) {
    AddWord(choices_, used_ordered_, t->WordId(), length);
  }
  switch(i) {
    case 0: REC3(1, 4, 5); break;
    case 1: REC5(0, 2, 4, 5, 6); break;
    case 2: REC5(1, 3, 5, 6, 7); break;
    case 3: REC3(2, 6, 7); break;
    case 4: REC5(0, 1, 5, 8, 9); break;
    case 5: REC8(0, 1, 2, 4, 6, 8, 9, 10); break;
    case 6: REC8(1, 2, 3, 5, 7, 9, 10, 11); break;
    case 7: REC5(2, 3, 6, 10, 11); break;
    case 8: REC5(4, 5, 9, 12, 13); break;
    case 9: REC8(4, 5, 6, 8, 10, 12, 13, 14); break;
    case 10: REC8(5, 6, 7, 9, 11, 13, 14, 15); break;
    case 11: REC5(6, 7, 10, 14, 15); break;
    case 12: REC3(8, 9, 13); break;
    case 13: REC5(8, 9, 10, 12, 14); break;
    case 14: REC5(9, 10, 11, 13, 15); break;
    case 15: REC3(10, 11, 14); break;
  }
}

// 4x5
template<>
void OrderlyTreeBuilder<4, 5>::DoDFS(
    int i, int n, int length, Trie* t, EvalNodeArena& arena
) {
  if (t->IsWord()) {
    AddWord(choices_, used_ordered_, t->WordId(), length);
  }
  switch(i) {
    case 0: REC3(1, 5, 6); break;
    case 1: REC5(0, 2, 5, 6, 7); break;
    case 2: REC5(1, 3, 6, 7, 8); break;
    case 3: REC5(2, 4, 7, 8, 9); break;
    case 4: REC3(3, 8, 9); break;
    case 5: REC5(0, 1, 6, 10, 11); break;
    case 6: REC8(0, 1, 2, 5, 7, 10, 11, 12); break;
    case 7: REC8(1, 2, 3, 6, 8, 11, 12, 13); break;
    case 8: REC8(2, 3, 4, 7, 9, 12, 13, 14); break;
    case 9: REC5(3, 4, 8, 13, 14); break;
    case 10: REC5(5, 6, 11, 15, 16); break;
    case 11: REC8(5, 6, 7, 10, 12, 15, 16, 17); break;
    case 12: REC8(6, 7, 8, 11, 13, 16, 17, 18); break;
    case 13: REC8(7, 8, 9, 12, 14, 17, 18, 19); break;
    case 14: REC5(8, 9, 13, 18, 19); break;
    case 15: REC3(10, 11, 16); break;
    case 16: REC5(10, 11, 12, 15, 17); break;
    case 17: REC5(11, 12, 13, 16, 18); break;
    case 18: REC5(12, 13, 14, 17, 19); break;
    case 19: REC3(13, 14, 18); break;
  }
}

// 5x5
template<>
void OrderlyTreeBuilder<5, 5>::DoDFS(
    int i, int n, int length, Trie* t, EvalNodeArena& arena
) {
  if (t->IsWord()) {
    AddWord(choices_, used_ordered_, t->WordId(), length);
  }
  switch(i) {
    case 0: REC3(1, 5, 6); break;
    case 1: REC5(0, 2, 5, 6, 7); break;
    case 2: REC5(1, 3, 6, 7, 8); break;
    case 3: REC5(2, 4, 7, 8, 9); break;
    case 4: REC3(3, 8, 9); break;
    case 5: REC5(0, 1, 6, 10, 11); break;
    case 6: REC8(0, 1, 2, 5, 7, 10, 11, 12); break;
    case 7: REC8(1, 2, 3, 6, 8, 11, 12, 13); break;
    case 8: REC8(2, 3, 4, 7, 9, 12, 13, 14); break;
    case 9: REC5(3, 4, 8, 13, 14); break;
    case 10: REC5(5, 6, 11, 15, 16); break;
    case 11: REC8(5, 6, 7, 10, 12, 15, 16, 17); break;
    case 12: REC8(6, 7, 8, 11, 13, 16, 17, 18); break;
    case 13: REC8(7, 8, 9, 12, 14, 17, 18, 19); break;
    case 14: REC5(8, 9, 13, 18, 19); break;
    case 15: REC5(10, 11, 16, 20, 21); break;
    case 16: REC8(10, 11, 12, 15, 17, 20, 21, 22); break;
    case 17: REC8(11, 12, 13, 16, 18, 21, 22, 23); break;
    case 18: REC8(12, 13, 14, 17, 19, 22, 23, 24); break;
    case 19: REC5(13, 14, 18, 23, 24); break;
    case 20: REC3(15, 16, 21); break;
    case 21: REC5(15, 16, 17, 20, 22); break;
    case 22: REC5(16, 17, 18, 21, 23); break;
    case 23: REC5(17, 18, 19, 22, 24); break;
    case 24: REC3(18, 19, 23); break;
  }
}
// [[[end]]]
// clang-format on
#undef REC
#undef REC3
#undef REC5
#undef REC8

template <int M, int N>
void OrderlyTreeBuilder<M, N>::AddWord(
    int* choices, unsigned int used_ordered, uint32_t word_id, int length
) {
  words_.emplace_back(WordPath());
  WordPath& word = *words_.rbegin();
  const auto& split_order = BucketBoggler<M, N>::SPLIT_ORDER;

  int idx = 0;
  word.path.fill('\0');
  while (used_ordered) {
    int order_index = std::countr_zero(used_ordered);
    int cell = split_order[order_index];
    int letter = choices[order_index];
#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wstringop-overflow"
#endif
    // The +1s here preserve null as end-of-word.
    word.path[idx++] = 1 + cell;
    word.path[idx++] = 1 + letter;
#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC diagnostic pop
#endif
    used_ordered &= used_ordered - 1;
  }
  word.points = kWordScores[length];
  word.word_id = word_id;
}

template <int M, int N>
bool OrderlyTreeBuilder<M, N>::WordComparator(const WordPath& a, const WordPath& b) {
  const auto& ap = a.path;
  const auto& bp = b.path;
  auto result = memcmp(ap.data(), bp.data(), 2 * M * N);
  if (result != 0) {
    return result < 0;
  }

  return a.word_id < b.word_id;
}

template <int M, int N>
void OrderlyTreeBuilder<M, N>::UniqueWordList(vector<WordPath>& words) {
  int write_idx = 1;
  WordPath last = words[0];  // TODO: use a reference or pointer here

  auto n = words.size();
  for (int i = 1; i < n; i++) {
    const auto& w = words[i];
    int result = memcmp(w.path.data(), last.path.data(), 2 * M * N);
    if (result != 0) {
      if (i != write_idx) {
        // cout << "uniq move " << i << " -> " << write_idx << endl;
        words[write_idx] = w;
      }
      last = words[write_idx];
      write_idx++;
    } else if (w.word_id != last.word_id) {
      words[write_idx - 1].points += w.points;
      last.word_id = w.word_id;
    }
    // otherwise: drop it
  }
  words.erase(words.begin() + write_idx, words.end());
}

template <unsigned long N>
int PathLength(const array<uint8_t, N>& a) {
  int len = 0;
  for (int i = 0; i < N; i += 2, len++) {
    if (a[i] == '\0') break;
  }
  return len;
}

// Endpoints are _inclusive_; equal ends = 1-element list
template <int M, int N>
SumNode* OrderlyTreeBuilder<M, N>::RangeToSumNode(
    const vector<WordPath>& words, pair<int, int> range, int depth, EvalNodeArena& arena
) {
  int start = range.first;
  int end = range.second;
  int points = 0;
  if (PathLength(words[start].path) == depth) {
    points = words[start].points;
    ++start;
  }

  size_t range_size = end - start;
  if (range_size == 0 && points <= 128) {
    return canonical_nodes_[points - 1];
  }

  // Use extract_equal_ranges for large ranges
  const int idx = 2 * depth;
  auto ranges = equal_ranges(words, idx, start, end);

  auto node = arena.NewSumNodeWithCapacity(ranges.size());
  node->bound_ = node->points_ = points;
  node->num_children_ = ranges.size();

  for (int i = 0; i < ranges.size(); i++) {
    const auto& [cell, range_start, range_end] = ranges[i];

    auto child =
        RangeToChoiceNode(cell - 1, words, {range_start, range_end}, depth, arena);
    node->children_[i] = child;
    node->bound_ += child->bound_;
  }
  return node;
}

template <int M, int N>
ChoiceNode* OrderlyTreeBuilder<M, N>::RangeToChoiceNode(
    int cell,
    const vector<WordPath>& words,
    pair<int, int> range,
    int depth,
    EvalNodeArena& arena
) {
  int start = range.first;
  int end = range.second;

  const auto idx = 2 * depth + 1;
  auto ranges = equal_ranges(words, idx, start, end);

  auto node = arena.NewChoiceNodeWithCapacity(ranges.size());
  node->cell_ = cell;
  node->bound_ = 0;
  uint32_t letter_mask = 0;
  for (int i = 0; i < ranges.size(); i++) {
    const auto& [letter, range_start, range_end] = ranges[i];
    letter_mask |= (1 << (letter - 1));
    auto child = RangeToSumNode(words, {range_start, range_end}, depth + 1, arena);
    node->children_[i] = child;
    node->bound_ = max(node->bound_, child->bound_);
  }
  node->child_letters_ = letter_mask;
  return node;
}

template <int M, int N>
void OrderlyTreeBuilder<M, N>::PrintWordList() {
  int i = 0;
  for (const auto& w : words_) {
    cout << std::setw(3) << (i++) << " [";
    for (int k = 0; k < 2 * M * N; k += 2) {
      if (w.path[k] == '\0') {
        break;
      }
      if (k) cout << ", ";
      cout << "(" << (int)(w.path[k] - 1) << ", " << (int)(w.path[k + 1] - 1) << ")";
    }
    cout << "] (" << (int)w.points << ") ";
    auto t = dict_->FindWordId(w.word_id);
    cout << "(" << Trie::ReverseLookup(dict_, t) << ")" << endl;
  }
}

#endif  // ORDERLY_TREE_BUILDER_H
