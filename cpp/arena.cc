#include "arena.h"

#include "eval_node.h"

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
  root->letter_ = SumNode::ROOT_NODE;  // irrelevant
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
