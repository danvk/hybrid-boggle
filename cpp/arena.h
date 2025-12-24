#ifndef ARENA_H
#define ARENA_H

#include <vector>
#include <cstdint>
#include <iostream>
#include <memory>
#include <cassert>

using namespace std;

class ChoiceNode;
class SumNode;

// Simple bump-pointer arena for 64-bit pointers.
// We use a vector of large blocks to ensure pointer stability.
constexpr size_t BLOCK_SIZE = 64 * 1024 * 1024; // 64MB blocks
constexpr int NUM_INTERNED = 128;

class EvalNodeArena {
 public:
  EvalNodeArena();
  ~EvalNodeArena();

  template <typename T>
  T* NewNodeWithCapacity(uint8_t capacity);

  SumNode* NewSumNodeWithCapacity(uint8_t capacity);
  ChoiceNode* NewChoiceNodeWithCapacity(uint8_t capacity);

  SumNode* GetCanonicalNode(int points) {
    assert(points >= 1 && points <= NUM_INTERNED);
    return canonical_nodes_[points - 1];
  }

  // Testing helper
  SumNode* NewRootNodeWithCapacity(uint8_t capacity);
  
  uint64_t NumNodes() { return num_nodes_; }
  uint64_t BytesAllocated() { return bytes_allocated_; }
  
  // Minimal checkpointing for force operations
  // We can just save the index of current block and offset.
  struct State {
      size_t block_idx;
      size_t offset;
  };
  State SaveLevel();
  void ResetLevel(State state);

  void PrintStats();

 private:
  vector<char*> blocks_;
  size_t current_offset_;
  uint64_t num_nodes_;
  uint64_t bytes_allocated_;
  vector<SumNode*> canonical_nodes_;
};

unique_ptr<EvalNodeArena> create_eval_node_arena();

template <typename T>
T* EvalNodeArena::NewNodeWithCapacity(uint8_t capacity) {
  num_nodes_++;
  // Size calculation for flexible array member of Pointers (8 bytes)
  int size = sizeof(T) + capacity * sizeof(void*);
  size = (size + 7) & ~7; // Align 8

  if (blocks_.empty() || current_offset_ + size > BLOCK_SIZE) {
      blocks_.push_back(new char[BLOCK_SIZE]);
      current_offset_ = 0;
  }

  char* buf = blocks_.back() + current_offset_;
  T* n = new (buf) T; // Placement new (trivial ctor)
  current_offset_ += size;
  bytes_allocated_ += size;
  return n;
}

#endif