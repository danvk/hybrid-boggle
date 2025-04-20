#include "eval_node.h"

#include <bit>
#include <cstring>
#include <functional>
#include <limits>
#include <new>
#include <variant>
#include <vector>

using namespace std;

inline bool SortByLetter(const EvalNode* a, const EvalNode* b) {
  return a->letter_ < b->letter_;
}

inline bool SortByCell(const EvalNode* a, const EvalNode* b) {
  return a->cell_ < b->cell_;
}

int num_reallocs = 0;
int num_in_capacity = 0;

void EvalNodeArena::PrintStats() {
  cout << "num_reallocs: " << num_reallocs << endl;
  cout << "num_in_capacity: " << num_in_capacity << endl;
  cout << "num_buffers: " << buffers_.size() << endl;
  cout << "tip: " << tip_ << endl;
}

EvalNode* EvalNode::AddChild(EvalNode* child, EvalNodeArena& arena) {
  if (num_children_ + 1 <= capacity_) {
    children_[num_children_++] = child;
    num_in_capacity++;
    return this;
  }
  num_reallocs++;
  // cout << "Exceeded capacity!" << endl;
  EvalNode* clone = arena.NewNodeWithCapacity(capacity_ + 2);
  clone->letter_ = letter_;
  clone->cell_ = cell_;
  clone->points_ = points_;
  clone->bound_ = bound_;
  clone->num_children_ = num_children_ + 1;
  // cout << "sizeof(children_[0]) = " << sizeof(children_[0]) << endl;
  memcpy(&clone->children_[0], &children_[0], num_children_ * sizeof(children_[0]));
  clone->children_[num_children_] = child;
  return clone;
}

SumNode* SumNode::AddChild(ChoiceNode* child, EvalNodeArena& arena) {
  if (num_children_ + 1 <= capacity_) {
    children_[num_children_++] = child;
    num_in_capacity++;
    return this;
  }
  num_reallocs++;
  // cout << "Exceeded capacity!" << endl;
  SumNode* clone = arena.NewSumNodeWithCapacity(capacity_ + 2);
  clone->letter_ = letter_;
  clone->points_ = points_;
  clone->bound_ = bound_;
  clone->num_children_ = num_children_ + 1;
  // cout << "sizeof(children_[0]) = " << sizeof(children_[0]) << endl;
  memcpy(&clone->children_[0], &children_[0], num_children_ * sizeof(children_[0]));
  clone->children_[num_children_] = child;
  return clone;
}

ChoiceNode* ChoiceNode::AddChild(SumNode* child, EvalNodeArena& arena) {
  if (num_children_ + 1 <= capacity_) {
    children_[num_children_++] = child;
    num_in_capacity++;
    return this;
  }
  num_reallocs++;
  // cout << "Exceeded capacity!" << endl;
  ChoiceNode* clone = arena.NewChoiceNodeWithCapacity(capacity_ + 2);
  clone->cell_ = cell_;
  clone->bound_ = bound_;
  clone->num_children_ = num_children_ + 1;
  // cout << "sizeof(children_[0]) = " << sizeof(children_[0]) << endl;
  memcpy(&clone->children_[0], &children_[0], num_children_ * sizeof(children_[0]));
  clone->children_[num_children_] = child;
  return clone;
}

EvalNode* EvalNode::AddWordWork(
    int num_choices,
    pair<int, int>* choices,
    const int* num_letters,
    int points,
    EvalNodeArena& arena
) {
  if (!num_choices) {
    points_ += points;
    bound_ += points;
    return this;
  }

  auto cell = choices->first;
  auto letter = choices->second;
  choices++;
  num_choices--;

  EvalNode* choice_child = NULL;
  for (int i = 0; i < num_children_; i++) {
    const auto& c = children_[i];
    if (c->cell_ == cell) {
      choice_child = (EvalNode*)c;
      break;
    }
  }
  int old_choice_bound = 0;
  EvalNode* new_me = this;
  if (!choice_child) {
    // TODO: 1 could be a function of num_choices
    choice_child = arena.NewNodeWithCapacity(1);
    choice_child->letter_ = CHOICE_NODE;
    choice_child->cell_ = cell;
    choice_child->bound_ = 0;
    new_me = AddChild(choice_child, arena);
    sort(&new_me->children_[0], &new_me->children_[new_me->num_children_], SortByCell);
  } else {
    old_choice_bound = choice_child->bound_;
  }

  EvalNode* letter_child = NULL;
  for (int i = 0; i < choice_child->num_children_; i++) {
    auto c = choice_child->children_[i];
    if (c->letter_ == letter) {
      letter_child = (EvalNode*)c;
      break;
    }
  }
  if (!letter_child) {
    // TODO: capacity could be a more complex function of num_choices
    letter_child = arena.NewNodeWithCapacity(num_choices == 1 ? 0 : 1);
    letter_child->cell_ = cell;
    letter_child->letter_ = letter;
    letter_child->bound_ = 0;
    auto new_choice_child = choice_child->AddChild(letter_child, arena);
    if (new_choice_child != choice_child) {
      for (int i = 0; i < new_me->num_children_; i++) {
        const auto& c = new_me->children_[i];
        if (c->cell_ == cell) {
          new_me->children_[i] = new_choice_child;
          break;
        }
      }
      choice_child = new_choice_child;
    }
    sort(
        &choice_child->children_[0],
        &choice_child->children_[choice_child->num_children_],
        SortByLetter
    );
  }
  auto new_letter_child =
      letter_child->AddWordWork(num_choices, choices, num_letters, points, arena);
  if (new_letter_child != letter_child) {
    for (int i = 0; i < choice_child->num_children_; i++) {
      auto& c = choice_child->children_[i];
      if (c->letter_ == letter) {
        choice_child->children_[i] = new_letter_child;
        break;
      }
    }
  }
  letter_child = new_letter_child;

  if (letter_child->bound_ > old_choice_bound) {
    choice_child->bound_ = letter_child->bound_;
  }
  new_me->bound_ += (choice_child->bound_ - old_choice_bound);
  return new_me;
}

void EvalNode::AddWord(
    vector<pair<int, int>> choices, int points, EvalNodeArena& arena
) {
  vector<int> num_letters(choices.size(), 1);
  AddWordWork(choices.size(), choices.data(), num_letters.data(), points, arena);
}

vector<EvalNode*> EvalNode::GetChildren() {
  vector<EvalNode*> out;
  out.reserve(num_children_);
  for (int i = 0; i < num_children_; i++) {
    out.push_back(children_[i]);
  }
  return out;
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
  out.reserve(num_children_);
  for (int i = 0; i < num_children_; i++) {
    out.push_back(children_[i]);
  }
  return out;
}

bool EvalNode::StructuralEq(const EvalNode& other) const {
  if (letter_ != other.letter_ || cell_ != other.cell_) {
    return false;
  }
  if (bound_ != other.bound_) {
    return false;
  }
  if (points_ != other.points_) {
    return false;
  }
  vector<const EvalNode*> nnc, nno;
  for (int i = 0; i < num_children_; i++) {
    auto c = children_[i];
    if (c) nnc.push_back(c);
  }
  for (int i = 0; i < other.num_children_; i++) {
    auto c = other.children_[i];
    if (c) nno.push_back(c);
  }
  if (nnc.size() != nno.size()) {
    return false;
  }
  for (size_t i = 0; i < nnc.size(); ++i) {
    if (!nnc[i]->StructuralEq(*nno[i])) {
      return false;
    }
  }
  return true;
}

bool SumNode::StructuralEq(const SumNode& other) const {
  if (letter_ != other.letter_) {
    return false;
  }
  if (bound_ != other.bound_) {
    return false;
  }
  if (points_ != other.points_) {
    return false;
  }
  vector<const ChoiceNode*> nnc, nno;
  for (int i = 0; i < num_children_; i++) {
    auto c = children_[i];
    if (c) nnc.push_back(c);
  }
  for (int i = 0; i < other.num_children_; i++) {
    auto c = other.children_[i];
    if (c) nno.push_back(c);
  }
  if (nnc.size() != nno.size()) {
    return false;
  }
  for (size_t i = 0; i < nnc.size(); ++i) {
    if (!nnc[i]->StructuralEq(*nno[i])) {
      return false;
    }
  }
  return true;
}

bool ChoiceNode::StructuralEq(const ChoiceNode& other) const {
  if (cell_ != other.cell_) {
    return false;
  }
  if (bound_ != other.bound_) {
    return false;
  }
  vector<const SumNode*> nnc, nno;
  for (int i = 0; i < num_children_; i++) {
    auto c = children_[i];
    if (c) nnc.push_back(c);
  }
  for (int i = 0; i < other.num_children_; i++) {
    auto c = other.children_[i];
    if (c) nno.push_back(c);
  }
  if (nnc.size() != nno.size()) {
    return false;
  }
  for (size_t i = 0; i < nnc.size(); ++i) {
    if (!nnc[i]->StructuralEq(*nno[i])) {
      return false;
    }
  }
  return true;
}

void EvalNode::PrintJSON() const {
  cout << "{\"type\": \"";
  if (letter_ == CHOICE_NODE) {
    cout << "CHOICE";
  } else if (letter_ == ROOT_NODE) {
    cout << "ROOT";
  } else {
    cout << (int)cell_ << "=? (" << (int)letter_ << ")";
  }
  cout << "\", \"cell\": " << (int)cell_;
  cout << ", \"bound\": " << bound_;
  if (points_) {
    cout << ", \"points\": " << (int)points_;
  }
  if (num_children_) {
    cout << ", \"children\": [";
    bool has_commad = false;
    for (int i = 0; i < num_children_; i++) {
      const auto& c = children_[i];
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
  cout << "}";
}

void SumNode::PrintJSON() const {
  cout << "{\"type\": \"";
  if (letter_ == EvalNode::ROOT_NODE) {
    cout << "ROOT";
  } else {
    cout << (int)letter_;
  }
  cout << ", \"bound\": " << bound_;
  if (points_) {
    cout << ", \"points\": " << (int)points_;
  }
  if (num_children_) {
    cout << ", \"children\": [";
    bool has_commad = false;
    for (int i = 0; i < num_children_; i++) {
      const auto& c = children_[i];
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
  cout << "}";
}

void ChoiceNode::PrintJSON() const {
  cout << "{\"type\": \"CHOICE\", \"cell\": " << (int)cell_;
  cout << ", \"bound\": " << bound_;
  if (num_children_) {
    cout << ", \"children\": [";
    bool has_commad = false;
    for (int i = 0; i < num_children_; i++) {
      const auto& c = children_[i];
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
  cout << "}";
}

int EvalNode::NodeCount() const {
  int count = 1;
  for (int i = 0; i < num_children_; i++) {
    const auto& c = children_[i];
    if (c) count += c->NodeCount();
  }
  return count;
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
  for (int i = 0; i < num_children_; i++) {
    const auto& c = children_[i];
    if (c) count += c->NodeCount();
  }
  return count;
}

unsigned int EvalNode::ScoreWithForces(const vector<int>& forces) const {
  if (letter_ == CHOICE_NODE) {
    auto force = forces[cell_];
    if (force >= 0) {
      for (int i = 0; i < num_children_; i++) {
        const auto& child = children_[i];
        if (child->letter_ == force) {
          return child->ScoreWithForces(forces);
        }
      }
      return 0;
    }
  }

  // Otherwise, this is the same as regular scoring
  if (letter_ == CHOICE_NODE) {
    unsigned int score = 0;
    for (int i = 0; i < num_children_; i++) {
      const auto& child = children_[i];
      if (child) {
        score = std::max(score, child->ScoreWithForces(forces));
      }
    }
    return score;
  } else {
    unsigned int score = points_;
    for (int i = 0; i < num_children_; i++) {
      const auto& child = children_[i];
      if (child) {
        score += child->ScoreWithForces(forces);
      }
    }
    return score;
  }
}

unique_ptr<EvalNodeArena> create_eval_node_arena() {
  return unique_ptr<EvalNodeArena>(new EvalNodeArena);
}

void EvalNodeArena::AddBuffer() {
  char* buf = new char[EVAL_NODE_ARENA_BUFFER_SIZE];
  buffers_.push_back(buf);
  tip_ = 0;
}

template <typename T>
T* EvalNodeArena::NewNodeWithCapacity<T>(uint8_t capacity) {
  num_nodes_++;
  int size = sizeof(T) + capacity * sizeof(T::children_[0]);
  // cout << "sizeof(EvalNode)=" << sizeof(EvalNode) << " size: " << size << endl;
  if (tip_ + size > EVAL_NODE_ARENA_BUFFER_SIZE) {
    AddBuffer();
  }
  char* buf = &(*buffers_.rbegin())[tip_];
  T* n = new (buf) T;
  // TODO: update tip_ to enforce alignment
  tip_ += size;
  n->capacity_ = capacity;
  return n;
}

SumNode* EvalNodeArena::NewSumNodeWithCapacity(uint8_t capacity) {
  return NewNodeWithCapacity<SumNode>(capacity);
}

ChoiceNode* EvalNodeArena::NewChoiceNodeWithCapacity(uint8_t capacity) {
  return NewNodeWithCapacity<ChoiceNode>(capacity);
}

SumNode* EvalNodeArena::NewRootNodeWithCapacity(uint8_t capacity) {
  auto root = NewSumNodeWithCapacity(capacity);
  root->letter_ = EvalNode::ROOT_NODE;  // irrelevant
  root->points_ = 0;
  root->bound_ = 0;
  return root;
}

// block-scope functions cannot be declared inline.
inline uint16_t advance(
    const EvalNode* node, vector<int>& sums, vector<vector<const EvalNode*>>& stacks
) {
  // assert(node->letter_ != CHOICE_NODE);
  for (int i = 0; i < node->num_children_; i++) {
    auto child = node->children_[i];
    // assert(child->letter_ == CHOICE_NODE);
    stacks[child->cell_].push_back(child);
    sums[child->cell_] += child->bound_;
  }
  return node->points_;
}

tuple<vector<pair<int, string>>, vector<int>, vector<int>> EvalNode::OrderlyBound(
    int cutoff,
    const vector<string>& cells,
    const vector<int>& split_order,
    const vector<pair<int, int>>& preset_cells
) const {
  vector<vector<const EvalNode*>> stacks(cells.size());
  vector<pair<int, int>> choices;
  vector<int> stack_sums(cells.size(), 0);
  vector<pair<int, string>> failures;
  int n_preset = preset_cells.size();
  vector<int> elim_at_level(1 + cells.size() - n_preset, 0);
  vector<int> visit_at_level(1 + cells.size() - n_preset, 0);

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
        if (bound <= cutoff) {
          // elim_at_level[num_splits] += 1;
          return;  // done!
        }
        if (num_splits == split_order.size()) {
          record_failure(bound);
          return;
        }

        int next_to_split = split_order[num_splits];
        vector<int> stack_top(stacks.size());
        for (int i = 0; i < stacks.size(); ++i) {
          stack_top[i] = stacks[i].size();
        }
        vector<int> base_sums = stack_sums;

        auto& next_stack = stacks[next_to_split];
        vector<pair<EvalNode* const*, EvalNode* const*>> its;
        its.reserve(next_stack.size());
        for (auto& n : next_stack) {
          // assert(n->letter_ == CHOICE_NODE);
          // assert(n->cell_ == next_to_split);
          its.push_back({&n->children_[0], &n->children_[n->num_children_]});
        }

        int num_letters = cells[next_to_split].size();
        for (int letter = 0; letter < num_letters; ++letter) {
          if (letter > 0) {
            // TODO: it should be possible to avoid this copy with another
            // stack.
            stack_sums = base_sums;
            for (int i = 0; i < stacks.size(); ++i) {
              // This will not de-allocate anything, just reduce size.
              // https://cplusplus.com/reference/vector/vector/resize/
              stacks[i].resize(stack_top[i]);
            }
          }
          choices.emplace_back(next_to_split, letter);
          int points = base_points;
          for (auto& [it, end] : its) {
            if (it != end && (*it)->letter_ == letter) {
              // visit_at_level[1 + num_splits] += 1;
              points += advance(*it, stack_sums, stacks);
              ++it;
            }
          }
          rec(points, num_splits + 1, stack_sums);
          choices.pop_back();
        }
      };

  vector<int> sums(cells.size(), 0);
  // visit_at_level[0] += 1;
  auto base_points = advance(this, sums, stacks);
  rec(base_points, 0, sums);
  return {failures, visit_at_level, elim_at_level};
}

EvalNode* merge_orderly_tree(
    const EvalNode* a, const EvalNode* b, EvalNodeArena& arena
);
EvalNode* merge_orderly_tree_children(
    const EvalNode* a,
    EvalNode* const* bc,
    int num_bc,
    int b_points,
    EvalNodeArena& arena
);
EvalNode* merge_orderly_choice_children(
    const EvalNode* a, const EvalNode* b, EvalNodeArena& arena
);

EvalNode* merge_orderly_choice_children(
    const EvalNode* a, const EvalNode* b, EvalNodeArena& arena
) {
  assert(a->letter_ == EvalNode::CHOICE_NODE);
  assert(b->letter_ == EvalNode::CHOICE_NODE);
  assert(a->cell_ == b->cell_);

  auto it_a = &a->children_[0];
  auto it_b = &b->children_[0];
  const auto& a_end = it_a + a->num_children_;
  const auto& b_end = it_b + b->num_children_;
  int num_children = 0;
  while (it_a != a_end && it_b != b_end) {
    const auto& a_child = *it_a;
    const auto& b_child = *it_b;
    if (a_child->letter_ < b_child->letter_) {
      num_children++;
      ++it_a;
    } else if (b_child->letter_ < a_child->letter_) {
      num_children++;
      ++it_b;
    } else {
      num_children++;
      ++it_a;
      ++it_b;
    }
  }
  num_children += (a_end - it_a) + (b_end - it_b);

  EvalNode* n = arena.NewNodeWithCapacity(num_children);
  n->letter_ = EvalNode::CHOICE_NODE;
  n->cell_ = a->cell_;
  n->points_ = 0;
  n->bound_ = 0;

  it_a = &a->children_[0];
  it_b = &b->children_[0];
  int out_i = 0;
  while (it_a != a_end && it_b != b_end) {
    const auto& a_child = *it_a;
    const auto& b_child = *it_b;
    if (a_child->letter_ < b_child->letter_) {
      n->children_[out_i++] = a_child;
      if (a_child) {
        n->bound_ = max(n->bound_, a_child->bound_);
      }
      ++it_a;
    } else if (b_child->letter_ < a_child->letter_) {
      n->children_[out_i++] = b_child;
      if (b_child) {
        n->bound_ = max(n->bound_, b_child->bound_);
      }
      ++it_b;
    } else {
      auto merged = merge_orderly_tree(a_child, b_child, arena);
      n->children_[out_i++] = merged;
      if (merged) {
        n->bound_ = max(n->bound_, merged->bound_);
      }
      ++it_a;
      ++it_b;
    }
  }

  while (it_a != a_end) {
    const auto& a_child = *it_a;
    n->children_[out_i++] = a_child;
    if (a_child) {
      n->bound_ = max(n->bound_, a_child->bound_);
    }
    ++it_a;
  }
  while (it_b != b_end) {
    const auto& b_child = *it_b;
    n->children_[out_i++] = b_child;
    if (b_child) {
      n->bound_ = max(n->bound_, b_child->bound_);
    }
    ++it_b;
  }
  assert(out_i == num_children);
  n->num_children_ = num_children;

  return n;
}

EvalNode* merge_orderly_tree_children(
    const EvalNode* a,
    EvalNode* const* bc,
    int num_bc,
    int b_points,
    EvalNodeArena& arena
) {
  assert(a->letter_ != EvalNode::CHOICE_NODE);

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

  EvalNode* n = arena.NewNodeWithCapacity(num_children);
  n->letter_ = a->letter_;
  n->cell_ = a->cell_;
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

EvalNode* merge_orderly_tree(
    const EvalNode* a, const EvalNode* b, EvalNodeArena& arena
) {
  assert(a->letter_ != EvalNode::CHOICE_NODE);
  assert(b->letter_ != EvalNode::CHOICE_NODE);
  return merge_orderly_tree_children(
      a, &b->children_[0], b->num_children_, b->points_, arena
  );
}

vector<const EvalNode*> EvalNode::OrderlyForceCell(
    int cell, int num_lets, EvalNodeArena& arena
) const {
  assert(letter_ != CHOICE_NODE);
  if (!num_children_) {
    return {this};  // XXX this is not the same as what Python does
  }

  vector<EvalNode*> non_cell_children;
  non_cell_children.reserve(num_children_ - 1);
  const EvalNode* top_choice = NULL;
  for (int i = 0; i < num_children_; i++) {
    auto& child = children_[i];
    if (child->cell_ == cell) {
      top_choice = child;
    } else {
      non_cell_children.push_back(child);
    }
  }

  if (!top_choice) {
    return {this};  // XXX this is not the same as what Python does
  }
  assert(top_choice->letter_ == CHOICE_NODE);

  int non_cell_points = points_;

  vector<const EvalNode*> out(num_lets, nullptr);
  for (int i = 0; i < top_choice->num_children_; i++) {
    const auto& child = top_choice->children_[i];
    out[child->letter_] = merge_orderly_tree_children(
        child, &non_cell_children[0], non_cell_children.size(), non_cell_points, arena
    );
  }

  if (top_choice->num_children_ < num_lets) {
    int other_bound = 0;
    for (auto c : non_cell_children) {
      if (c) {
        other_bound += c->bound_;
      }
    }
    if (other_bound > 0 || non_cell_points > 0) {
      for (int i = 0; i < num_lets; ++i) {
        if (!out[i]) {
          EvalNode* point_node = arena.NewNodeWithCapacity(non_cell_children.size());
          point_node->points_ = non_cell_points;
          point_node->cell_ = cell;
          point_node->letter_ = i;
          point_node->bound_ = non_cell_points + other_bound;
          point_node->SetChildrenFromVector(non_cell_children);
          out[i] = point_node;
        }
      }
    }
  }
  return out;
}

void EvalNode::SetChildrenFromVector(const vector<EvalNode*>& children) {
  num_children_ = children.size();
  memcpy(&children_[0], &children[0], num_children_ * sizeof(EvalNode*));
}
