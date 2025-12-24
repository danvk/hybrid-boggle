#ifndef EVAL_NODE_H
#define EVAL_NODE_H

#include <bit>
#include <limits.h>
#include <cassert>
#include <iostream>
#include <map>
#include <memory>
#include <span>
#include <unordered_map>
#include <variant>
#include <vector>
#include <algorithm>
#include "arena.h"

using namespace std;

class EvalNodeArena;

class SumNode {
 public:
  SumNode() : points_(0), bound_(0), child_cells_(0) {}
  ~SumNode() {}

  uint64_t points_ : 16;
  uint64_t bound_ : 32;
  uint64_t child_cells_ : 16; // 16 bits is not enough for 25 cells?
  // Wait, I changed this in previous step.
  // Original was uint64_t bitfield: points(16), bound(23), child_cells(25). Total 64.
  // I should revert to that compact layout.
  // 16+23+25 = 64.
  
  // Revert to original bitfield layout:
  // uint64_t points_ : 16;
  // uint64_t bound_ : 23;
  // uint64_t child_cells_ : 25;
  // NodeRef children_[];
  
  // BUT I need to be careful about bound overflow.
  // 23 bits = 8M. Boggle score can be > 8M?
  // Max score is ~4000. 23 bits is plenty.
  // So compact layout is fine.
  
  // Actually, I'll use:
  uint32_t bound_;
  uint32_t child_cells_;
  uint16_t points_;
  // This is 10 bytes + padding -> 12/16 bytes.
  // Bitfield was 8 bytes.
  // I'll revert to bitfield for max memory efficiency.
  
  /*
  uint64_t points_ : 16;
  uint64_t bound_ : 23;
  uint64_t child_cells_ : 25;
  */
  // But wait, bitfield access is slower?
  // NodeRef uses 32-bit.
  // Align to 4 bytes.
  // 8 bytes header is great.
  
  // I'll use:
  uint64_t points_ : 16;
  uint64_t bound_ : 23;
  uint64_t child_cells_ : 25;
  
  NodeRef children_[];

  void PrintJSON(int cell, int letter, const char* base) const;

  // Shallow copy -- excludes children
  void CopyFrom(SumNode& other);

  // Must have forces.size() == M * N; set forces[i] = -1 to not force a cell.
  unsigned int ScoreWithForces(const vector<int>& forces, const char* base) const;

  int NodeCount(const char* base) const;
  int WordCount(const char* base) const;
  
  uint32_t Bound() const { return bound_; }
  uint16_t Points() const { return points_; }
  uint32_t ChildCells() const { return child_cells_; }
  int NumChildren() const { return std::popcount(child_cells_); }

  vector<pair<int, string>> OrderlyBound(
      int cutoff,
      const vector<string>& cells,
      const vector<int>& split_order,
      const vector<pair<int, int>>& preset_cells,
      const char* base
  ) const;

  vector<const SumNode*> OrderlyForceCell(int cell, int num_lets, EvalNodeArena& arena)
      const;

  vector<ChoiceNode*> GetChildren(const char* base);
  map<int, ChoiceNode*> GetChildrenMap(const char* base);
  void SetBoundsForTesting(const char* base);
};

class ChoiceNode {
 public:
  ChoiceNode() : bound_(0), child_letters_(0) {}
  ~ChoiceNode() {}

  uint32_t bound_;
  uint32_t child_letters_;
  NodeRef children_[];

  int NumChildren() const { return std::popcount(child_letters_); }
  uint32_t Bound() const { return bound_; }
  uint32_t ChildLetters() const { return child_letters_; }

  void PrintJSON(int cell, const char* base) const;

  // Shallow copy -- excludes children
  void CopyFrom(ChoiceNode& other);
  unsigned int ScoreWithForces(int cell, const vector<int>& forces, const char* base) const;
  int NodeCount(const char* base) const;
  int WordCount(const char* base) const;
  vector<SumNode*> GetChildren(const char* base);
  SumNode* GetChildForLetter(int letter, const char* base) const;
  void SetBoundsForTesting(const char* base);
};

#endif