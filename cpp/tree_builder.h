#ifndef TREE_BUILDER_H
#define TREE_BUILDER_H

#include "ibuckets.h"
#include "eval_node.h"

using namespace std;

// TODO: templating on M, N probably isn't that helpful here.
template <int M, int N>
class TreeBuilder : public BoardClassBoggler<M, N> {
 public:
  TreeBuilder(Trie* t) : BoardClassBoggler<M, N>(t), runs_(0) {}
  virtual ~TreeBuilder() {}

  // These are "dependent names", see https://stackoverflow.com/a/1528010/388951.
  using BoardClassBoggler<M, N>::dict_;
  using BoardClassBoggler<M, N>::bd_;
  using BoardClassBoggler<M, N>::used_;

  /** Build an EvalTree for the current board. */
  const EvalNode* BuildTree(EvalNodeArena& arena, bool dedupe=false);

  unique_ptr<EvalNodeArena> CreateArena() {
    return create_eval_node_arena();
  }

  int SumUnion() const { return details_.sum_union; }

 private:
  uintptr_t runs_;
  ScoreDetails details_;
  EvalNode* root_;
  bool dedupe_;
  unordered_map<uint64_t, EvalNode*> node_cache_;

  unsigned int DoAllDescents(int idx, int length, Trie* t, EvalNode* node, EvalNodeArena& arena);
  unsigned int DoDFS(int i, int length, Trie* t, EvalNode* node, EvalNodeArena& arena);
  EvalNode* GetCanonicalNode(EvalNode* node);
};

// TODO: can this not be a template method?
template <int M, int N>
const EvalNode* TreeBuilder<M, N>::BuildTree(EvalNodeArena& arena, bool dedupe) {
  // auto start = chrono::high_resolution_clock::now();
  root_ = new EvalNode();

  root_->letter_ = EvalNode::ROOT_NODE;
  root_->cell_ = 0; // irrelevant
  root_->points_ = 0;

  details_.max_nomark = 0;
  details_.sum_union = 0;
  details_.bailout_cell = -1;
  runs_ = 1 + dict_->Mark();
  used_ = 0;
  dedupe_ = dedupe;
  node_cache_.clear();

  for (int i = 0; i < M * N; i++) {
    auto child = new EvalNode();
    child->letter_ = EvalNode::CHOICE_NODE;
    child->cell_ = i;
    auto score = DoAllDescents(i, 0, dict_, child, arena);
    if (score > 0) {
      details_.max_nomark += score;
      root_->children_.push_back(child);
      arena.AddNode(child);
    } else {
      delete child;
    }
  }

  root_->bound_ = details_.max_nomark;
  dict_->Mark(runs_);
  // auto finish = chrono::high_resolution_clock::now();
  // auto duration = chrono::duration_cast<chrono::milliseconds>(finish - start).count();
  // TODO: record tree building time
  // cout << "build tree: " << duration << " ms" << endl;
  auto root = root_;
  root_ = NULL;
  arena.AddNode(root);
  node_cache_.clear();
  return root;
  // return unique_ptr<EvalNode>(root_);
}

template<int M, int N>
unsigned int TreeBuilder<M, N>::DoAllDescents(int idx, int length, Trie* t, EvalNode* node, EvalNodeArena& arena) {
  unsigned int max_score = 0;
  int n = strlen(bd_[idx]);

  for (int j = 0; j < n; j++) {
    auto cc = bd_[idx][j] - 'a';
    if (t->StartsWord(cc)) {
      auto child = new EvalNode;
      child->cell_ = idx;
      child->letter_ = j;
      auto tscore = DoDFS(idx, length + (cc == kQ ? 2 : 1), t->Descend(cc), child, arena);
      auto owned_child = child;
      child = GetCanonicalNode(child);
      if (tscore > 0) {
        max_score = std::max(max_score, tscore);
        node->children_.push_back(child);
      }
      if (tscore == 0 || child != owned_child) {
        delete owned_child;
      } else {
        arena.AddNode(owned_child);
      }
    }
  }

  node->bound_ = max_score;
  node->points_ = 0;
  return max_score;
}

template<int M, int N>
unsigned int TreeBuilder<M, N>::DoDFS(int i, int length, Trie* t, EvalNode* node, EvalNodeArena& arena) {
  unsigned int score = 0;
  used_ ^= (1 << i);

  auto& neighbors = BucketBoggler<M, N>::NEIGHBORS[i];
  auto n_neighbors = neighbors[0];
  for (int j = 1; j <= n_neighbors; j++) {
    auto idx = neighbors[j];
    if ((used_ & (1<<idx)) == 0) {
      auto neighbor = new EvalNode;
      neighbor->letter_ = EvalNode::CHOICE_NODE;
      neighbor->cell_ = idx;
      auto tscore = DoAllDescents(idx, length, t, neighbor, arena);
      auto owned_neighbor = neighbor;
      neighbor = GetCanonicalNode(neighbor);
      if (tscore > 0) {
        score += tscore;
        node->children_.push_back(neighbor);
      }
      if (tscore == 0 || neighbor != owned_neighbor) {
        delete owned_neighbor;
      } else {
        arena.AddNode(owned_neighbor);
      }
    }
  }

  node->points_ = 0;
  if (t->IsWord()) {
    auto word_score = kWordScores[length];
    node->points_ = word_score;
    score += word_score;
    if (t->Mark() != runs_) {
      details_.sum_union += word_score;
      t->Mark(runs_);
    }
  }

  used_ ^= (1 << i);
  node->bound_ = score;
  return score;
}


template<int M, int N>
EvalNode* TreeBuilder<M, N>::GetCanonicalNode(EvalNode* node) {
  return node;
}

#endif // TREE_BUILDER_H
