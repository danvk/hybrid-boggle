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

SumNode* ChoiceNode::GetChildForLetter(int letter) const {
  assert(letter >= 0 && letter < 32);
  if (!(child_letters_ & (1 << letter))) {
    return nullptr;
  }
  uint32_t mask = (1 << letter) - 1;
  int index = std::popcount(child_letters_ & mask);
  return children_[index];
}

vector<ChoiceNode*> SumNode::GetChildren() {
  vector<ChoiceNode*> out;
  int num_children = NumChildren();
  out.reserve(num_children);
  for (int i = 0; i < num_children; i++) {
    out.push_back(children_[i]);
  }
  return out;
}

vector<SumNode*> ChoiceNode::GetChildren() {
  vector<SumNode*> out;
  int n_children = NumChildren();
  out.reserve(n_children);
  for (int i = 0; i < n_children; i++) {
    out.push_back(children_[i]);
  }
  return out;
}

map<int, ChoiceNode*> SumNode::GetChildrenMap() {
  map<int, ChoiceNode*> out;
  uint32_t remaining_mask = child_cells_;
  int i = 0;
  while (remaining_mask) {
    int cell = std::countr_zero(remaining_mask);
    out[cell] = children_[i++];
    remaining_mask &= remaining_mask - 1;
  }
  return out;
}

void PrintJSONChildren(const SumNode& n) {
  if (n.NumChildren() > 0) {
    cout << ", \"children\": [";
    uint32_t remaining_mask = n.ChildCells();
    int i = 0;
    bool has_commad = false;
    while (remaining_mask) {
      int cell = std::countr_zero(remaining_mask);
      const auto& c = n.children_[i++];
      if (c) {
        if (!has_commad) {
          has_commad = true;
        } else {
          cout << ", ";
        }
        c->PrintJSON(cell);
      }
      remaining_mask &= remaining_mask - 1;
    }
    cout << "]";
  }
}

void PrintJSONChildren(const ChoiceNode& n) {
  int n_children = n.NumChildren();
  if (n_children) {
    cout << ", \"children\": [";
    bool has_commad = false;
    uint32_t remaining_bits = n.ChildLetters();
    int i = 0;
    while (remaining_bits) {
      int letter = std::countr_zero(remaining_bits);
      const auto& c = n.children_[i++];
      if (c) {
        if (!has_commad) {
          has_commad = true;
        } else {
          cout << ", ";
        }
        c->PrintJSON(-1, letter);
      }
      remaining_bits &= remaining_bits - 1;
    }
    cout << "]";
  }
}

void SumNode::PrintJSON(int cell, int letter) const {
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
  PrintJSONChildren(*this);
  cout << "}";
}

void ChoiceNode::PrintJSON(int cell) const {
  cout << "{\"type\": \"CHOICE\", \"cell\": " << cell;
  cout << ", \"bound\": " << Bound();
  cout << ", \"child_letters\": " << ChildLetters();
  PrintJSONChildren(*this);
  cout << "}";
}

int SumNode::NodeCount() const {
  int count = 1;
  for (int i = 0; i < NumChildren(); i++) {
    const auto& c = children_[i];
    if (c) count += c->NodeCount();
  }
  return count;
}

int ChoiceNode::NodeCount() const {
  int count = 1;
  int n_children = NumChildren();
  for (int i = 0; i < n_children; i++) {
    const auto& c = children_[i];
    if (c) count += c->NodeCount();
  }
  return count;
}

int SumNode::WordCount() const {
  int count = (points_ > 0) ? 1 : 0;
  for (int i = 0; i < NumChildren(); i++) {
    const auto& c = children_[i];
    if (c) count += c->WordCount();
  }
  return count;
}

int ChoiceNode::WordCount() const {
  int count = 0;
  int n_children = NumChildren();
  for (int i = 0; i < n_children; i++) {
    const auto& c = children_[i];
    if (c) count += c->WordCount();
  }
  return count;
}

unsigned int SumNode::ScoreWithForces(const vector<int>& forces) const {
  unsigned int score = points_;
  uint32_t remaining_mask = child_cells_;
  int i = 0;
  while (remaining_mask) {
    int cell = std::countr_zero(remaining_mask);
    const auto& child = children_[i++];
    if (child) {
      score += child->ScoreWithForces(cell, forces);
    }
    remaining_mask &= remaining_mask - 1;
  }
  return score;
}

unsigned int ChoiceNode::ScoreWithForces(int cell, const vector<int>& forces) const {
  // If this cell is forced, apply the force.
  auto force = forces[cell];
  if (force >= 0) {
    auto child = GetChildForLetter(force);
    if (child) {
      return child->ScoreWithForces(forces);
    }
    return 0;
  }

  // Otherwise, this is the same as regular scoring.
  unsigned int score = 0;
  int n_children = NumChildren();
  for (int i = 0; i < n_children; i++) {
    const auto& child = children_[i];
    if (child) {
      score = std::max(score, child->ScoreWithForces(forces));
    }
  }
  return score;
}

const SumNode* SumNode::SubtractTree(const SumNode* other, EvalNodeArena& arena) const {
  uint32_t remaining_self = child_cells_;
  uint32_t remaining_other = other->child_cells_;

  if ((remaining_other & ~remaining_self) != 0) {
    throw std::runtime_error("Other tree has child at cell which is missing in self");
  }

  int idx_self = 0;
  int idx_other = 0;

  vector<ChoiceNode*> new_children;
  uint32_t new_child_cells = 0;

  while (remaining_self) {
    int cell = std::countr_zero(remaining_self);
    auto child = children_[idx_self++];

    const ChoiceNode* new_child = nullptr;

    // Check if other has this cell. Since other is a subset, if it has any bits set,
    // the lowest bit must be >= cell.
    int other_cell = remaining_other ? std::countr_zero(remaining_other) : -1;

    if (other_cell == cell) {
      auto other_child = other->children_[idx_other++];
      new_child = child->SubtractTree(other_child, arena);
      remaining_other &= remaining_other - 1;
    } else {
      new_child = child;
    }

    if (new_child && new_child->Bound() > 0) {
      new_children.push_back(const_cast<ChoiceNode*>(new_child));
      new_child_cells |= (1u << cell);
    }

    remaining_self &= remaining_self - 1;
  }

  int new_points = (int)points_ - (int)other->points_;

  auto res = arena.NewSumNodeWithCapacity(new_children.size());
  res->points_ = new_points;
  res->child_cells_ = new_child_cells;

  uint32_t bound = new_points;
  for (size_t i = 0; i < new_children.size(); ++i) {
    res->children_[i] = new_children[i];
    bound += new_children[i]->Bound();
  }
  res->bound_ = bound;
  return res;
}

const ChoiceNode* ChoiceNode::SubtractTree(
    const ChoiceNode* other, EvalNodeArena& arena
) const {
  if ((other->child_letters_ & ~child_letters_) != 0) {
    throw std::runtime_error("Other tree has child letters not in self");
  }

  uint32_t remaining_self = child_letters_;
  // Since other is a subset mask, we can iterate just like SumNode
  uint32_t remaining_other = other->child_letters_;

  int idx_self = 0;
  int idx_other = 0;

  vector<SumNode*> new_children;
  uint32_t new_child_letters = 0;

  while (remaining_self) {
    int letter = std::countr_zero(remaining_self);
    auto child = children_[idx_self++];

    const SumNode* new_child = nullptr;
    int other_letter = remaining_other ? std::countr_zero(remaining_other) : -1;

    if (other_letter == letter) {
      auto other_child = other->children_[idx_other++];
      new_child = child->SubtractTree(other_child, arena);
      remaining_other &= remaining_other - 1;
    } else {
      new_child = child;
    }

    if (new_child && new_child->Bound() > 0) {
      new_children.push_back(const_cast<SumNode*>(new_child));
      new_child_letters |= (1u << letter);
    }

    remaining_self &= remaining_self - 1;
  }

  auto res = arena.NewChoiceNodeWithCapacity(new_children.size());
  res->child_letters_ = new_child_letters;

  uint32_t bound = 0;
  for (size_t i = 0; i < new_children.size(); ++i) {
    res->children_[i] = new_children[i];
    bound = std::max(bound, new_children[i]->Bound());
  }
  res->bound_ = bound;
  return res;
}

// block-scope functions cannot be declared inline.
inline uint16_t advance(
    const SumNode* node,
    int* sums,
    const ChoiceNode* stacks[MAX_CELLS][MAX_STACK_DEPTH],
    int stack_sizes[MAX_CELLS]
) {
  uint32_t remaining_mask = node->ChildCells();
  int i = 0;
  while (remaining_mask) {
    int cell = std::countr_zero(remaining_mask);
    auto child = node->children_[i++];
    auto n = stack_sizes[cell]++;
    assert(n < MAX_STACK_DEPTH);
    stacks[cell][n] = child;
    sums[cell] += child->Bound();
    remaining_mask &= remaining_mask - 1;
  }
  return node->points_;
}

vector<pair<int, string>> SumNode::OrderlyBound(
    int cutoff,
    const vector<string>& cells,
    const vector<int>& split_order,
    const vector<pair<int, int>>& preset_cells
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

  auto rec = [&](auto&& self, int base_points, int num_splits, int* stack_sums
             ) -> void {
    int bound = base_points;
    for (int i = num_splits; i < split_order.size(); ++i) {
      bound += stack_sums[split_order[i]];
    }
    if (bound < cutoff) {
      return;  // done!
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
        // Restore state
        memcpy(stack_sums, base_sums, sizeof(base_sums));
        memcpy(stack_sizes, base_stack_sizes, sizeof(base_stack_sizes));
      }
      choices.emplace_back(next_to_split, letter);
      int points = base_points;
      for (int i = 0; i < stack_sizes[next_to_split]; i++) {
        auto choice_node = next_stack[i];
        auto child = choice_node->GetChildForLetter(letter);
        if (child) {
          // visit_at_level[1 + num_splits] += 1;
          points += advance(child, stack_sums, stacks, stack_sizes);
        }
      }
      self(self, points, num_splits + 1, stack_sums);
      choices.pop_back();
    }
  };

  int sums[MAX_CELLS];
  memset(sums, 0, sizeof(sums));
  auto base_points = advance(this, sums, stacks, stack_sizes);
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
  uint32_t merged_letters = a->ChildLetters() | b->ChildLetters();
  int num_children = std::popcount(merged_letters);

  auto n = arena.NewChoiceNodeWithCapacity(num_children);
  n->bound_ = 0;
  n->child_letters_ = merged_letters;

  int out_i = 0;
  uint32_t remaining_bits = merged_letters;
  while (remaining_bits) {
    int letter = std::countr_zero(remaining_bits);
    auto a_child = a->GetChildForLetter(letter);
    auto b_child = b->GetChildForLetter(letter);

    SumNode* result_child = nullptr;
    if (a_child && b_child) {
      result_child = merge_orderly_tree(a_child, b_child, arena);
    } else if (a_child) {
      result_child = const_cast<SumNode*>(a_child);
    } else if (b_child) {
      result_child = const_cast<SumNode*>(b_child);
    }

    n->children_[out_i++] = result_child;
    if (result_child) {
      n->bound_ = max(n->bound_, result_child->Bound());
    }

    remaining_bits &= remaining_bits - 1;
  }
  assert(out_i == num_children);

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
  uint32_t merged_child_cells = a->ChildCells() | b_child_cells;
  int num_children = std::popcount(merged_child_cells);

  auto new_points = a->points_ + b_points;
  if (num_children == 0 && new_points >= 1 && new_points <= NUM_INTERNED) {
    return arena.GetCanonicalNode(new_points);
  }

  auto n = arena.NewSumNodeWithCapacity(num_children);
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
      merged =
          merge_orderly_choice_children(cell, a->children_[i_a++], bc[i_b++], arena);
    } else if (in_a) {
      merged = a->children_[i_a++];
    } else if (in_b) {
      merged = bc[i_b++];
    }
    n->children_[out_i++] = merged;
    if (merged) {
      n->bound_ += merged->Bound();
    }
    remaining_bits &= remaining_bits - 1;
  }
  assert(out_i == num_children);

  return n;
}

SumNode* merge_orderly_tree(const SumNode* a, const SumNode* b, EvalNodeArena& arena) {
  return merge_orderly_tree_children(
      a, b->ChildCells(), &b->children_[0], b->NumChildren(), b->points_, arena
  );
}

void SumNode::SetChildren(uint32_t child_cells, std::span<ChoiceNode* const> children) {
  child_cells_ = child_cells;
  int num_children = NumChildren();
  assert(children.size() == num_children);
  memcpy(&children_[0], children.data(), num_children * sizeof(ChoiceNode*));
}

vector<const SumNode*> SumNode::OrderlyForceCell(
    int cell, int num_lets, EvalNodeArena& arena
) const {
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
    auto& child = children_[child_idx++];
    if (child_cell == cell) {
      top_choice = child;
    } else {
      non_cell_children[non_cell_children_count++] = child;
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
      auto child = top_choice->GetChildForLetter(letter);
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
          auto point_node = arena.NewSumNodeWithCapacity(non_cell_children_count);
          point_node->points_ = non_cell_points;
          point_node->bound_ = non_cell_points + other_bound;
          vector<ChoiceNode*> tmp(
              non_cell_children, non_cell_children + non_cell_children_count
          );
          point_node->SetChildren(non_cell_child_cells, tmp);
          out[k] = point_node;
        }
      }
    }
  }

  return out;
}

void SumNode::SetBoundsForTesting() {
  bound_ = points_;
  for (int i = 0; i < NumChildren(); i++) {
    auto& c = children_[i];
    c->SetBoundsForTesting();
    bound_ += c->Bound();
  }
}

void ChoiceNode::SetBoundsForTesting() {
  bound_ = 0;
  auto children = GetChildren();
  for (auto& c : children) {
    c->SetBoundsForTesting();
    bound_ = max(bound_, c->Bound());
  }
}
