#ifndef EVAL_NODE_H
#define EVAL_NODE_H

#include <limits.h>

#include <cassert>
#include <deque>
#include <iostream>
#include <map>
#include <memory>
#include <unordered_map>
#include <variant>
#include <vector>

using namespace std;

class EvalNode;

// Allocate this much memory at once.
const int EVAL_NODE_ARENA_BUFFER_SIZE = 1'048'576;

class EvalNodeArena {
 public:
  EvalNodeArena() : num_nodes_(0), tip_(EVAL_NODE_ARENA_BUFFER_SIZE) {
    // TODO: this is a waste for all but the tree builder
    available_nodes_.resize(32);
  }
  ~EvalNodeArena() { FreeTheChildren(); }

  void FreeTheChildren() {
    // cout << "Freeing " << buffers_.size() << " buffers" << endl;
    for (auto buffer : buffers_) {
      // cout << "Freeing " << node << endl;
      delete[] buffer;
      // cout << "(done)" << endl;
    }
    buffers_.clear();
  }

  int NumNodes() { return num_nodes_; }

  EvalNode* NewNodeWithCapacity(uint8_t capacity);

  void ReleaseNode(EvalNode* node);

  // For testing
  EvalNode* NewRootNodeWithCapacity(uint8_t capacity);
  void PrintStats();
  int Index(const EvalNode* n);

 private:
  void AddBuffer();
  vector<char*> buffers_;
  // capacity -> available nodes;
  // see https://stackoverflow.com/q/6292332/388951 for deque implementation details
  vector<deque<EvalNode*>> available_nodes_;
  int num_nodes_;
  int tip_;
};

unique_ptr<EvalNodeArena> create_eval_node_arena();

class EvalNode {
 public:
  EvalNode() : points_(0), num_children_(0) {}
  ~EvalNode() {}

  void AddWord(vector<pair<int, int>> choices, int points, EvalNodeArena& arena);
  EvalNode* AddWordWork(
      int num_choices, pair<int, int>* choices, int points, EvalNodeArena& arena
  );

  bool StructuralEq(const EvalNode& other) const;
  void PrintJSON(EvalNodeArena& arena) const;

  // Must have forces.size() == M * N; set forces[i] = -1 to not force a cell.
  unsigned int ScoreWithForces(const vector<int>& forces) const;

  void SetChildrenFromVector(const vector<EvalNode*>& children);
  uint64_t StructuralHash() const;

  void AssertOrderly(const vector<int>& split_order, int max_index = -1) const;

  int8_t letter_;
  int8_t cell_;
  static const int8_t ROOT_NODE = -2;
  static const int8_t CHOICE_NODE = -1;

  // points contributed by _this_ node.
  uint16_t points_;

  uint8_t num_children_;
  uint8_t capacity_;

  // cached computation across all children
  uint32_t bound_;

  // These might be the various options on a cell or the various directions.
  EvalNode* children_[];

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

  vector<EvalNode*> GetChildren();

 private:
  // This must be called with the same arena that was used to create child.
  // It may trigger a reallocation, in which case it will return a new child node.
  EvalNode* AddChild(EvalNode* child, EvalNodeArena& arena);
};

#endif  // EVAL_NODE_H
