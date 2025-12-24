#include "eval_node.h"

#include <bit>
#include <cstring>
#include <functional>
#include <limits>
#include <new>
#include <span>
#include <variant>
#include <vector>

#include "constants.h"

using namespace std;

void SumNode::CopyFrom(SumNode& other) {
  points_ = other.points_;
  bound_ = other.bound_;
}

void ChoiceNode::CopyFrom(ChoiceNode& other) {
  bound_ = other.bound_;
  child_letters_ = other.child_letters_;
}

SumNode* ChoiceNode::GetChildForLetter(int letter, const char* base) const {
  assert(letter >= 0 && letter < 32);
  if (!(child_letters_ & (1 << letter))) {
    return nullptr;
  }
  uint32_t mask = (1 << letter) - 1;
  int index = std::popcount(child_letters_ & mask);
  if (children_[index] == 0) return nullptr;
  return (SumNode*)(base + children_[index]);
}

vector<ChoiceNode*> SumNode::GetChildren(const char* base) {
  vector<ChoiceNode*> out;
  int num_children = NumChildren();
  out.reserve(num_children);
  for (int i = 0; i < num_children; i++) {
    if (children_[i])
        out.push_back((ChoiceNode*)(base + children_[i]));
    else
        out.push_back(nullptr);
  }
  return out;
}

vector<SumNode*> ChoiceNode::GetChildren(const char* base) {
  vector<SumNode*> out;
  int n_children = NumChildren();
  out.reserve(n_children);
  for (int i = 0; i < n_children; i++) {
    if (children_[i])
        out.push_back((SumNode*)(base + children_[i]));
    else
        out.push_back(nullptr);
  }
  return out;
}

map<int, ChoiceNode*> SumNode::GetChildrenMap(const char* base) {
  map<int, ChoiceNode*> out;
  uint32_t remaining_mask = child_cells_;
  int i = 0;
  while (remaining_mask) {
    int cell = std::countr_zero(remaining_mask);
    if (children_[i])
        out[cell] = (ChoiceNode*)(base + children_[i]);
    else
        out[cell] = nullptr;
    i++;
    remaining_mask &= remaining_mask - 1;
  }
  return out;
}

void PrintJSONChildren(const SumNode& n, const char* base) {
  if (n.NumChildren() > 0) {
    cout << ", \"children\": [";
    uint32_t remaining_mask = n.ChildCells();
    int i = 0;
    bool has_commad = false;
    while (remaining_mask) {
      int cell = std::countr_zero(remaining_mask);
      const auto& c = *(ChoiceNode*)(base + n.children_[i++]);
      if (true) {
        if (!has_commad) {
          has_commad = true;
        } else {
          cout << ", ";
        }
        c.PrintJSON(cell, base);
      }
      remaining_mask &= remaining_mask - 1;
    }
    cout << "]";
  }
}

void PrintJSONChildren(const ChoiceNode& n, const char* base) {
  int n_children = n.NumChildren();
  if (n_children) {
    cout << ", \"children\": [";
    bool has_commad = false;
    uint32_t remaining_bits = n.ChildLetters();
    int i = 0;
    while (remaining_bits) {
      int letter = std::countr_zero(remaining_bits);
      const auto& c = *(SumNode*)(base + n.children_[i++]);
      if (true) {
        if (!has_commad) {
          has_commad = true;
        } else {
          cout << ", ";
        }
        c.PrintJSON(-1, letter, base);
      }
      remaining_bits &= remaining_bits - 1;
    }
    cout << "]";
  }
}

void SumNode::PrintJSON(int cell, int letter, const char* base) const {
  cout << "{\"type\": \"SUM\"";
  cout << ", \"bound\": " << Bound();
  if (points_) {
    cout << ", \"points\": " << (int)points_;
  }
  if (cell != -1) {
    cout << ", \"cell\": " << cell;
  }
  if (letter != -1) {
    cout << ", \"letter\": " << letter;
  }
  PrintJSONChildren(*this, base);
  cout << "}";
}

void ChoiceNode::PrintJSON(int cell, const char* base) const {
  cout << "{\"type\": \"CHOICE\", \"cell\": " << cell;
  cout << ", \"bound\": " << Bound();
  cout << ", \"child_letters\": " << ChildLetters();
  PrintJSONChildren(*this, base);
  cout << "}";
}

int SumNode::NodeCount(const char* base) const {
  int count = 1;
  int num = NumChildren();
  for (int i = 0; i < num; i++) {
    const auto& c = *(ChoiceNode*)(base + children_[i]);
    count += c.NodeCount(base);
  }
  return count;
}

int ChoiceNode::NodeCount(const char* base) const {
  int count = 1;
  int n_children = NumChildren();
  for (int i = 0; i < n_children; i++) {
    const auto& c = *(SumNode*)(base + children_[i]);
    count += c.NodeCount(base);
  }
  return count;
}

int SumNode::WordCount(const char* base) const {
  int count = (points_ > 0) ? 1 : 0;
  int num = NumChildren();
  for (int i = 0; i < num; i++) {
    const auto& c = *(ChoiceNode*)(base + children_[i]);
    count += c.WordCount(base);
  }
  return count;
}

int ChoiceNode::WordCount(const char* base) const {
  int count = 0;
  int n_children = NumChildren();
  for (int i = 0; i < n_children; i++) {
    const auto& c = *(SumNode*)(base + children_[i]);
    count += c.WordCount(base);
  }
  return count;
}

unsigned int SumNode::ScoreWithForces(const vector<int>& forces, const char* base) const {
  unsigned int score = points_;
  uint32_t remaining_mask = child_cells_;
  int i = 0;
  while (remaining_mask) {
    int cell = std::countr_zero(remaining_mask);
    const auto& child = *(ChoiceNode*)(base + children_[i++]);
    score += child.ScoreWithForces(cell, forces, base);
    remaining_mask &= remaining_mask - 1;
  }
  return score;
}

unsigned int ChoiceNode::ScoreWithForces(int cell, const vector<int>& forces, const char* base) const {
  auto force = forces[cell];
  if (force >= 0) {
    auto child = GetChildForLetter(force, base);
    if (child) {
      return child->ScoreWithForces(forces, base);
    }
    return 0;
  }

  unsigned int score = 0;
  int n_children = NumChildren();
  for (int i = 0; i < n_children; i++) {
    const auto& child = *(SumNode*)(base + children_[i]);
    score = std::max(score, child.ScoreWithForces(forces, base));
  }
  return score;
}

inline uint16_t advance(
    const SumNode* node,
    int* sums,
    const ChoiceNode* stacks[MAX_CELLS][MAX_STACK_DEPTH],
    int stack_sizes[MAX_CELLS],
    const char* base
) {
  uint32_t remaining_mask = node->ChildCells();
  int i = 0;
  while (remaining_mask) {
    int cell = std::countr_zero(remaining_mask);
    auto child = (ChoiceNode*)(base + node->children_[i++]);
    auto n = stack_sizes[cell]++;
    assert(n < MAX_STACK_DEPTH);
    stacks[cell][n] = child;
    sums[cell] += child->Bound();
    remaining_mask &= remaining_mask - 1;
  }
  return node->points_;
}

constexpr int BATCH_SIZE = 8;

inline uint16_t AdvanceBatch(
    const SumNode* const* nodes,
    int count,
    int* sums,
    const ChoiceNode* stacks[MAX_CELLS][MAX_STACK_DEPTH],
    int stack_sizes[MAX_CELLS],
    const char* base
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
                // Get child
                NodeRef idx = nodes[k]->children_[child_indices[k]++];
                auto child = (ChoiceNode*)(base + idx);
                
                target_stack[sz++] = child; // Assumes sz < MAX_STACK_DEPTH
                cell_sum += child->bound_;
            }
        }
        sums[cell] += cell_sum;
        
        union_mask &= union_mask - 1;
    }
    return total_points;
}

vector<pair<int, string>> SumNode::OrderlyBound(
    int cutoff,
    const vector<string>& cells,
    const vector<int>& split_order,
    const vector<pair<int, int>>& preset_cells,
    const char* base
) const {
  const ChoiceNode* stacks[MAX_CELLS][MAX_STACK_DEPTH];
  int stack_sizes[MAX_CELLS];
  for (int i = 0; i < MAX_CELLS; i++) {
    stack_sizes[i] = 0;
  }
  vector<pair<int, int>> choices;
  vector<pair<int, string>> failures;

  auto record_failure = [&](int bound) {
    string board(cells.size(), '.');
    for (const auto& choice : preset_cells) {
      board[choice.first] = cells[choice.first][choice.second];
    }
    for (const auto& choice : choices) {
      board[choice.first] = cells[choice.first][choice.second];
    }
    failures.push_back({bound, board});
  };

  auto rec = [&](auto&& self, int base_points, int num_splits, int* stack_sums) -> void {
        int bound = base_points;
        for (int i = num_splits; i < split_order.size(); ++i) {
          bound += stack_sums[split_order[i]];
        }
        if (bound < cutoff) {
          return;
        }
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
          
          // Batched processing of stack
          int stack_size = stack_sizes[next_to_split];
          
          for (int i = 0; i < stack_size; i += BATCH_SIZE) {
              int n = std::min(BATCH_SIZE, stack_size - i);
              const SumNode* sums_batch[BATCH_SIZE];
              int sums_count = 0;
              
              for(int k=0; k<n; ++k) {
                  auto choice_node = next_stack[i+k];
                  auto child = choice_node->GetChildForLetter(letter, base);
                  if (child) {
                      sums_batch[sums_count++] = child;
                  }
              }
              
              if (sums_count > 0) {
                  points += AdvanceBatch(sums_batch, sums_count, stack_sums, stacks, stack_sizes, base);
              }
          }
          
          self(self, points, num_splits + 1, stack_sums);
          choices.pop_back();
        }
      };

  int sums[MAX_CELLS];
  memset(sums, 0, sizeof(sums));
  auto base_points = advance(this, sums, stacks, stack_sizes, base);
  rec(rec, base_points, 0, sums);
  return failures;
}

SumNode* merge_orderly_tree(const SumNode* a, const SumNode* b, EvalNodeArena& arena);
SumNode* merge_orderly_tree_children(
    const SumNode* a,
    uint32_t b_child_cells,
    ChoiceNode* const* bc,
    int num_bc,
    int b_points,
    EvalNodeArena& arena
);
ChoiceNode* merge_orderly_choice_children(
    int cell, const ChoiceNode* a, const ChoiceNode* b, EvalNodeArena& arena
);

ChoiceNode* merge_orderly_choice_children(
    int cell, const ChoiceNode* a, const ChoiceNode* b, EvalNodeArena& arena
) {
  const char* base = arena.Base();
  uint32_t merged_letters = a->ChildLetters() | b->ChildLetters();
  int num_children = std::popcount(merged_letters);

  auto n_ref = arena.NewChoiceNodeWithCapacity(num_children);
  auto n = arena.ToPtr<ChoiceNode>(n_ref);
  n->bound_ = 0;
  n->child_letters_ = merged_letters;

  int out_i = 0;
  uint32_t remaining_bits = merged_letters;
  while (remaining_bits) {
    int letter = std::countr_zero(remaining_bits);
    auto a_child = a->GetChildForLetter(letter, base);
    auto b_child = b->GetChildForLetter(letter, base);

    SumNode* result_child = nullptr;
    if (a_child && b_child) {
      result_child = merge_orderly_tree(a_child, b_child, arena);
    } else if (a_child) {
      result_child = const_cast<SumNode*>(a_child);
    } else if (b_child) {
      result_child = const_cast<SumNode*>(b_child);
    }

    n->children_[out_i++] = arena.ToRef(result_child);
    if (result_child) {
      n->bound_ = max(n->bound_, result_child->Bound());
    }

    remaining_bits &= remaining_bits - 1;
  }
  return n;
}

SumNode* merge_orderly_tree_children(
    const SumNode* a,
    uint32_t b_child_cells,
    ChoiceNode* const* bc,
    int num_bc,
    int b_points,
    EvalNodeArena& arena
) {
  const char* base = arena.Base();
  uint32_t merged_child_cells = a->ChildCells() | b_child_cells;
  int num_children = std::popcount(merged_child_cells);

  auto new_points = a->points_ + b_points;
  if (num_children == 0 && new_points >= 1 && new_points <= NUM_INTERNED) {
    return arena.GetCanonicalNode(new_points);
  }

  auto n_ref = arena.NewSumNodeWithCapacity(num_children);
  auto n = arena.ToPtr<SumNode>(n_ref);
  n->points_ = new_points;
  n->bound_ = n->points_;
  n->child_cells_ = merged_child_cells;

  int out_i = 0;
  uint32_t remaining_bits = merged_child_cells;
  int i_a = 0;
  int i_b = 0;
  while (remaining_bits) {
    int cell = std::countr_zero(remaining_bits);
    bool in_a = (a->ChildCells() & (1 << cell));
    bool in_b = (b_child_cells & (1 << cell));
    ChoiceNode* merged = nullptr;
    if (in_a && in_b) {
      auto a_child = (ChoiceNode*)(base + a->children_[i_a++]);
      auto b_child = bc[i_b++];
      merged = merge_orderly_choice_children(cell, a_child, b_child, arena);
    } else if (in_a) {
      merged = (ChoiceNode*)(base + a->children_[i_a++]);
    } else if (in_b) {
      merged = bc[i_b++];
    }
    n->children_[out_i++] = arena.ToRef(merged);
    if (merged) {
      n->bound_ += merged->Bound();
    }
    remaining_bits &= remaining_bits - 1;
  }
  return n;
}

SumNode* merge_orderly_tree(const SumNode* a, const SumNode* b, EvalNodeArena& arena) {
  const char* base = arena.Base();
  int num_children = b->NumChildren();
  ChoiceNode* children[32]; 
  for(int i=0; i<num_children; ++i) {
      children[i] = (ChoiceNode*)(base + b->children_[i]);
  }
  return merge_orderly_tree_children(
      a, b->ChildCells(), children, num_children, b->points_, arena
  );
}

vector<const SumNode*> SumNode::OrderlyForceCell(
    int cell, int num_lets, EvalNodeArena& arena
) const {
  const char* base = arena.Base();
  if (NumChildren() == 0) {
    throw runtime_error("tried to force empty cell");
  }

  uint32_t non_cell_child_cells = child_cells_ & (~(1u << cell));
  ChoiceNode* non_cell_children[MAX_CELLS];
  int non_cell_children_count = 0;

  const ChoiceNode* top_choice = NULL;
  uint32_t remaining_mask = child_cells_;
  int child_idx = 0;
  while (remaining_mask) {
    int child_cell = std::countr_zero(remaining_mask);
    auto& child = *(ChoiceNode*)(base + children_[child_idx++]);
    if (child_cell == cell) {
      top_choice = &child;
    } else {
      non_cell_children[non_cell_children_count++] = &child;
    }
    remaining_mask &= remaining_mask - 1;
  }

  if (!top_choice) {
    vector<const SumNode*> out(num_lets, this);
    return out;
  }

  int non_cell_points = points_;
  vector<const SumNode*> out(num_lets, nullptr);
  uint32_t remaining_bits = top_choice->ChildLetters();
  while (remaining_bits) {
    int letter = std::countr_zero(remaining_bits);
    if (letter < num_lets) {
      auto child = top_choice->GetChildForLetter(letter, base);
      if (child) {
        out[letter] = merge_orderly_tree_children(
            child,
            non_cell_child_cells,
            non_cell_children,
            non_cell_children_count,
            non_cell_points,
            arena
        );
      }
    }
    remaining_bits &= remaining_bits - 1;
  }

  if (top_choice->NumChildren() < num_lets) {
    int other_bound = 0;
    for (int i = 0; i < non_cell_children_count; ++i) {
      auto c = non_cell_children[i];
      if (c) {
        other_bound += c->Bound();
      }
    }
    if (other_bound > 0 || non_cell_points > 0) {
      for (int k = 0; k < num_lets; ++k) {
        if (!out[k]) {
          auto point_node_ref = arena.NewSumNodeWithCapacity(non_cell_children_count);
          auto point_node = arena.ToPtr<SumNode>(point_node_ref);
          point_node->points_ = non_cell_points;
          point_node->bound_ = non_cell_points + other_bound;
          point_node->child_cells_ = non_cell_child_cells;
          for(int i=0; i<non_cell_children_count; ++i) {
              point_node->children_[i] = arena.ToRef(non_cell_children[i]);
          }
          out[k] = point_node;
        }
      }
    }
  }
  return out;
}

void SumNode::SetBoundsForTesting(const char* base) {
  bound_ = points_;
  int num = NumChildren();
  for (int i = 0; i < num; i++) {
    auto& c = *(ChoiceNode*)(base + children_[i]);
    c.SetBoundsForTesting(base);
    bound_ += c.Bound();
  }
}

void ChoiceNode::SetBoundsForTesting(const char* base) {
  bound_ = 0;
  int num = NumChildren();
  for (int i = 0; i < num; i++) {
    auto& c = *(SumNode*)(base + children_[i]);
    c.SetBoundsForTesting(base);
    bound_ = max(bound_, c.Bound());
  }
}
