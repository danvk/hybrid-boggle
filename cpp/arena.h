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

  int SaveLevel();
  void ResetLevel(int level);

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

  // Note: sum_cache_ and choice_cache_ are now private member references

  SumNode* CanonicalizeSumNode(SumNode* n);
  ChoiceNode* CanonicalizeChoiceNode(ChoiceNode* n);

  void SizeCaches(size_t cache_size);

  // Cache accessors for compatibility
  size_t GetSumCacheSize() const {
    size_t total = 0;
    for (const auto& cache_pair : level_caches_) {
      total += cache_pair.first.size();
    }
    return total;
  }
  size_t GetChoiceCacheSize() const {
    size_t total = 0;
    for (const auto& cache_pair : level_caches_) {
      total += cache_pair.second.size();
    }
    return total;
  }

  // Statistics accessors
  void ResetStats() { sum_hit_ = sum_miss_ = choice_hit_ = choice_miss_ = 0; }
  void ClearCaches() {
    for (auto& cache_pair : level_caches_) {
      cache_pair.first.clear();
      cache_pair.second.clear();
    }
  }
  void PrintCacheStats() {
    cout << "sum_cache.size() = " << GetSumCacheSize() << " hit=" << sum_hit_
         << " miss=" << sum_miss_ << endl;
    cout << "choice_cache.size() = " << GetChoiceCacheSize() << " hit=" << choice_hit_
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
  vector<pair<int, int>> saved_levels_;  // Store buffer/tip pairs for each level
  // Multi-level caching - one cache pair per level
  using SumNodeCache = unordered_set<SumNode*, SumNodePtrHash, SumNodePtrEqual>;
  using ChoiceNodeCache =
      unordered_set<ChoiceNode*, ChoiceNodePtrHash, ChoiceNodePtrEqual>;
  vector<pair<SumNodeCache, ChoiceNodeCache>> level_caches_;
  // Legacy accessors for compatibility - these reference the first level cache
  unordered_set<SumNode*, SumNodePtrHash, SumNodePtrEqual>& sum_cache_;
  unordered_set<ChoiceNode*, ChoiceNodePtrHash, ChoiceNodePtrEqual>& choice_cache_;
  vector<SumNode*> canonical_nodes_;
  uint64_t sum_hit_;
  uint64_t sum_miss_;
  uint64_t choice_hit_;
  uint64_t choice_miss_;
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
