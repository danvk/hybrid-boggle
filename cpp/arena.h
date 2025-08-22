#ifndef ARENA_H
#define ARENA_H

#include <limits.h>

#include <cassert>
#include <iostream>
#include <map>
#include <memory>
#include <unordered_map>
#include <unordered_set>
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

  struct SumNodePtrHash {
    size_t operator()(const SumNode* node) const;
  };
  struct SumNodePtrEqual {
    bool operator()(const SumNode* a, const SumNode* b) const;
  };
  struct ChoiceNodePtrHash {
    size_t operator()(const ChoiceNode* node) const;
  };
  struct ChoiceNodePtrEqual {
    bool operator()(const ChoiceNode* a, const ChoiceNode* b) const;
  };
  unordered_set<SumNode*, SumNodePtrHash, SumNodePtrEqual> sum_cache_;
  unordered_set<ChoiceNode*, ChoiceNodePtrHash, ChoiceNodePtrEqual> choice_cache_;

  SumNode* CanonicalizeSumNode(SumNode* n);
  ChoiceNode* CanonicalizeChoiceNode(ChoiceNode* n);

  void SizeCaches(size_t cache_size);

  // Statistics accessors
  void ResetStats() { sum_hit_ = sum_miss_ = choice_hit_ = choice_miss_ = 0; }
  void ClearCaches() { sum_cache_.clear(); choice_cache_.clear(); }
  void PrintCacheStats() {
    cout << "sum_cache.size() = " << sum_cache_.size() << " hit=" << sum_hit_
         << " miss=" << sum_miss_ << endl;
    cout << "choice_cache.size() = " << choice_cache_.size() << " hit=" << choice_hit_
         << " miss=" << choice_miss_ << endl;
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
  int sum_hit_;
  int sum_miss_;
  int choice_hit_;
  int choice_miss_;
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
