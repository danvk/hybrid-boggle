#include "arena.h"

#include "eval_node.h"

void EvalNodeArena::PrintStats() {
  cout << "num_buffers: " << buffers_.size() << endl;
  cout << "tip: " << tip_ << endl;
}

unique_ptr<EvalNodeArena> create_eval_node_arena() {
  return unique_ptr<EvalNodeArena>(new EvalNodeArena);
}

void EvalNodeArena::AddBuffer() {
  char* buf = new char[EVAL_NODE_ARENA_BUFFER_SIZE];
  buffers_.push_back(buf);
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
