#ifndef ORDERLY_TREE_BUILDER_H
#define ORDERLY_TREE_BUILDER_H

#include <array>
#include <iomanip>

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
  int num_paths_;
  unsigned int num_overflow_;
  vector<WordPath> words_;
  bool count_only_;

  // For interning zero-child SumNodes
  SumNode* canonical_nodes_[128];         // canonical nodes for 1-128 points
  unique_ptr<EvalNodeArena> temp_arena_;  // temporary arena for initial allocation

  void DoAllDescents(int cell, int n, int length, Trie* t, EvalNodeArena& arena);
  void DoDFS(int cell, int n, int length, Trie* t, EvalNodeArena& arena);
  void AddWord(int* choices, unsigned int used_ordered, uint32_t word_id, int length);

  static bool WordComparator(const WordPath& a, const WordPath& b);
  static void UniqueWordList(vector<WordPath>& words);

  // TODO: doesn't C++ have a range API now?
  SumNode* RangeToSumNode(
      pair<WordPath*, WordPath*> range, int depth, EvalNodeArena& arena
  );
  ChoiceNode* RangeToChoiceNode(
      int cell, pair<WordPath*, WordPath*> range, int depth, EvalNodeArena& arena
  );

  void PrintWordList();
};

template <int M, int N>
const SumNode* OrderlyTreeBuilder<M, N>::BuildTree(EvalNodeArena& arena) {
  auto start = chrono::high_resolution_clock::now();
  // cout << "alignment_of<EvalNode>=" << alignment_of<EvalNode>() << endl;

  // Step 1: Create canonical zero-child SumNodes in main arena
  for (int points = 1; points <= 128; points++) {
    auto node = arena.NewSumNodeWithCapacity(0);
    node->points_ = points;
    node->bound_ = points;  // For zero-child nodes, bound equals points
    canonical_nodes_[points - 1] = node;
  }

  count_only_ = false;
  words_.clear();
  words_.reserve(36'000'000);

  for (int cell = 0; cell < M * N; cell++) {
    DoAllDescents(cell, 0, 0, dict_, *temp_arena_);
  }
  auto end1 = chrono::high_resolution_clock::now();
  auto duration = chrono::duration_cast<chrono::milliseconds>(end1 - start).count();
  cout << "Build word list: " << duration << " ms" << endl;

  sort(words_.begin(), words_.end(), WordComparator);
  auto end2 = chrono::high_resolution_clock::now();
  duration = chrono::duration_cast<chrono::milliseconds>(end2 - end1).count();
  cout << "sort list: " << duration << " ms" << endl;
  cout << "words_.size() = " << words_.size() << endl;
  // PrintWordList();

  // auto unique_end =
  //     unique(words_.begin(), words_.end(), [](const auto& a, const auto& b) {
  //       return !WordComparator(a, b) && !WordComparator(b, a);
  //     });
  // words_.erase(unique_end, words_.end());
  UniqueWordList(words_);
  auto end3 = chrono::high_resolution_clock::now();
  duration = chrono::duration_cast<chrono::milliseconds>(end3 - end2).count();

  cout << "unique list: " << duration << " ms" << endl;
  cout << "unique words_.size() = " << words_.size() << endl;
  // PrintWordList();

  WordPath* w_start = &words_[0];
  WordPath* w_end = &words_[words_.size() - 1];
  auto root = RangeToSumNode({w_start, w_end}, 0, arena);

  auto end4 = chrono::high_resolution_clock::now();
  duration = chrono::duration_cast<chrono::milliseconds>(end4 - end3).count();
  cout << "build tree: " << duration << " ms" << endl;

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
    if (!count_only_) {
      AddWord(choices_, used_ordered_, t->WordId(), length);
    }
    num_paths_++;
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
  word.path.fill('\0');
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

  int result = memcmp(ap.data(), bp.data(), 2 * M * N);
  if (result != 0) {
    return result < 0;
  }

  return a.word_id < b.word_id;
}

template <unsigned long N>
bool ArrayEq(const array<uint8_t, N>& a, const array<uint8_t, N>& b) {
  for (int i = 0; i < N; i++) {
    if (a[i] != b[i]) return false;
    if (a[i] == '\0' || b[i] == '\0') break;
  }
  return true;  // they're equal if the have nulls at the spot, or are full-length equal
}

template <int M, int N>
void OrderlyTreeBuilder<M, N>::UniqueWordList(vector<WordPath>& words) {
  int write_idx = 1;
  WordPath last = words[0];  // TODO: use a reference or pointer here

  auto n = words.size();
  for (int i = 1; i < n; i++) {
    const auto& w = words[i];
    if (!ArrayEq(w.path, last.path)) {
      if (i != write_idx) {
        // cout << "uniq move " << i << " -> " << write_idx << endl;
        words[write_idx] = w;
      }
      last = words[write_idx];
      write_idx++;
    } else if (w.word_id != last.word_id) {
      words[write_idx - 1].points += w.points;
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
    pair<WordPath*, WordPath*> range, int depth, EvalNodeArena& arena
) {
  WordPath* it = range.first;
  WordPath* end = range.second;
  // cout << string(depth, ' ') << "RangeToSumNode(" << (end - it + 1)
  //      << " words, depth=" << depth << ")" << endl;
  int points = 0;
  if (PathLength(it->path) == depth) {
    points = it->points;
    ++it;
  }

  // TOOD: return interned node if no children

  // TODO: reserve
  vector<int> child_cells;
  vector<WordPath*> child_range_starts;
  vector<WordPath*> child_range_ends;
  int last_cell = -1;
  for (; it <= end; ++it) {
    int cell = it->path[2 * depth];
    if (cell != last_cell) {
      child_cells.push_back(cell);
      child_range_starts.push_back(it);
      child_range_ends.push_back(it);
      last_cell = cell;
    } else {
      *child_range_ends.rbegin() = it;
    }
  }

  auto node = arena.NewSumNodeWithCapacity(child_cells.size());
  node->bound_ = node->points_ = points;
  node->num_children_ = child_cells.size();
  for (int i = 0; i < child_cells.size(); i++) {
    auto child = RangeToChoiceNode(
        child_cells[i] - 1, {child_range_starts[i], child_range_ends[i]}, depth, arena
    );
    node->children_[i] = child;
    node->bound_ += child->bound_;
  }
  return node;
}

template <int M, int N>
ChoiceNode* OrderlyTreeBuilder<M, N>::RangeToChoiceNode(
    int cell, pair<WordPath*, WordPath*> range, int depth, EvalNodeArena& arena
) {
  WordPath* it = range.first;
  WordPath* end = range.second;
  // cout << string(depth, ' ') << "RangeToChoiceNode(" << (end - it + 1)
  //      << " words, cell=" << cell << ", depth=" << depth << ")" << endl;
  // TODO: reserve
  vector<int> child_letters;
  vector<WordPath*> child_range_starts;
  vector<WordPath*> child_range_ends;
  int last_letter = -1;
  for (; it <= end; ++it) {
    int letter = it->path[2 * depth + 1];
    if (letter != last_letter) {
      child_letters.push_back(letter);
      child_range_starts.push_back(it);
      child_range_ends.push_back(it);
      last_letter = letter;
    } else {
      *child_range_ends.rbegin() = it;
    }
  }

  uint32_t letter_mask = 0;
  for (auto& letter : child_letters) {
    letter_mask |= (1 << (letter - 1));
  }

  auto node = arena.NewChoiceNodeWithCapacity(child_letters.size());
  node->cell_ = cell;
  node->child_letters_ = letter_mask;
  node->bound_ = 0;
  for (int i = 0; i < child_letters.size(); i++) {
    auto child =
        RangeToSumNode({child_range_starts[i], child_range_ends[i]}, depth + 1, arena);
    node->children_[i] = child;
    node->bound_ = max(node->bound_, child->bound_);
  }
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
    // cout << "(" << w.word_id << ")";
    // cout << endl;
  }
}

#endif  // ORDERLY_TREE_BUILDER_H
