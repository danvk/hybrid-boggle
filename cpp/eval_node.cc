#include "eval_node.h"

#include <bit>
#include <cstring>
#include <functional>
#include <limits>
#include <new>
#include <variant>
#include <vector>

#include "constants.h"

using namespace std;

// Children are now ordered by letter index implicitly via child_letters_ bitmask

inline bool SortByCell(const ChoiceNode* a, const ChoiceNode* b) {
  return a->cell_ < b->cell_;
}

void SumNode::CopyFrom(SumNode& other) {
  points_ = other.points_;
  bound_ = other.bound_;
}

void ChoiceNode::CopyFrom(ChoiceNode& other) {
  cell_ = other.cell_;
  bound_ = other.bound_;
  child_letters_ = other.child_letters_;
}

SumNode* SumNode::AddChild(ChoiceNode* child, EvalNodeArena& arena) {
  if (num_children_ + 1 <= capacity_) {
    children_[num_children_++] = child;
    return this;
  }
  SumNode* clone = arena.NewNodeWithCapacity<SumNode>(capacity_ + 2);
  clone->CopyFrom(*this);
  clone->num_children_ = num_children_ + 1;
  memcpy(&clone->children_[0], &children_[0], num_children_ * sizeof(children_[0]));
  clone->children_[num_children_] = child;
  return clone;
}

ChoiceNode* ChoiceNode::AddChild(SumNode* child, int letter, EvalNodeArena& arena) {
  assert(letter >= 0 && letter < 26);  // Ensure letter fits in 26-bit field
  uint32_t mask = (1 << letter) - 1;
  int insert_index = std::popcount(child_letters_ & mask);
  int old_num_children = NumChildren();

  if (old_num_children + 1 <= capacity_) {
    memmove(
        &children_[insert_index + 1],
        &children_[insert_index],
        (old_num_children - insert_index) * sizeof(children_[0])
    );
    children_[insert_index] = child;
    child_letters_ |= (1 << letter);
    return this;
  }

  assert(capacity_ + 2 < 64);  // Ensure capacity fits in 6-bit field
  auto new_node = arena.NewNodeWithCapacity<ChoiceNode>(capacity_ + 2);
  new_node->CopyFrom(*this);
  new_node->child_letters_ |= (1 << letter);

  memcpy(&new_node->children_[0], &children_[0], insert_index * sizeof(children_[0]));
  new_node->children_[insert_index] = child;
  memcpy(
      &new_node->children_[insert_index + 1],
      &children_[insert_index],
      (old_num_children - insert_index) * sizeof(children_[0])
  );

  return new_node;
}

SumNode* ChoiceNode::GetChildForLetter(int letter) const {
  assert(letter >= 0 && letter < 26);  // Ensure letter fits in 26-bit field
  if (!(child_letters_ & (1 << letter))) {
    return nullptr;
  }
  uint32_t mask = (1 << letter) - 1;
  int index = std::popcount(child_letters_ & mask);
  return children_[index];
}

SumNode* SumNode::AddWord(
    int choices[],
    unsigned int used_ordered,
    const int split_order[],
    EvalNodeArena& arena,
    SumNode** leaf
) {
  if (used_ordered == 0) {
    *leaf = this;
    return this;
  }

  // some choices values are uninitialized here, but we only access the ones that are
  // initialized based on the bitmap
  int order_index = std::countr_zero(used_ordered);
  int cell = split_order[order_index];
  int letter = choices[order_index];

  // remove the cell from used_ordered
  used_ordered &= used_ordered - 1;

  ChoiceNode* choice_child = NULL;
  for (int i = 0; i < num_children_; i++) {
    const auto& c = children_[i];
    if (c->cell_ == cell) {
      choice_child = c;
      break;
    }
  }
  SumNode* new_me = this;
  if (!choice_child) {
    choice_child = arena.NewChoiceNodeWithCapacity(1);
    choice_child->cell_ = cell;
    new_me = AddChild(choice_child, arena);
    sort(&new_me->children_[0], &new_me->children_[new_me->num_children_], SortByCell);
  }

  SumNode* letter_child = choice_child->GetChildForLetter(letter);
  if (!letter_child) {
    unsigned int num_choices = std::popcount(used_ordered);
    letter_child = arena.NewSumNodeWithCapacity(num_choices == 1 ? 0 : 1);
    auto new_choice_child = choice_child->AddChild(letter_child, letter, arena);
    if (new_choice_child != choice_child) {
      const auto& old_choice_child = choice_child;
      bool patched = false;
      for (int i = 0; i < new_me->num_children_; i++) {
        const auto& c = new_me->children_[i];
        if (c == old_choice_child) {
          // TODO: assign through reference
          new_me->children_[i] = new_choice_child;
          patched = true;
          break;
        }
      }
      assert(patched);  // TODO: remove
      choice_child = new_choice_child;
    }
  }
  auto new_letter_child =
      letter_child->AddWord(choices, used_ordered, split_order, arena, leaf);
  if (new_letter_child != letter_child) {
    const auto& old_letter_child = letter_child;
    bool patched = false;
    for (int i = 0; i < choice_child->NumChildren(); i++) {
      auto& c = choice_child->children_[i];
      if (c == old_letter_child) {
        // TODO: assign through reference
        choice_child->children_[i] = new_letter_child;
        patched = true;
        break;
      }
    }
    assert(patched);  // TODO: remove
    letter_child = new_letter_child;
  }

  return new_me;
}

vector<ChoiceNode*> SumNode::GetChildren() {
  vector<ChoiceNode*> out;
  out.reserve(num_children_);
  for (int i = 0; i < num_children_; i++) {
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

void PrintJSONChildren(const SumNode& n) {
  if (n.num_children_) {
    cout << ", \"children\": [";
    bool has_commad = false;
    for (int i = 0; i < n.num_children_; i++) {
      const auto& c = n.children_[i];
      if (!c) {
        continue;
      }
      if (!has_commad) {
        has_commad = true;
      } else {
        cout << ", ";
      }
      c->PrintJSON();
    }
    cout << "]";
  }
}

void PrintJSONChildren(const ChoiceNode& n) {
  int n_children = n.NumChildren();
  if (n_children) {
    cout << ", \"children\": [";
    bool has_commad = false;
    for (int i = 0; i < n_children; i++) {
      const auto& c = n.children_[i];
      if (!c) {
        continue;
      }
      if (!has_commad) {
        has_commad = true;
      } else {
        cout << ", ";
      }
      c->PrintJSON();
    }
    cout << "]";
  }
}

void SumNode::PrintJSON() const {
  cout << "{\"type\": \"SUM\"";
  cout << ", \"bound\": " << bound_;
  if (points_) {
    cout << ", \"points\": " << (int)points_;
  }
  PrintJSONChildren(*this);
  cout << "}";
}

void ChoiceNode::PrintJSON() const {
  cout << "{\"type\": \"CHOICE\", \"cell\": " << (int)cell_;
  cout << ", \"bound\": " << bound_;
  cout << ", \"child_letters\": " << child_letters_;
  PrintJSONChildren(*this);
  cout << "}";
}

int SumNode::NodeCount() const {
  int count = 1;
  for (int i = 0; i < num_children_; i++) {
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
  if (num_children_ == 0) {
    return 1;
  }
  int count = 0;
  for (int i = 0; i < num_children_; i++) {
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
  for (int i = 0; i < num_children_; i++) {
    const auto& child = children_[i];
    if (child) {
      score += child->ScoreWithForces(forces);
    }
  }
  return score;
}

unsigned int ChoiceNode::ScoreWithForces(const vector<int>& forces) const {
  // If this cell is forced, apply the force.
  auto force = forces[cell_];
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

// block-scope functions cannot be declared inline.
inline uint16_t advance(
    const SumNode* node,
    vector<int>& sums,
    const ChoiceNode* stacks[MAX_CELLS][MAX_STACK_DEPTH],
    int stack_sizes[MAX_CELLS]
) {
  for (int i = 0; i < node->num_children_; i++) {
    auto child = node->children_[i];
    stacks[child->cell_][stack_sizes[child->cell_]++] = child;
    sums[child->cell_] += child->bound_;
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

  function<void(int, int, vector<int>&)> rec =
      [&](int base_points, int num_splits, vector<int>& stack_sums) {
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
        for (int i = 0; i < MAX_CELLS; i++) {
          base_stack_sizes[i] = stack_sizes[i];
        }
        vector<int> base_sums = stack_sums;

        auto& next_stack = stacks[next_to_split];

        int num_letters = cells[next_to_split].size();
        for (int letter = 0; letter < num_letters; ++letter) {
          if (letter > 0) {
            // TODO: it should be possible to avoid this copy with another stack.
            stack_sums = base_sums;
            for (int i = 0; i < MAX_CELLS; i++) {
              stack_sizes[i] = base_stack_sizes[i];
            }
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
          rec(points, num_splits + 1, stack_sums);
          choices.pop_back();
        }
      };

  vector<int> sums(cells.size(), 0);
  auto base_points = advance(this, sums, stacks, stack_sizes);
  rec(base_points, 0, sums);
  return failures;
}

SumNode* merge_orderly_tree(const SumNode* a, const SumNode* b, EvalNodeArena& arena);
SumNode* merge_orderly_tree_children(
    const SumNode* a,
    ChoiceNode* const* bc,
    int num_bc,
    int b_points,
    EvalNodeArena& arena
);
ChoiceNode* merge_orderly_choice_children(
    const ChoiceNode* a, const ChoiceNode* b, EvalNodeArena& arena
);

ChoiceNode* merge_orderly_choice_children(
    const ChoiceNode* a, const ChoiceNode* b, EvalNodeArena& arena
) {
  assert(a->cell_ == b->cell_);

  uint32_t merged_letters = a->child_letters_ | b->child_letters_;
  int num_children = std::popcount(merged_letters);

  auto n = arena.NewChoiceNodeWithCapacity(num_children);
  n->cell_ = a->cell_;
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
      n->bound_ = max(n->bound_, result_child->bound_);
    }

    remaining_bits &= remaining_bits - 1;
  }
  assert(out_i == num_children);

  return n;
}

SumNode* merge_orderly_tree_children(
    const SumNode* a,
    ChoiceNode* const* bc,
    int num_bc,
    int b_points,
    EvalNodeArena& arena
) {
  int num_children = 0;
  auto it_a = &a->children_[0];
  auto it_b = bc;
  const auto& a_end = it_a + a->num_children_;
  const auto& b_end = it_b + num_bc;
  while (it_a != a_end && it_b != b_end) {
    const auto& a_child = *it_a;
    const auto& b_child = *it_b;
    if (a_child->cell_ < b_child->cell_) {
      num_children += 1;
      ++it_a;
    } else if (b_child->cell_ < a_child->cell_) {
      num_children += 1;
      ++it_b;
    } else {
      num_children += 1;
      ++it_a;
      ++it_b;
    }
  }
  num_children += (a_end - it_a) + (b_end - it_b);

  auto n = arena.NewSumNodeWithCapacity(num_children);
  n->points_ = a->points_ + b_points;
  n->bound_ = n->points_;

  it_a = &a->children_[0];
  it_b = bc;
  int out_i = 0;

  while (it_a != a_end && it_b != b_end) {
    const auto& a_child = *it_a;
    const auto& b_child = *it_b;
    if (a_child->cell_ < b_child->cell_) {
      n->children_[out_i++] = a_child;
      if (a_child) {
        n->bound_ += a_child->bound_;
      }
      ++it_a;
    } else if (b_child->cell_ < a_child->cell_) {
      n->children_[out_i++] = b_child;
      if (b_child) {
        n->bound_ += b_child->bound_;
      }
      ++it_b;
    } else {
      auto merged = merge_orderly_choice_children(a_child, b_child, arena);
      n->children_[out_i++] = merged;
      n->bound_ += merged->bound_;
      ++it_a;
      ++it_b;
    }
  }

  while (it_a != a_end) {
    const auto& a_child = *it_a;
    n->children_[out_i++] = a_child;
    if (a_child) {
      n->bound_ += a_child->bound_;
    }
    ++it_a;
  }
  while (it_b != b_end) {
    const auto& b_child = *it_b;
    n->children_[out_i++] = b_child;
    if (b_child) {
      n->bound_ += b_child->bound_;
    }
    ++it_b;
  }
  assert(out_i == num_children);
  n->num_children_ = num_children;

  return n;
}

SumNode* merge_orderly_tree(const SumNode* a, const SumNode* b, EvalNodeArena& arena) {
  return merge_orderly_tree_children(
      a, &b->children_[0], b->num_children_, b->points_, arena
  );
}

void SumNode::SetChildrenFromVector(const vector<ChoiceNode*>& children) {
  num_children_ = children.size();
  memcpy(&children_[0], &children[0], num_children_ * sizeof(ChoiceNode*));
}

vector<const SumNode*> SumNode::OrderlyForceCell(
    int cell, int num_lets, EvalNodeArena& arena
) const {
  if (!num_children_) {
    throw runtime_error("tried to force empty cell");
    return {this};
  }

  vector<ChoiceNode*> non_cell_children;
  non_cell_children.reserve(num_children_ - 1);
  const ChoiceNode* top_choice = NULL;
  for (int i = 0; i < num_children_; i++) {
    auto& child = children_[i];
    if (child->cell_ == cell) {
      top_choice = child;
    } else {
      non_cell_children.push_back(child);
    }
  }

  if (!top_choice) {
    // This means that there are zero words going through the next cell, so it's
    // completely irrelevant to the bound. It's exceptionally rare that this would
    // happen on a high-scoring board class. Returning N copies of ourselves is not
    // the most efficient way to deal with this, but it's expedient.
    vector<const SumNode*> out(num_lets, this);
    return out;
  }

  int non_cell_points = points_;

  vector<const SumNode*> out(num_lets, nullptr);
  uint32_t remaining_bits = top_choice->child_letters_;
  while (remaining_bits) {
    int letter = std::countr_zero(remaining_bits);
    if (letter < num_lets) {
      auto child = top_choice->GetChildForLetter(letter);
      if (child) {
        out[letter] = merge_orderly_tree_children(
            child,
            &non_cell_children[0],
            non_cell_children.size(),
            non_cell_points,
            arena
        );
      }
    }
    remaining_bits &= remaining_bits - 1;
  }

  if (top_choice->NumChildren() < num_lets) {
    int other_bound = 0;
    for (auto c : non_cell_children) {
      if (c) {
        other_bound += c->bound_;
      }
    }
    if (other_bound > 0 || non_cell_points > 0) {
      for (int i = 0; i < num_lets; ++i) {
        if (!out[i]) {
          auto point_node = arena.NewSumNodeWithCapacity(non_cell_children.size());
          point_node->points_ = non_cell_points;
          point_node->bound_ = non_cell_points + other_bound;
          point_node->SetChildrenFromVector(non_cell_children);
          out[i] = point_node;
        }
      }
    }
  }
  return out;
}

static const uint32_t FRESH_MASK = 1 << 23;

// See orderly_tree_builder.h for an explanation of the encoding.
void SumNode::DecodePointsAndBound(vector<vector<uint32_t>>& wordlists) {
  if (bound_) {
    // A word was found on this node; decode the points.
    int count;
    if (bound_ & FRESH_MASK) {
      // just one word stored inline
      count = 1;
    } else {
      auto slot = bound_;
      auto& wordlist = wordlists[slot];
      count = wordlist.size();
    }
    auto word_score = points_;
    points_ = bound_ = word_score * count;
  } else {
    bound_ = points_;
  }

  for (int i = 0; i < num_children_; i++) {
    auto& child = children_[i];
    child->DecodePointsAndBound(wordlists);
    bound_ += child->bound_;
  }
}

void ChoiceNode::DecodePointsAndBound(vector<vector<uint32_t>>& wordlists) {
  uint32_t bound = 0;
  int n_children = NumChildren();
  for (int i = 0; i < n_children; i++) {
    auto& child = children_[i];
    child->DecodePointsAndBound(wordlists);
    bound = max(bound, child->bound_);
  }
  bound_ = bound;
}

void SumNode::AddWordWithPointsForTesting(
    vector<int> choices,
    unsigned int used_ordered,
    vector<int> split_order,
    int points,
    EvalNodeArena& arena
) {
  SumNode* node;
  auto r = AddWord(choices.data(), used_ordered, split_order.data(), arena, &node);
  assert(r == this);
  node->points_ += points;
}
