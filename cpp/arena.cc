#include "arena.h"

#include "eval_node.h"

// Hash and equality functors implementations
size_t EvalNodeArena::SumNodePtrHash::operator()(const SumNode* node) const {
  return node->Hash();
}

bool EvalNodeArena::SumNodePtrEqual::operator()(const SumNode* a, const SumNode* b)
    const {
  return a->IsEqual(*b);
}

size_t EvalNodeArena::ChoiceNodePtrHash::operator()(const ChoiceNode* node) const {
  return node->Hash();
}

bool EvalNodeArena::ChoiceNodePtrEqual::operator()(
    const ChoiceNode* a, const ChoiceNode* b
) const {
  return a->IsEqual(*b);
}

EvalNodeArena::EvalNodeArena()
    : num_nodes_(0),
      cur_buffer_(-1),
      tip_(EVAL_NODE_ARENA_BUFFER_SIZE),
      saved_levels_(),
      level_caches_(1),  // Start with one level
      sum_cache_(level_caches_[0].first),
      choice_cache_(level_caches_[0].second) {
  canonical_nodes_.resize(NUM_INTERNED);
  for (int i = 0; i < NUM_INTERNED; i++) {
    canonical_nodes_[i] = NewSumNodeWithCapacity(0);
    canonical_nodes_[i]->points_ = i + 1;
    canonical_nodes_[i]->bound_ = i + 1;
  }
}

EvalNodeArena::~EvalNodeArena() {
  for (auto buffer : buffers_) {
    delete[] buffer;
  }
  buffers_.clear();
}

void EvalNodeArena::PrintStats() {
  cout << "num_buffers: " << buffers_.size() << endl;
  cout << "tip: " << tip_ << endl;
}

unique_ptr<EvalNodeArena> create_eval_node_arena() {
  return unique_ptr<EvalNodeArena>(new EvalNodeArena);
}

void EvalNodeArena::AddBuffer() {
  if (cur_buffer_ == buffers_.size() - 1) {
    char* buf = new char[EVAL_NODE_ARENA_BUFFER_SIZE];
    buffers_.push_back(buf);
  }
  cur_buffer_++;
  tip_ = 0;
}

SumNode* EvalNodeArena::NewSumNodeWithCapacity(uint8_t capacity) {
  return NewNodeWithCapacity<SumNode>(capacity);
}

ChoiceNode* EvalNodeArena::NewChoiceNodeWithCapacity(uint8_t capacity) {
  return NewNodeWithCapacity<ChoiceNode>(capacity);
}

SumNode* EvalNodeArena::NewRootNodeWithCapacity(uint8_t capacity) {
  auto root = NewSumNodeWithCapacity(capacity);
  root->points_ = 0;
  root->bound_ = 0;
  return root;
}

int EvalNodeArena::SaveLevel() {
  int level = saved_levels_.size();
  saved_levels_.push_back({cur_buffer_, tip_});

  // Create a new cache level for this save point
  level_caches_.emplace_back();

  return level;
}

void EvalNodeArena::ResetLevel(int level) {
  assert(level >= 0 && level < saved_levels_.size());
  auto [new_cur_buffer, new_tip] = saved_levels_[level];
  assert(new_cur_buffer <= cur_buffer_);
  if (new_cur_buffer == cur_buffer_) {
    assert(new_tip <= tip_);
  }
  cur_buffer_ = new_cur_buffer;
  tip_ = new_tip;

  // Remove all levels above this one
  saved_levels_.resize(level);
  level_caches_.resize(level + 1);  // Keep level + 1 cache levels
}

SumNode* EvalNodeArena::CanonicalizeSumNode(SumNode* node, bool no_insert) {
  // Search all cache levels for an existing equivalent node
  for (auto cit = level_caches_.rbegin(); cit != level_caches_.rend(); ++cit) {
    auto& cache_pair = *cit;
    auto it = cache_pair.first.find(node);
    if (it != cache_pair.first.end()) {
      sum_hit_++;
      return *it;
    }
  }

  // Not found in any cache level
  sum_miss_++;
  auto new_node = NewSumNodeWithCapacity(node->num_children_);
  new_node->CopyFrom(node);
  if (!no_insert && !level_caches_.empty()) {
    // Insert into the current (last) cache level
    level_caches_.back().first.emplace(new_node);
  }
  return new_node;
}

ChoiceNode* EvalNodeArena::CanonicalizeChoiceNode(ChoiceNode* node, bool no_insert) {
  // Search all cache levels for an existing equivalent node
  for (auto cit = level_caches_.rbegin(); cit != level_caches_.rend(); ++cit) {
    auto& cache_pair = *cit;
    auto it = cache_pair.second.find(node);
    if (it != cache_pair.second.end()) {
      choice_hit_++;
      return *it;
    }
  }

  // Not found in any cache level
  choice_miss_++;
  auto new_node = NewChoiceNodeWithCapacity(node->NumChildren());
  new_node->CopyFrom(node);
  if (!no_insert && !level_caches_.empty()) {
    // Insert into the current (last) cache level
    level_caches_.back().second.emplace(new_node);
  }
  return new_node;
}

void EvalNodeArena::SizeCaches(size_t cache_size) {
  // Reserve space in all cache levels
  for (auto& cache_pair : level_caches_) {
    cache_pair.first.reserve(cache_size);
    cache_pair.second.reserve(cache_size);
  }
}
