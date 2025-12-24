#include "arena.h"
#include "eval_node.h"

EvalNodeArena::EvalNodeArena() : current_offset_(0), num_nodes_(0), bytes_allocated_(0) {
  canonical_nodes_.resize(NUM_INTERNED);
  for (int i = 0; i < NUM_INTERNED; i++) {
    canonical_nodes_[i] = NewSumNodeWithCapacity(0);
    canonical_nodes_[i]->points_ = i + 1;
    canonical_nodes_[i]->bound_ = i + 1;
  }
}

EvalNodeArena::~EvalNodeArena() {
  for (char* block : blocks_) {
    delete[] block;
  }
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

EvalNodeArena::State EvalNodeArena::SaveLevel() {
    return {blocks_.size() > 0 ? blocks_.size() - 1 : 0, current_offset_};
}

void EvalNodeArena::ResetLevel(State state) {
    // This is a simplified reset. It doesn't free blocks, just resets pointer.
    // Ideally we would delete blocks > state.block_idx.
    // For this problem, it's sufficient.
    // If we added blocks, we could remove them.
    if (blocks_.size() > state.block_idx + 1) {
        // Free extra blocks
        for (size_t i = state.block_idx + 1; i < blocks_.size(); ++i) {
            delete[] blocks_[i];
        }
        blocks_.resize(state.block_idx + 1);
    }
    current_offset_ = state.offset;
}

void EvalNodeArena::PrintStats() {
  cout << "Nodes: " << num_nodes_ << " Bytes: " << bytes_allocated_ << endl;
}

unique_ptr<EvalNodeArena> create_eval_node_arena() {
  return unique_ptr<EvalNodeArena>(new EvalNodeArena);
}