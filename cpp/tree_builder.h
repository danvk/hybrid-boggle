#ifndef TREE_BUILDER_H
#define TREE_BUILDER_H

#include "ibuckets.h"
#include "eval_node.h"

using namespace std;

// TODO: inheritance isn't that helpful here.
// TODO: templating on M, N probably isn't helpful, either.
template <int M, int N>
class TreeBuilder : public BucketBoggler<M, N> {
 public:
  TreeBuilder(Trie* t) : BucketBoggler<M, N>(t) {}
  virtual ~TreeBuilder() {}

  // These are "dependent names", see https://stackoverflow.com/a/1528010/388951.
  using BucketBoggler<M, N>::dict_;
  using BucketBoggler<M, N>::runs_;
  using BucketBoggler<M, N>::bd_;
  using BucketBoggler<M, N>::used_;
  using BucketBoggler<M, N>::details_;

  /** Build an EvalTree for the current board. */
  const EvalNode* BuildTree(EvalNodeArena& arena, bool dedupe=false);

 private:
  EvalNode* root_;
  bool dedupe_;
  unordered_map<uint64_t, EvalNode*> node_cache_;

  // This one does not depend on M, N
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
      if (strlen(bd_[i]) > 1) {
        child->choice_mask_ |= 1 << i;
      }
      root_->choice_mask_ |= child->choice_mask_;
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
        node->choice_mask_ |= child->choice_mask_;
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
      // TODO: optimize
      if (strlen(bd_[idx]) > 1) {
        neighbor->choice_mask_ = 1 << idx;
      }
      auto tscore = DoAllDescents(idx, length, t, neighbor, arena);
      auto owned_neighbor = neighbor;
      neighbor = GetCanonicalNode(neighbor);
      if (tscore > 0) {
        score += tscore;
        node->children_.push_back(neighbor);
        node->choice_mask_ |= neighbor->choice_mask_;
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
  if (!dedupe_) {
    return node;
  }
  auto h = node->StructuralHash();
  auto prev = node_cache_.find(h);
  if (prev != node_cache_.end()) {
    return prev->second;
  }
  node_cache_[h] = node;
  return node;
}

#endif // TREE_BUILDER_H
