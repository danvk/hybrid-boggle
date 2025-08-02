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
  uint16_t points_;
  uint8_t num_children_;
  uint8_t capacity_;
  ChoiceNode* children_[];

  void PrintJSON() const;

  void CopyFrom(const SumNode* other);

  // Must have forces.size() == M * N; set forces[i] = -1 to not force a cell.
  unsigned int ScoreWithForces(const vector<int>& forces) const;

  void SetChildrenFromVector(const vector<ChoiceNode*>& children);

  int NodeCount() const;
  int WordCount() const;
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
  void SetBoundsForTesting();

  // Shallow hash and equality test based on child pointers
  uint32_t Hash() const;
  bool IsEqual(const SumNode& other) const;
  bool operator==(const SumNode& other) const { return IsEqual(other); }

 private:
};

class ChoiceNode {
 public:
  ChoiceNode() : bound_(0), cell_(0), child_letters_(0), capacity_(0) {}
  ~ChoiceNode() {}

  uint32_t bound_ : 24;
  uint32_t cell_ : 8;  // Changed to uint32_t bit field to fit in same word
  uint32_t child_letters_ : 26;
  uint32_t capacity_ : 6;
  SumNode* children_[];

  int NumChildren() const { return std::popcount(child_letters_); }
  uint32_t Bound() const { return bound_; }
  uint32_t ChildLetters() const { return child_letters_; }
  uint32_t Cell() const { return cell_; }

  void PrintJSON() const;

  void CopyFrom(const ChoiceNode* other);

  unsigned int ScoreWithForces(const vector<int>& forces) const;

  int NodeCount() const;
  int WordCount() const;
  vector<SumNode*> GetChildren();

  // Find child SumNode for given letter using popcount on child_letters_ bitmask
  SumNode* GetChildForLetter(int letter) const;
  void SetBoundsForTesting();

  // Shallow hash and equality test based on child pointers
  uint32_t Hash() const;
  bool IsEqual(const ChoiceNode& other) const;

  bool operator==(const ChoiceNode& other) const { return IsEqual(other); }

 private:
};

namespace std {
template <>
struct hash<SumNode> {
  size_t operator()(const SumNode& x) const { return x.Hash(); }
};
template <>
struct hash<ChoiceNode> {
  size_t operator()(const ChoiceNode& x) const { return x.Hash(); }
};

}  // namespace std

#endif  // EVAL_NODE_H
