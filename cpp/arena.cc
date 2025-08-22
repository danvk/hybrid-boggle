#include "arena.h"

#include "eval_node.h"

EvalNodeArena::EvalNodeArena()
    : num_nodes_(0), cur_buffer_(-1), tip_(EVAL_NODE_ARENA_BUFFER_SIZE) {
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

pair<int, int> EvalNodeArena::SaveLevel() { return {cur_buffer_, tip_}; }

void EvalNodeArena::ResetLevel(pair<int, int> level) {
  auto [new_cur_buffer, new_tip] = level;
  assert(new_cur_buffer <= cur_buffer_);
  if (new_cur_buffer == cur_buffer_) {
    assert(new_tip <= tip_);
  }
  cur_buffer_ = new_cur_buffer;
  tip_ = new_tip;
}

SumNode* EvalNodeArena::CanonicalizeSumNode(SumNode* node) {
  auto it = sum_cache_.find(node);
  if (it != sum_cache_.end()) {
    sum_hit_++;
    return *it;
  }
  sum_miss_++;
  auto new_node = NewSumNodeWithCapacity(node->num_children_);
  new_node->CopyFrom(node);
  sum_cache_.emplace(new_node);
  return new_node;
}

ChoiceNode* EvalNodeArena::CanonicalizeChoiceNode(ChoiceNode* node) {
  auto it = choice_cache_.find(node);
  if (it != choice_cache_.end()) {
    choice_hit_++;
    return *it;
  }
  choice_miss_++;
  auto new_node = NewChoiceNodeWithCapacity(node->NumChildren());
  new_node->CopyFrom(node);
  choice_cache_.emplace(new_node);
  return new_node;
}

void EvalNodeArena::SizeCaches(size_t cache_size) {
  sum_cache_.reserve(cache_size);
  choice_cache_.reserve(cache_size);
}
