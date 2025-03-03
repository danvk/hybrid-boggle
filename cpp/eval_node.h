#ifndef EVAL_NODE_H
#define EVAL_NODE_H

#include <limits.h>

#include <cassert>
#include <iostream>
#include <map>
#include <memory>
#include <unordered_map>
#include <variant>
#include <vector>

using namespace std;

class EvalNode;

template <typename T>
class Arena {
 public:
  ~Arena() { FreeTheChildren(); }

  void FreeTheChildren() {
    // cout << "Freeing " << owned_nodes.size() << " nodes" << endl;
    for (auto node : owned_nodes_) {
      // cout << "Freeing " << node << endl;
      delete node;
      // cout << "(done)" << endl;
    }
    owned_nodes_.clear();
  }

  int NumNodes() { return owned_nodes_.size(); }

  void AddNode(T* node) {
    // for (auto n : owned_nodes_) {
    //   if (n == node) {
    //     cout << "Double add!" << endl;
    //   }
    // }
    owned_nodes_.push_back(node);
  }

  // For testing
  T* NewNode();

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
  EvalNode() : points_(0) {}
  ~EvalNode() {}

  void AddWord(vector<pair<int, int>> choices, int points, EvalNodeArena& arena);
  void AddWordWork(
      int num_choices,
      pair<int, int>* choices,
      const int* num_letters,
      int points,
      EvalNodeArena& arena
  );

  bool StructuralEq(const EvalNode& other) const;
  void PrintJSON() const;

  // Must have forces.size() == M * N; set forces[i] = -1 to not force a cell.
  unsigned int ScoreWithForces(const vector<int>& forces) const;

  int FilterBelowThreshold(int min_score);

  uint64_t StructuralHash() const;

  int8_t letter_;
  int8_t cell_;
  static const int8_t ROOT_NODE = -2;
  static const int8_t CHOICE_NODE = -1;

  // points contributed by _this_ node.
  uint16_t points_;

  // cached computation across all children
  uint32_t bound_;

  // These might be the various options on a cell or the various directions.
  // TODO: the "const" here is increasingly a joke.
  vector<const EvalNode*> children_;

  int RecomputeScore() const;
  int NodeCount() const;
  unsigned int UniqueNodeCount(uint32_t mark) const;

  tuple<vector<pair<int, string>>, vector<int>, vector<int>> OrderlyBound(
      int cutoff,
      const vector<string>& cells,
      const vector<int>& split_order,
      const vector<pair<int, int>>& preset_cells
  ) const;

  vector<const EvalNode*> OrderlyForceCell(int cell, int num_lets, EvalNodeArena& arena)
      const;

 private:
  unsigned int ScoreWithForcesMask(const vector<int>& forces, uint16_t choice_mask)
      const;
};

#endif  // EVAL_NODE_H
