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

#include "arena.h"

using namespace std;

class EvalNodeArena;

class SumNode {
 public:
  SumNode() : bound_(0), points_(0), num_children_(0) {}
  ~SumNode() {}

  uint32_t bound_ : 24;
  int8_t letter_;
  uint16_t points_;
  uint8_t num_children_;
  uint8_t capacity_;
  ChoiceNode* children_[];

  static const int8_t ROOT_NODE = -2;

  // Add a new path to the tree, or return an existing one.
  // This does not touch points_ or bound_ on any nodes.
  // Returns `this` or a new version of this node if a reallocation happened.
  // *leaf will be set to the new or existing leaf node.
  SumNode* AddWord(
      int choices[],
      unsigned int used_ordered,
      const int split_order[],
      EvalNodeArena& arena,
      SumNode** leaf  // output parameter
  );

  void PrintJSON() const;

  // Shallow copy -- excludes children
  void CopyFrom(SumNode& other);

  // Must have forces.size() == M * N; set forces[i] = -1 to not force a cell.
  unsigned int ScoreWithForces(const vector<int>& forces) const;

  void SetChildrenFromVector(const vector<ChoiceNode*>& children);

  int NodeCount() const;
  uint32_t Bound() const { return bound_; }

  vector<pair<int, string>> OrderlyBound(
      int cutoff,
      const vector<string>& cells,
      const vector<int>& split_order,
      const vector<pair<int, int>>& preset_cells
  ) const;

  vector<const SumNode*> OrderlyForceCell(int cell, int num_lets, EvalNodeArena& arena)
      const;

  vector<ChoiceNode*> GetChildren();
  SumNode* AddChild(ChoiceNode* child, EvalNodeArena& arena);

  // Decode the points_ and bound_ fields as set by OrderlyTreeBuilder,
  // setting them to the correct values for this entire tree.
  // See comment near EncodeWordInSumNode for details on the encoding.
  void DecodePointsAndBound(vector<vector<uint32_t>>& wordlists);

  // Wrapper with pybind11-friendly parameter types.
  void AddWordWithPointsForTesting(
      vector<int> choices,
      unsigned int used_ordered,
      vector<int> split_order,
      int points,
      EvalNodeArena& arena
  );

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

  // Shallow copy -- excludes children
  void CopyFrom(ChoiceNode& other);

  unsigned int ScoreWithForces(const vector<int>& forces) const;

  int NodeCount() const;
  vector<SumNode*> GetChildren();
  ChoiceNode* AddChild(SumNode* child, EvalNodeArena& arena);

  // See corresponding method on SumNode
  void DecodePointsAndBound(vector<vector<uint32_t>>& wordlists);

 private:
};

#endif  // EVAL_NODE_H
