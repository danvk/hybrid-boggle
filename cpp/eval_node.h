#ifndef EVAL_NODE_H
#define EVAL_NODE_H

#include <limits.h>
#include <iostream>
#include <map>
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
    for (auto node : owned_nodes) {
      // cout << "Freeing " << node << endl;
      delete node;
      // cout << "(done)" << endl;
    }
    owned_nodes.clear();
  }

  int NumNodes() {
    return owned_nodes.size();
  }

  void AddNode(T* node) {
    // for (auto n : owned_nodes) {
    //   if (n == node) {
    //     cout << "Double add!" << endl;
    //   }
    // }
    owned_nodes.push_back(node);
  }

  // friend EvalNode;

 private:
  vector<T*> owned_nodes;
};

typedef Arena<EvalNode> EvalNodeArena;
typedef Arena<vector<const EvalNode*>> VectorArena;

unique_ptr<EvalNodeArena> create_eval_node_arena();
unique_ptr<VectorArena> create_vector_arena();

class EvalNode {
 public:
  EvalNode() {}
  virtual ~EvalNode() {}

  const EvalNode*
  LiftChoice(int cell, int num_lets, EvalNodeArena& arena, bool dedupe=false, bool compress=false) const;

  variant<const EvalNode*, vector<const EvalNode*>*>
  ForceCell(int cell, int num_lets, EvalNodeArena& arena, VectorArena& vector_arena) const;

  variant<const EvalNode*, vector<const EvalNode*>*>
  ForceCellWork(int cell, int num_lets, EvalNodeArena& arena, VectorArena& vector_arena) const;

  // Must have forces.size() == M * N; set forces[i] = -1 to not force a cell.
  unsigned int ScoreWithForces(const vector<int>& forces, const vector<string>& cells) const;

  void FilterBelowThreshold(int min_score);
  unsigned int UniqueNodeCount() const;

  vector<pair<const EvalNode*, vector<pair<int, int>>>> MaxSubtrees() const;

  int8_t letter;
  int8_t cell;
  static const int8_t ROOT_NODE = -2;
  static const int8_t CHOICE_NODE = -1;

  // These might be the various options on a cell or the various directions.
  vector<const EvalNode*> children;

  // cached computation across all children
  unsigned int bound;

  // points contributed by _this_ node.
  unsigned int points;

  uint16_t choice_mask;

  mutable uint32_t cache_key;
  mutable uintptr_t cache_value;

  int RecomputeScore() const;
  int NodeCount() const;

 private:
  unsigned int ScoreWithForcesMask(const vector<int>& forces, uint16_t choice_mask, const vector<int>& num_letters) const;
  void MaxSubtreesHelp(vector<pair<const EvalNode*, vector<pair<int, int>>>>& out, vector<pair<int, int>> path) const;
  unsigned int UniqueNodeCountHelp(uint32_t mark) const;
};


#endif  // EVAL_NODE_H
