#ifndef ORDERLY_TREE_BUILDER_H
#define ORDERLY_TREE_BUILDER_H

#include "eval_node.h"
#include "ibuckets.h"

using namespace std;

using int128_t = __int128;

namespace std {
template <>
struct hash<int128_t> {
  size_t operator()(const int128_t& x) const {
    // Combine the hash of the upper and lower 64 bits
    const uint64_t* data = reinterpret_cast<const uint64_t*>(&x);
    std::hash<uint64_t> hasher;
    size_t seed = hasher(data[0]);
    seed ^= hasher(data[1]) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
    return seed;
  }
};
}  // namespace std

// TODO: templating on M, N probably isn't helpful, either.
template <int M, int N>
class OrderlyTreeBuilder : public BoardClassBoggler<M, N> {
 public:
  OrderlyTreeBuilder(Trie* t) : BoardClassBoggler<M, N>(t) {
    for (int i = 0; i < M * N; i++) {
      cell_to_order_[BucketBoggler<M, N>::SPLIT_ORDER[i]] = i;
    }
    used_ordered_ = 0;
    found_words_ = unordered_set<int128_t>();
  }
  virtual ~OrderlyTreeBuilder() {}

  // These are "dependent names", see
  // https://stackoverflow.com/a/1528010/388951.
  using BoardClassBoggler<M, N>::dict_;
  using BoardClassBoggler<M, N>::bd_;
  using BoardClassBoggler<M, N>::used_;

  /** Build an EvalTree for the current board. */
  const SumNode* BuildTree(EvalNodeArena& arena, bool dedupe = false);

  unique_ptr<EvalNodeArena> CreateArena() { return create_eval_node_arena(); }

  int SumUnion() const { return 0; }

 private:
  SumNode* root_;
  int cell_to_order_[M * N];
  unsigned int used_ordered_;            // used cells mapped to their split order
  int choices_[M * N];                   // cell order -> letter index
  unordered_set<int128_t> found_words_;  // hash of (choices, used_ordered, word id)

  void DoAllDescents(int cell, int n, int length, Trie* t, EvalNodeArena& arena);
  void DoDFS(int cell, int n, int length, Trie* t, EvalNodeArena& arena);
  int128_t HashChoices(uint32_t word_id);
};

template <int M, int N>
const SumNode* OrderlyTreeBuilder<M, N>::BuildTree(EvalNodeArena& arena, bool dedupe) {
  // auto start = chrono::high_resolution_clock::now();
  // cout << "alignment_of<EvalNode>=" << alignment_of<EvalNode>() << endl;
  root_ = arena.NewRootNodeWithCapacity(M * N);  // this will never be reallocated
  used_ = 0;

  for (int cell = 0; cell < M * N; cell++) {
    DoAllDescents(cell, 0, 0, dict_, arena);
  }
  auto root = root_;
  root_ = NULL;
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
    auto hash = HashChoices(t->WordId());
    if (found_words_.find(hash) == found_words_.end()) {
      auto word_score = kWordScores[length];
      found_words_.insert(hash);
      auto new_root = root_->AddWordWork(
          choices_, used_ordered_, BucketBoggler<M, N>::SPLIT_ORDER, word_score, arena
      );
      assert(new_root == root_);
    }
  }
}

// Packs the choices + used_order + word_id into a 128-bit integer.
// Assumes at most 23 choices are made. 110 bits used to hash the choices, the remaining
// 18 bits are used to store the word index from the wordlist (max size 2**18 = 262143).
// 2**110 >= 26**23
template <int M, int N>
int128_t OrderlyTreeBuilder<M, N>::HashChoices(uint32_t word_id) {
  assert(__builtin_popcount(used_ordered_) <= 23);

  // Take only the indices from choices that are part of the used_order bitmap
  int128_t hash = 0;
  for (int i = 0; i < M * N; i++) {
    if (used_ordered_ & (1 << i)) {
      hash += choices_[i];
    }
    hash *= 26;
  }

  // Word_id goes in the highest 18 bits
  return hash | (static_cast<int128_t>(word_id) << 110);
}

#endif  // ORDERLY_TREE_BUILDER_H
