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

template <class T>
static void hash_combine(std::size_t& seed, const T& v) {
  std::hash<T> hasher;
  seed ^= hasher(v) + 0x9e3779b9 + (seed << 6) + (seed >> 2);
}

class EvalNodeArena;

class SumNode {
 public:
  SumNode() : points_(0), bound_(0), child_cells_(0) {}
  ~SumNode() {}

  uint64_t points_ : 16;
  uint64_t bound_ : 23;
  uint64_t child_cells_ : 25;
  ChoiceNode* children_[];

  void PrintJSON(int cell, int letter) const;

  // Shallow copy -- excludes children
  void CopyFrom(SumNode& other);

  // Must have forces.size() == M * N; set forces[i] = -1 to not force a cell.
  unsigned int ScoreWithForces(const vector<int>& forces) const;

  void SetChildren(uint32_t child_cells, const vector<ChoiceNode*>& children);

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

  vector<const SumNode*> OrderlyForceCell(int cell, int num_lets, EvalNodeArena& arena)
      const;

  vector<ChoiceNode*> GetChildren();
  map<int, ChoiceNode*> GetChildrenMap();
  void SetBoundsForTesting();

  size_t ShallowHash() const;
  bool ShallowEquals(const SumNode* other) const;
 private:
};

class ChoiceNode {
 public:
  ChoiceNode() : bound_(0), child_letters_(0) {}
  ~ChoiceNode() {}

  uint32_t bound_;
  uint32_t child_letters_;
  SumNode* children_[];

  int NumChildren() const { return std::popcount(child_letters_); }
  uint32_t Bound() const { return bound_; }
  uint32_t ChildLetters() const { return child_letters_; }

  void PrintJSON(int cell) const;

  // Shallow copy -- excludes children
  void CopyFrom(ChoiceNode& other);

  unsigned int ScoreWithForces(int cell, const vector<int>& forces) const;

  int NodeCount() const;
  int WordCount() const;
  vector<SumNode*> GetChildren();

  // Find child SumNode for given letter using popcount on child_letters_ bitmask
  SumNode* GetChildForLetter(int letter) const;
  void SetBoundsForTesting();

  size_t ShallowHash() const;
  bool ShallowEquals(const ChoiceNode* other) const;
 private:
};

#endif  // EVAL_NODE_H
