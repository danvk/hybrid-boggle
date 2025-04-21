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

#endif
