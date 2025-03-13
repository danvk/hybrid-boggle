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

// Allocate this much memory at once.
// TODO: increase this
const int EVAL_NODE_ARENA_BUFFER_SIZE = 1'048'576;

class EvalNodeArena {
 public:
  EvalNodeArena() : num_nodes_(0), cur_buffer_(-1), tip_(EVAL_NODE_ARENA_BUFFER_SIZE) {}
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
  int BytesAllocated() { return buffers_.size() * EVAL_NODE_ARENA_BUFFER_SIZE; }

  EvalNode* NewNodeWithCapacity(uint8_t capacity);

  pair<int, int> SaveLevel();
  void ResetLevel(pair<int, int> level);

  // For testing
  EvalNode* NewRootNodeWithCapacity(uint8_t capacity);
  void PrintStats();

 private:
  void AddBuffer();
  vector<char*> buffers_;
  int num_nodes_;
  int cur_buffer_;
  int tip_;
  vector<pair<int, int>> watermarks_;
};

unique_ptr<EvalNodeArena> create_eval_node_arena();

class EvalNode {
 public:
  EvalNode() : points_(0), num_children_(0) {}
  ~EvalNode() {}

  void AddWord(vector<pair<int, int>> choices, int points, EvalNodeArena& arena);
  EvalNode* AddWordWork(
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

  void SetChildrenFromVector(const vector<EvalNode*>& children);
  uint64_t StructuralHash() const;

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
  EvalNode* AddChild(EvalNode* child, EvalNodeArena& arena);
};

#endif  // EVAL_NODE_H
