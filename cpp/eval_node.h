#ifndef EVAL_NODE_H
#define EVAL_NODE_H

#include <limits.h>
#include <iostream>
#include <map>
#include <memory>
#include <unordered_map>
#include <variant>
#include <vector>
#include <cassert>

using namespace std;

class EvalNode;

template<typename T>
class Arena {
 public:
  ~Arena() {
    FreeTheChildren();
  }

  void FreeTheChildren() {
    // cout << "Freeing " << owned_nodes.size() << " nodes" << endl;
    for (auto node : owned_nodes_) {
      // cout << "Freeing " << node << endl;
      delete node;
      // cout << "(done)" << endl;
    }
    owned_nodes_.clear();
  }

  int NumNodes() {
    return owned_nodes_.size();
  }

  void AddNode(T* node) {
    // for (auto n : owned_nodes_) {
    //   if (n == node) {
    //     cout << "Double add!" << endl;
    //   }
    // }
    owned_nodes_.push_back(node);
  }

  // Returns the number of nodes deleted
  int MarkAndSweep(T* root, uint32_t mark);

  // friend EvalNode;

 private:
  vector<T*> owned_nodes_;
};

typedef Arena<EvalNode> EvalNodeArena;
typedef Arena<vector<const EvalNode*>> VectorArena;

unique_ptr<EvalNodeArena> create_eval_node_arena();
unique_ptr<VectorArena> create_vector_arena();

class EvalNode {
 public:
  EvalNode() : points_(0), choice_mask_(0), hash_(0) {}
  virtual ~EvalNode() {}

  const EvalNode*
  LiftChoice(int cell, int num_lets, EvalNodeArena& arena, uint32_t mark, bool dedupe=false, bool compress=false) const;

  variant<const EvalNode*, vector<const EvalNode*>*>
  ForceCell(int cell, int num_lets, EvalNodeArena& arena, VectorArena& vector_arena, uint32_t mark, bool dedupe=false, bool compress=false) const;

  variant<const EvalNode*, vector<const EvalNode*>*>
  ForceCellWork(int cell, int num_lets, EvalNodeArena& arena, VectorArena& vector_arena, uint32_t mark, bool dedupe, bool compress, unordered_map<uint64_t, const EvalNode*>& force_cell_cache) const;

  // Must have forces.size() == M * N; set forces[i] = -1 to not force a cell.
  unsigned int ScoreWithForces(const vector<int>& forces) const;

  int FilterBelowThreshold(int min_score);

  vector<pair<const EvalNode*, vector<pair<int, int>>>> MaxSubtrees() const;

  uint64_t StructuralHash() const;

  void SetChoicePointMask(const vector<int>& num_letters);

  void ResetChoicePointMask();

  int8_t letter_;
  int8_t cell_;
  static const int8_t ROOT_NODE = -2;
  static const int8_t CHOICE_NODE = -1;

  // These might be the various options on a cell or the various directions.
  vector<const EvalNode*> children_;

  // cached computation across all children
  uint32_t bound_;

  // points contributed by _this_ node.
  uint32_t points_;

  // Note: using uint16_t here precludes 5x5 Boggle trees
  uint16_t choice_mask_;

  mutable uint32_t cache_key_;
  mutable variant<const EvalNode*, vector<const EvalNode*>*> cache_value_;

  mutable uint64_t hash_;

  int RecomputeScore() const;
  int NodeCount() const;
  unsigned int UniqueNodeCount(uint32_t mark) const;
  void MarkAllWith(uint32_t mark);

  vector<string> BoundRemainingBoards(
    vector<string> cells,
    int cutoff,
    vector<int> split_order
  );

 private:
  unsigned int ScoreWithForcesMask(const vector<int>& forces, uint16_t choice_mask) const;
  void MaxSubtreesHelp(vector<pair<const EvalNode*, vector<pair<int, int>>>>& out, vector<pair<int, int>> path) const;
};

#endif  // EVAL_NODE_H
