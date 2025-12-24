#ifndef EVAL_NODE_H
#define EVAL_NODE_H

#include <bit>
#include <vector>
#include <map>
#include <cassert>
#include <iostream>
#include <span>
#include "arena.h"

using namespace std;

class SumNode {
 public:
  SumNode() : points_(0), bound_(0), child_cells_(0) {}
  
  uint64_t points_ : 16;
  uint64_t bound_ : 23;
  uint64_t child_cells_ : 25;
  
  ChoiceNode* children_[]; // Pointer!

  // API
  void PrintJSON(int cell, int letter) const;
  void CopyFrom(SumNode& other);
  unsigned int ScoreWithForces(const vector<int>& forces) const;
  
  int NodeCount() const;
  int WordCount() const;
  
  uint32_t Bound() const { return bound_; }
  uint16_t Points() const { return points_; }
  uint32_t ChildCells() const { return child_cells_; }
  int NumChildren() const { return std::popcount(child_cells_); }

  vector<pair<int, string>> OrderlyBound(
      int cutoff,
      const vector<string>& cells,
      const vector<int>& split_order,
      const vector<pair<int, int>>& preset_cells
  ) const;

  vector<const SumNode*> OrderlyForceCell(int cell, int num_lets, EvalNodeArena& arena) const;

  vector<ChoiceNode*> GetChildren();
  map<int, ChoiceNode*> GetChildrenMap();
  void SetBoundsForTesting();
};

class ChoiceNode {
 public:
  ChoiceNode() : bound_(0), child_letters_(0) {}
  
  uint32_t bound_;
  uint32_t child_letters_;
  SumNode* children_[]; // Pointer!

  int NumChildren() const { return std::popcount(child_letters_); }
  uint32_t Bound() const { return bound_; }
  uint32_t ChildLetters() const { return child_letters_; }

  void PrintJSON(int cell) const;
  void CopyFrom(ChoiceNode& other);
  unsigned int ScoreWithForces(int cell, const vector<int>& forces) const;
  int NodeCount() const;
  int WordCount() const;
  vector<SumNode*> GetChildren();
  SumNode* GetChildForLetter(int letter) const;
  void SetBoundsForTesting();
};

#endif
