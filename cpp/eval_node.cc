#include "eval_node.h"
#include "constants.h"
#include <bit>
#include <cstring>
#include <algorithm>

using namespace std;

void SumNode::CopyFrom(SumNode& other) {
  points_ = other.points_;
  bound_ = other.bound_;
}

void ChoiceNode::CopyFrom(ChoiceNode& other) {
  bound_ = other.bound_;
  child_letters_ = other.child_letters_;
}

SumNode* ChoiceNode::GetChildForLetter(int letter) const {
  if (!(child_letters_ & (1 << letter))) return nullptr;
  uint32_t mask = (1 << letter) - 1;
  int index = std::popcount(child_letters_ & mask);
  return children_[index];
}

vector<ChoiceNode*> SumNode::GetChildren() {
  vector<ChoiceNode*> out;
  int n = NumChildren();
  out.reserve(n);
  for(int i=0; i<n; ++i) out.push_back(children_[i]);
  return out;
}

vector<SumNode*> ChoiceNode::GetChildren() {
  vector<SumNode*> out;
  int n = NumChildren();
  out.reserve(n);
  for(int i=0; i<n; ++i) out.push_back(children_[i]);
  return out;
}

map<int, ChoiceNode*> SumNode::GetChildrenMap() {
  map<int, ChoiceNode*> out;
  uint32_t remaining = child_cells_;
  int i = 0;
  while(remaining) {
      int cell = std::countr_zero(remaining);
      out[cell] = children_[i++];
      remaining &= remaining - 1;
  }
  return out;
}

// ... Printing omitted for brevity, logic is same but pointers ...
void SumNode::PrintJSON(int cell, int letter) const { /* ... */ }
void ChoiceNode::PrintJSON(int cell) const { /* ... */ }

int SumNode::NodeCount() const {
    int c = 1;
    int n = NumChildren();
    for(int i=0; i<n; ++i) c += children_[i]->NodeCount();
    return c;
}
int ChoiceNode::NodeCount() const {
    int c = 1;
    int n = NumChildren();
    for(int i=0; i<n; ++i) c += children_[i]->NodeCount();
    return c;
}
int SumNode::WordCount() const {
    int c = (points_ > 0);
    int n = NumChildren();
    for(int i=0; i<n; ++i) c += children_[i]->WordCount();
    return c;
}
int ChoiceNode::WordCount() const {
    int c = 0;
    int n = NumChildren();
    for(int i=0; i<n; ++i) c += children_[i]->WordCount();
    return c;
}

unsigned int SumNode::ScoreWithForces(const vector<int>& forces) const {
    unsigned int s = points_;
    uint32_t remaining = child_cells_;
    int i = 0;
    while(remaining) {
        int cell = std::countr_zero(remaining);
        s += children_[i++]->ScoreWithForces(cell, forces);
        remaining &= remaining - 1;
    }
    return s;
}

unsigned int ChoiceNode::ScoreWithForces(int cell, const vector<int>& forces) const {
    auto force = forces[cell];
    if (force >= 0) {
        auto child = GetChildForLetter(force);
        return child ? child->ScoreWithForces(forces) : 0;
    }
    unsigned int s = 0;
    int n = NumChildren();
    for(int i=0; i<n; ++i) s = max(s, children_[i]->ScoreWithForces(forces));
    return s;
}

// Batch Advance
constexpr int BATCH_SIZE = 8;

inline uint16_t AdvanceBatch(
    const SumNode* const* nodes,
    int count,
    int* sums,
    const ChoiceNode* stacks[MAX_CELLS][MAX_STACK_DEPTH],
    int stack_sizes[MAX_CELLS]
) {
    uint16_t total_points = 0;
    int child_indices[BATCH_SIZE] = {0};
    
    uint32_t union_mask = 0;
    for(int k=0; k<count; ++k) {
        union_mask |= nodes[k]->child_cells_;
        total_points += nodes[k]->points_;
    }
    
    while(union_mask) {
        int cell = std::countr_zero(union_mask);
        auto& target_stack = const_cast<const ChoiceNode**>(stacks[cell]);
        int& sz = stack_sizes[cell];
        int cell_sum = 0;
        
        for(int k=0; k<count; ++k) {
            if ((nodes[k]->child_cells_ >> cell) & 1) {
                auto child = nodes[k]->children_[child_indices[k]++];
                target_stack[sz++] = child;
                cell_sum += child->bound_;
            }
        }
        sums[cell] += cell_sum;
        union_mask &= union_mask - 1;
    }
    return total_points;
}

inline uint16_t advance(
    const SumNode* node,
    int* sums,
    const ChoiceNode* stacks[MAX_CELLS][MAX_STACK_DEPTH],
    int stack_sizes[MAX_CELLS]
) {
    // Single node fallback
    const SumNode* nodes[1] = {node};
    return AdvanceBatch(nodes, 1, sums, stacks, stack_sizes);
}

vector<pair<int, string>> SumNode::OrderlyBound(
    int cutoff,
    const vector<string>& cells,
    const vector<int>& split_order,
    const vector<pair<int, int>>& preset_cells
) const {
  const ChoiceNode* stacks[MAX_CELLS][MAX_STACK_DEPTH];
  int stack_sizes[MAX_CELLS] = {0};
  vector<pair<int, int>> choices;
  vector<pair<int, string>> failures;

  auto record_failure = [&](int bound) {
    string board(cells.size(), '.');
    for (const auto& choice : preset_cells) board[choice.first] = cells[choice.first][choice.second];
    for (const auto& choice : choices) board[choice.first] = cells[choice.first][choice.second];
    failures.push_back({bound, board});
  };

  auto rec = [&](auto&& self, int base_points, int num_splits, int* stack_sums) -> void {
        int bound = base_points;
        for (int i = num_splits; i < split_order.size(); ++i) {
          bound += stack_sums[split_order[i]];
        }
        if (bound < cutoff) return;
        if (num_splits == split_order.size()) {
          record_failure(bound);
          return;
        }

        int next_to_split = split_order[num_splits];
        int base_stack_sizes[MAX_CELLS];
        memcpy(base_stack_sizes, stack_sizes, sizeof(base_stack_sizes));
        int base_sums[MAX_CELLS];
        memcpy(base_sums, stack_sums, sizeof(base_sums));

        auto& next_stack = stacks[next_to_split];
        int num_letters = cells[next_to_split].size();
        
        for (int letter = 0; letter < num_letters; ++letter) {
          if (letter > 0) {
            memcpy(stack_sums, base_sums, sizeof(base_sums));
            memcpy(stack_sizes, base_stack_sizes, sizeof(base_stack_sizes));
          }
          choices.emplace_back(next_to_split, letter);
          int points = base_points;
          
          // Batch process stack
          int stack_size = stack_sizes[next_to_split];
          for(int i=0; i<stack_size; i+=BATCH_SIZE) {
              int n = min(BATCH_SIZE, stack_size - i);
              const SumNode* sums_batch[BATCH_SIZE];
              int sums_count = 0;
              for(int k=0; k<n; ++k) {
                  auto choice_node = next_stack[i+k];
                  auto child = choice_node->GetChildForLetter(letter);
                  if (child) sums_batch[sums_count++] = child;
              }
              if (sums_count > 0) {
                  points += AdvanceBatch(sums_batch, sums_count, stack_sums, stacks, stack_sizes);
              }
          }
          
          self(self, points, num_splits + 1, stack_sums);
          choices.pop_back();
        }
      };

  int sums[MAX_CELLS] = {0};
  auto base_points = advance(this, sums, stacks, stack_sizes);
  rec(rec, base_points, 0, sums);
  return failures;
}

// Recursive Merge Functions (Pointer-based)

SumNode* merge_orderly_tree(const SumNode* a, const SumNode* b, EvalNodeArena& arena);
SumNode* merge_orderly_tree_children(const SumNode* a, uint32_t b_child_cells, ChoiceNode* const* bc, int b_points, EvalNodeArena& arena);
ChoiceNode* merge_orderly_choice_children(int cell, const ChoiceNode* a, const ChoiceNode* b, EvalNodeArena& arena);

ChoiceNode* merge_orderly_choice_children(int cell, const ChoiceNode* a, const ChoiceNode* b, EvalNodeArena& arena) {
    uint32_t merged_letters = a->ChildLetters() | b->ChildLetters();
    int num = std::popcount(merged_letters);
    auto n = arena.NewChoiceNodeWithCapacity(num);
    n->bound_ = 0;
    n->child_letters_ = merged_letters;
    
    int out_i = 0;
    uint32_t rem = merged_letters;
    while(rem) {
        int letter = std::countr_zero(rem);
        auto a_child = a->GetChildForLetter(letter);
        auto b_child = b->GetChildForLetter(letter);
        SumNode* res = nullptr;
        if (a_child && b_child) res = merge_orderly_tree(a_child, b_child, arena);
        else if (a_child) res = a_child; // Shallow copy/share
        else if (b_child) res = b_child;
        
        n->children_[out_i++] = res;
        if (res) n->bound_ = max(n->bound_, res->Bound());
        rem &= rem - 1;
    }
    return n;
}

SumNode* merge_orderly_tree_children(const SumNode* a, uint32_t b_child_cells, ChoiceNode* const* bc, int b_points, EvalNodeArena& arena) {
    uint32_t merged = a->ChildCells() | b_child_cells;
    int num = std::popcount(merged);
    auto new_p = a->points_ + b_points;
    if (num == 0 && new_p <= NUM_INTERNED) return arena.GetCanonicalNode(new_p);
    
    auto n = arena.NewSumNodeWithCapacity(num);
    n->points_ = new_p;
    n->bound_ = new_p;
    n->child_cells_ = merged;
    
    int out_i = 0;
    int i_a = 0;
    int i_b = 0;
    uint32_t rem = merged;
    while(rem) {
        int cell = std::countr_zero(rem);
        bool in_a = (a->ChildCells() >> cell) & 1;
        bool in_b = (b_child_cells >> cell) & 1;
        ChoiceNode* res = nullptr;
        
        if (in_a && in_b) {
            res = merge_orderly_choice_children(cell, a->children_[i_a++], bc[i_b++], arena);
        } else if (in_a) {
            res = a->children_[i_a++];
        } else if (in_b) {
            res = bc[i_b++];
        }
        n->children_[out_i++] = res;
        if (res) n->bound_ += res->Bound();
        rem &= rem - 1;
    }
    return n;
}

SumNode* merge_orderly_tree(const SumNode* a, const SumNode* b, EvalNodeArena& arena) {
    return merge_orderly_tree_children(a, b->ChildCells(), b->children_, b->points_, arena);
}

vector<const SumNode*> SumNode::OrderlyForceCell(int cell, int num_lets, EvalNodeArena& arena) const {
    if (NumChildren() == 0) throw runtime_error("force empty");
    
    uint32_t non_cell_mask = child_cells_ & ~(1<<cell);
    ChoiceNode* non_cell_children[MAX_CELLS];
    int non_cnt = 0;
    const ChoiceNode* top = nullptr;
    
    int idx = 0;
    uint32_t rem = child_cells_;
    while(rem) {
        int c = std::countr_zero(rem);
        auto child = children_[idx++];
        if (c == cell) top = child;
        else non_cell_children[non_cnt++] = child;
        rem &= rem - 1;
    }
    
    if (!top) return vector<const SumNode*>(num_lets, this);
    
    vector<const SumNode*> out(num_lets, nullptr);
    rem = top->ChildLetters();
    while(rem) {
        int l = std::countr_zero(rem);
        if (l < num_lets) {
            auto child = top->GetChildForLetter(l);
            if (child) {
                out[l] = merge_orderly_tree_children(child, non_cell_mask, non_cell_children, points_, arena);
            }
        }
        rem &= rem - 1;
    }
    
    // Fill gaps
    if (top->NumChildren() < num_lets) {
        int other_bound = 0;
        for(int i=0; i<non_cnt; ++i) other_bound += non_cell_children[i]->Bound();
        if (other_bound > 0 || points_ > 0) {
            for(int k=0; k<num_lets; ++k) {
                if (!out[k]) {
                    auto n = arena.NewSumNodeWithCapacity(non_cnt);
                    n->points_ = points_;
                    n->bound_ = points_ + other_bound;
                    n->child_cells_ = non_cell_mask;
                    memcpy(n->children_, non_cell_children, non_cnt * sizeof(ChoiceNode*));
                    out[k] = n;
                }
            }
        }
    }
    return out;
}

void SumNode::SetBoundsForTesting() {
    bound_ = points_;
    int n = NumChildren();
    for(int i=0; i<n; ++i) {
        children_[i]->SetBoundsForTesting();
        bound_ += children_[i]->Bound();
    }
}
void ChoiceNode::SetBoundsForTesting() {
    bound_ = 0;
    int n = NumChildren();
    for(int i=0; i<n; ++i) {
        children_[i]->SetBoundsForTesting();
        bound_ = max(bound_, children_[i]->Bound());
    }
}