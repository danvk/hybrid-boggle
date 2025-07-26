#ifndef ARENA_H
#define ARENA_H

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
const uint64_t EVAL_NODE_ARENA_BUFFER_SIZE = 64 << 20;

constexpr int NUM_INTERNED = 128;

class EvalNodeArena {
 public:
  EvalNodeArena();
  ~EvalNodeArena();

  uint64_t NumNodes() { return num_nodes_; }
  uint64_t BytesAllocated() { return buffers_.size() * EVAL_NODE_ARENA_BUFFER_SIZE; }

  pair<int, int> SaveLevel();
  void ResetLevel(pair<int, int> level);

  template <typename T>
  T* NewNodeWithCapacity(uint8_t capacity);

  SumNode* NewSumNodeWithCapacity(uint8_t capacity);
  ChoiceNode* NewChoiceNodeWithCapacity(uint8_t capacity);

  SumNode* GetCanonicalNode(int points) {
    assert(points >= 1 && points <= NUM_INTERNED);
    return canonical_nodes_[points - 1];
  }

  // For testing
  SumNode* NewRootNodeWithCapacity(uint8_t capacity);
  void PrintStats();

 private:
  void AddBuffer();
  vector<char*> buffers_;
  uint64_t num_nodes_;
  int cur_buffer_;
  int tip_;
  vector<pair<int, int>> watermarks_;
  vector<SumNode*> canonical_nodes_;
};

unique_ptr<EvalNodeArena> create_eval_node_arena();

template <typename T>
T* EvalNodeArena::NewNodeWithCapacity(uint8_t capacity) {
  num_nodes_++;
  int size = sizeof(T) + capacity * sizeof(T::children_[0]);
  // cout << "sizeof(EvalNode)=" << sizeof(EvalNode) << " size: " << size << endl;
  if (tip_ + size > EVAL_NODE_ARENA_BUFFER_SIZE) {
    AddBuffer();
  }
  char* buf = &buffers_[cur_buffer_][tip_];
  T* n = new (buf) T;
  // TODO: update tip_ to enforce alignment
  tip_ += size;
  n->capacity_ = capacity;
  return n;
}

#endif
