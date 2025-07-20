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
  SumNode() : bound_(0), is_merged_(0), points_(0), num_children_(0) {}
  ~SumNode() {}

  uint32_t bound_ : 24;
  uint32_t is_merged_ : 8;
  uint16_t points_;
  uint8_t num_children_;
  uint8_t capacity_;
  ChoiceNode* children_[];

  void PrintJSON() const;

  // Shallow copy -- excludes children
  void CopyFrom(SumNode& other);

  // Must have forces.size() == M * N; set forces[i] = -1 to not force a cell.
  unsigned int ScoreWithForces(const vector<int>& forces) const;

  void SetChildrenFromVector(const vector<ChoiceNode*>& children);

  int NodeCount() const;
  int WordCount() const;
  uint32_t Bound() const { return bound_; }
  pair<unordered_map<int, int>, unordered_map<int, int>> ChildStats() const {
    unordered_map<int, int> sums, choices;
    ChildStatsHelp(sums, choices);
    return {sums, choices};
  }

  // pair<vector<pair<int, string>>, tuple<int, int, int>>
  vector<pair<int, string>> OrderlyBound(
      int cutoff,
      const vector<string>& cells,
      const vector<int>& split_order,
      const vector<pair<int, int>>& preset_cells
  );

  vector<const SumNode*> OrderlyForceCell(int cell, int num_lets, EvalNodeArena& arena)
      const;

  vector<ChoiceNode*> GetChildren();
  void SetBoundsForTesting();

  void ChildStatsHelp(
      unordered_map<int, int>& sum_counts, unordered_map<int, int>& choice_counts
  ) const;

  void FillBoundStats(int& n_init, int& n_merged, int& n_visited) const;
};

class ChoiceNode {
 public:
  ChoiceNode() : bound_(0), cell_(0), is_merged_(0), child_letters_(0), capacity_(0) {}
  ~ChoiceNode() {}

  uint32_t bound_ : 24;
  uint32_t cell_ : 6;
  uint32_t is_merged_ : 2;
  uint32_t child_letters_ : 26;
  uint32_t capacity_ : 6;
  SumNode* children_[];

  int NumChildren() const { return std::popcount(child_letters_); }
  uint32_t Bound() const { return bound_; }
  uint32_t ChildLetters() const { return child_letters_; }
  uint32_t Cell() const { return cell_; }

  void PrintJSON() const;

  // Shallow copy -- excludes children
  void CopyFrom(ChoiceNode& other);

  unsigned int ScoreWithForces(const vector<int>& forces) const;

  int NodeCount() const;
  int WordCount() const;
  vector<SumNode*> GetChildren();

  // Find child SumNode for given letter using popcount on child_letters_ bitmask
  SumNode* GetChildForLetter(int letter) const;
  void SetBoundsForTesting();

  void ChildStatsHelp(
      unordered_map<int, int>& sum_counts, unordered_map<int, int>& choice_counts
  ) const;

  void FillBoundStats(int& n_init, int& n_merged, int& n_visited) const;

 private:
};

#endif  // EVAL_NODE_H
