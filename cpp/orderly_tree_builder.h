#ifndef ORDERLY_TREE_BUILDER_H
#define ORDERLY_TREE_BUILDER_H

#include "ibuckets.h"
#include "eval_node.h"

using namespace std;

// TODO: inheritance isn't that helpful here.
// TODO: templating on M, N probably isn't helpful, either.
template <int M, int N>
class OrderlyTreeBuilder : public BucketBoggler<M, N> {
 public:
  OrderlyTreeBuilder(Trie* t) : BucketBoggler<M, N>(t) {
    for (int i = 0; i < M*N; i++) {
      cell_to_order_[BucketBoggler<M, N>::SPLIT_ORDER[i]] = i;
    }
  }
  virtual ~OrderlyTreeBuilder() {}

  // These are "dependent names", see https://stackoverflow.com/a/1528010/388951.
  using BucketBoggler<M, N>::dict_;
  using BucketBoggler<M, N>::bd_;
  using BucketBoggler<M, N>::used_;

  /** Build an EvalTree for the current board. */
  const EvalNode* BuildTree(EvalNodeArena& arena, bool dedupe=false);

  unique_ptr<EvalNodeArena> CreateArena() {
    return create_eval_node_arena();
  }

 private:
  EvalNode* root_;
  bool dedupe_;
  int cell_to_order_[M*N];
  pair<int, int> choices_[M*N];

  // This one does not depend on M, N
  void DoAllDescents(int cell, int n, int length, Trie* t, EvalNodeArena& arena);
  void DoDFS(int cell, int n, int length, Trie* t, EvalNodeArena& arena);
};

template <int M, int N>
const EvalNode* OrderlyTreeBuilder<M, N>::BuildTree(EvalNodeArena& arena, bool dedupe) {
  // auto start = chrono::high_resolution_clock::now();
  root_ = new EvalNode();
  root_->letter_ = EvalNode::ROOT_NODE;
  root_->cell_ = 0; // irrelevant
  root_->points_ = 0;
  used_ = 0;

  // TODO: remove this if I disentangle OrderlyTreeBuilder and BucketBoggler.
  details_.max_nomark = 0;
  details_.sum_union = 0;
  details_.bailout_cell = -1;

  for (int cell = 0; cell < M * N; cell++) {
    DoAllDescents(cell, 0, 0, dict_, arena);
  }

  vector<int> num_letters(M*N, 0);
  for (int i = 0; i < M*N; i++) {
    num_letters[i] = strlen(bd_[i]);
  }
  root_->SetComputedFields(num_letters);
  auto root = root_;
  root_ = NULL;
  arena.AddNode(root);
  details_.max_nomark = root->bound_;
  return root;
}

template<int M, int N>
void OrderlyTreeBuilder<M, N>::DoAllDescents(int cell, int n, int length, Trie* t, EvalNodeArena& arena) {
  choices_[n] = {cell, 0};

  // TODO: store num_letters array or iterate string
  int n_chars = strlen(bd_[cell]);
  for (int j = 0; j < n_chars; j++) {
    auto cc = bd_[cell][j] - 'a';
    if (t->StartsWord(cc)) {
      choices_[n].second = j;
      DoDFS(cell, n + 1, length + (cc == kQ ? 2 : 1), t->Descend(cc), arena);
    }
  }
}

template<int M, int N>
void OrderlyTreeBuilder<M, N>::DoDFS(int i, int n, int length, Trie* t, EvalNodeArena& arena) {
  used_ ^= (1 << i);

  auto& neighbors = BucketBoggler<M, N>::NEIGHBORS[i];
  auto n_neighbors = neighbors[0];
  for (int j = 1; j <= n_neighbors; j++) {
    auto idx = neighbors[j];
    if ((used_ & (1<<idx)) == 0) {
      DoAllDescents(idx, n, length, t, arena);
    }
  }

  if (t->IsWord()) {
    auto word_score = kWordScores[length];

    vector<pair<int, int>> orderly_choices;
    for (int j = 0; j < n; j++) {
      orderly_choices.push_back(choices_[j]);
    }
    // TODO: "this" capture could be avoided
    sort(orderly_choices.begin(), orderly_choices.end(), [this](const pair<int, int>& a, const pair<int, int>& b) {
      return cell_to_order_[a.first] < cell_to_order_[b.first];
    });
    root_->AddWord(orderly_choices, word_score, arena);
  }

  used_ ^= (1 << i);
}


#endif // ORDERLY_TREE_BUILDER_H
