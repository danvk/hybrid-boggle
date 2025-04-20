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

class ChoiceNode;
class SumNode;

// Allocate this much memory at once.
const int EVAL_NODE_ARENA_BUFFER_SIZE = 1'048'576;

class EvalNodeArena {
 public:
  EvalNodeArena() : num_nodes_(0), tip_(EVAL_NODE_ARENA_BUFFER_SIZE) {}
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

  template <typename T>
  T* NewNodeWithCapacity(uint8_t capacity);

  SumNode* NewSumNodeWithCapacity(uint8_t capacity);
  ChoiceNode* NewChoiceNodeWithCapacity(uint8_t capacity);

  // For testing
  SumNode* NewRootNodeWithCapacity(uint8_t capacity);
  void PrintStats();

 private:
  void AddBuffer();
  vector<char*> buffers_;
  int num_nodes_;
  int tip_;
};

unique_ptr<EvalNodeArena> create_eval_node_arena();

class SumNode {
 public:
  SumNode() : points_(0), num_children_(0) {}
  ~SumNode() {}

  void AddWord(vector<pair<int, int>> choices, int points, EvalNodeArena& arena);
  SumNode* AddWordWork(
      int num_choices,
      pair<int, int>* choices,
      const int* num_letters,
      int points,
      EvalNodeArena& arena
  );

  int8_t letter_;
  uint16_t points_;
  uint8_t num_children_;
  uint8_t capacity_;
  uint32_t bound_;
  ChoiceNode* children_[];

  static const int8_t ROOT_NODE = -2;

  void PrintJSON() const;

  void CopyFrom(SumNode& other);

  // Must have forces.size() == M * N; set forces[i] = -1 to not force a cell.
  unsigned int ScoreWithForces(const vector<int>& forces) const;

  void SetChildrenFromVector(const vector<ChoiceNode*>& children);

  int NodeCount() const;

  tuple<vector<pair<int, string>>, vector<int>, vector<int>> OrderlyBound(
      int cutoff,
      const vector<string>& cells,
      const vector<int>& split_order,
      const vector<pair<int, int>>& preset_cells
  ) const;

  vector<const SumNode*> OrderlyForceCell(
      int cell, int num_lets, EvalNodeArena& arena
  ) const;

  vector<ChoiceNode*> GetChildren();
  SumNode* AddChild(ChoiceNode* child, EvalNodeArena& arena);

 private:
};

class ChoiceNode {
 public:
  ChoiceNode() : num_children_(0) {}
  ~ChoiceNode() {}

  int8_t cell_;
  uint8_t num_children_;
  uint8_t capacity_;
  uint32_t bound_;
  SumNode* children_[];

  void PrintJSON() const;

  void CopyFrom(ChoiceNode& other);

  unsigned int ScoreWithForces(const vector<int>& forces) const;

  int NodeCount() const;
  vector<SumNode*> GetChildren();
  ChoiceNode* AddChild(SumNode* child, EvalNodeArena& arena);

 private:
};

#endif  // EVAL_NODE_H
