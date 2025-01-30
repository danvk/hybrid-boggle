#ifndef TREE_BUILDER_H
#define TREE_BUILDER_H

#include "ibuckets.h"
#include "eval_node.h"

using namespace std;

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
  const EvalNode* BuildTree(EvalNodeArena& arena);

 private:
  EvalNode* root_;

  // This one does not depend on M, N
  unsigned int DoAllDescents(int idx, int length, Trie* t, EvalNode* node, EvalNodeArena& arena);
  unsigned int DoDFS(int i, int length, Trie* t, EvalNode* node, EvalNodeArena& arena);
};

// TODO: can this not be a template method?
template <int M, int N>
const EvalNode* TreeBuilder<M, N>::BuildTree(EvalNodeArena& arena) {
  // auto start = chrono::high_resolution_clock::now();
  root_ = new EvalNode();

  root_->letter = EvalNode::ROOT_NODE;
  root_->cell = 0; // irrelevant
  root_->points = 0;

  details_.max_nomark = 0;
  details_.sum_union = 0;
  details_.bailout_cell = -1;
  runs_ = 1 + dict_->Mark();
  used_ = 0;

  for (int i = 0; i < M * N; i++) {
    auto child = new EvalNode();
    child->letter = EvalNode::CHOICE_NODE;
    child->cell = i;
    auto score = DoAllDescents(i, 0, dict_, child, arena);
    if (score > 0) {
      details_.max_nomark += score;
      root_->children.push_back(child);
      arena.AddNode(child);
      if (strlen(bd_[i]) > 1) {
        child->choice_mask |= 1 << i;
      }
      root_->choice_mask |= child->choice_mask;
    } else {
      delete child;
    }
  }

  root_->bound = details_.max_nomark;
  dict_->Mark(runs_);
  // auto finish = chrono::high_resolution_clock::now();
  // auto duration = chrono::duration_cast<chrono::milliseconds>(finish - start).count();
  // TODO: record tree building time
  // cout << "build tree: " << duration << " ms" << endl;
  auto root = root_;
  root_ = NULL;
  arena.AddNode(root);
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
      child->cell = idx;
      child->letter = j;
      auto tscore = DoDFS(idx, length + (cc == kQ ? 2 : 1), t->Descend(cc), child, arena);
      if (tscore > 0) {
        max_score = std::max(max_score, tscore);
        node->children.push_back(child);
        arena.AddNode(child);
        node->choice_mask |= child->choice_mask;
      } else {
        delete child;
      }
    }
  }

  node->bound = max_score;
  node->points = 0;
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
      neighbor->letter = EvalNode::CHOICE_NODE;
      neighbor->cell = idx;
      // TODO: optimize
      if (strlen(bd_[idx]) > 1) {
        neighbor->choice_mask = 1 << idx;
      }
      auto tscore = DoAllDescents(idx, length, t, neighbor, arena);
      if (tscore > 0) {
        score += tscore;
        node->children.push_back(neighbor);
        arena.AddNode(neighbor);
        node->choice_mask |= neighbor->choice_mask;
      } else {
        delete neighbor;
      }
    }
  }

  node->points = 0;
  if (t->IsWord()) {
    auto word_score = kWordScores[length];
    node->points = word_score;
    score += word_score;
    if (t->Mark() != runs_) {
      details_.sum_union += word_score;
      t->Mark(runs_);
    }
  }

  used_ ^= (1 << i);
  node->bound = score;
  return score;
}

#endif // TREE_BUILDER_H
