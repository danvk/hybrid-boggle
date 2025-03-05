#include "eval_node.h"

#include <bit>
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

void EvalNode::SetChildrenFromVector(const vector<EvalNode*>& children) {
  num_children_ = children.size();
  memcpy(&children_[0], &children[0], num_children_ * sizeof(EvalNode*));
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

int EvalNode::NodeCount() const {
  int count = 1;
  for (int i = 0; i < num_children_; i++) {
    const auto& c = children_[i];
    if (c) count += c->NodeCount();
  }
  return count;
}

unsigned int EvalNode::UniqueNodeCount(uint32_t mark) const {
  throw runtime_error("not implemented");
  return 0;
}

unsigned int EvalNode::ScoreWithForces(const vector<int>& forces) const {
  if (letter_ == CHOICE_NODE) {
    auto force = forces[cell_];
    if (force >= 0) {
      if (points_ & (1 << force)) {
        unsigned int mask = points_ & ((1 << force) - 1);
        unsigned int idx = std::popcount(mask);
        auto child = children_[idx];
        if (child) {
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

// Borrowed from Boost.ContainerHash via
// https://stackoverflow.com/a/78509978/388951
// https://github.com/boostorg/container_hash/blob/ee5285bfa64843a11e29700298c83a37e3132fcd/include/boost/container_hash/hash.hpp#L471
template <typename T>
void hash_combine(std::size_t& seed, const T& v) {
  static constexpr auto digits = std::numeric_limits<std::size_t>::digits;
  static_assert(digits == 64 || digits == 32);

  if constexpr (digits == 64) {
    // https://github.com/boostorg/container_hash/blob/ee5285bfa64843a11e29700298c83a37e3132fcd/include/boost/container_hash/detail/hash_mix.hpp#L67
    std::size_t x = seed + 0x9e3779b9 + std::hash<T>()(v);
    const std::size_t m = 0xe9846af9b1a615d;
    x ^= x >> 32;
    x *= m;
    x ^= x >> 32;
    x *= m;
    x ^= x >> 28;
    seed = x;
  } else {  // 32-bits
    // https://github.com/boostorg/container_hash/blob/ee5285bfa64843a11e29700298c83a37e3132fcd/include/boost/container_hash/detail/hash_mix.hpp#L88
    std::size_t x = seed + 0x9e3779b9 + std::hash<T>()(v);
    const std::size_t m1 = 0x21f0aaad;
    const std::size_t m2 = 0x735a2d97;
    x ^= x >> 16;
    x *= m1;
    x ^= x >> 15;
    x *= m2;
    x ^= x >> 15;
    seed = x;
  }
}

uint64_t EvalNode::StructuralHash() const {
  static constexpr auto digits = std::numeric_limits<std::size_t>::digits;
  static_assert(digits == 64 || digits == 32);
  // letter, cell, points, children
  size_t h = 0xb0881e;
  hash_combine(h, letter_);
  hash_combine(h, cell_);
  hash_combine(h, points_);
  // TODO: bound_? choice_mask_?
  for (int i = 0; i < num_children_; i++) {
    const auto& c = children_[i];
    if (c) {
      hash_combine(h, c->StructuralHash());
    }
  }
  return h;
}

unique_ptr<EvalNodeArena> create_eval_node_arena() {
  return unique_ptr<EvalNodeArena>(new EvalNodeArena);
}

void EvalNodeArena::AddBuffer() {
  char* buf = new char[EVAL_NODE_ARENA_BUFFER_SIZE];
  buffers_.push_back(buf);
  tip_ = 0;
}

EvalNode* EvalNodeArena::NewNodeWithCapacity(uint8_t capacity) {
  int size = sizeof(EvalNode) + capacity * sizeof(EvalNode::children_[0]);
  // cout << "sizeof(EvalNode)=" << sizeof(EvalNode) << " size: " << size << endl;
  if (tip_ + size > EVAL_NODE_ARENA_BUFFER_SIZE) {
    AddBuffer();
  }
  char* buf = &(*buffers_.rbegin())[tip_];
  EvalNode* n = new (buf) EvalNode;
  // TODO: update tip_ to enforce alignment
  // TODO: probably don't need to set all these fields
  tip_ += size;
  n->letter_ = EvalNode::ROOT_NODE;
  n->cell_ = 0;
  n->bound_ = 0;
  n->capacity_ = capacity;
  return n;
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

  vector<EvalNode*> out;
  auto it_a = &a->children_[0];
  auto it_b = &b->children_[0];
  const auto& a_end = it_a + a->num_children_;
  const auto& b_end = it_b + b->num_children_;

  while (it_a != a_end && it_b != b_end) {
    const auto& a_child = *it_a;
    const auto& b_child = *it_b;
    if (a_child->letter_ < b_child->letter_) {
      out.push_back(a_child);
      ++it_a;
    } else if (b_child->letter_ < a_child->letter_) {
      out.push_back(b_child);
      ++it_b;
    } else {
      out.push_back(merge_orderly_tree(a_child, b_child, arena));
      ++it_a;
      ++it_b;
    }
  }

  while (it_a != a_end) {
    out.push_back(*it_a);
    ++it_a;
  }

  while (it_b != b_end) {
    out.push_back(*it_b);
    ++it_b;
  }

  EvalNode* n = arena.NewNodeWithCapacity(out.size());
  n->letter_ = EvalNode::CHOICE_NODE;
  n->cell_ = a->cell_;
  // TODO: could avoid this copy with a first pass to determine overlap
  n->SetChildrenFromVector(out);
  n->points_ = 0;
  n->bound_ = 0;
  for (int i = 0; i < n->num_children_; i++) {
    auto child = n->children_[i];
    if (child) {
      n->bound_ = max(n->bound_, child->bound_);
    }
  }
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

  // TODO: factor out this counting
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

  while (it_a != a_end) {
    num_children += 1;
    ++it_a;
  }

  while (it_b != b_end) {
    num_children += 1;
    ++it_b;
  }

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
      ++it_a;
    } else if (b_child->cell_ < a_child->cell_) {
      n->children_[out_i++] = b_child;
      ++it_b;
    } else {
      n->children_[out_i++] = merge_orderly_choice_children(a_child, b_child, arena);
      ++it_a;
      ++it_b;
    }
  }

  while (it_a != a_end) {
    n->children_[out_i++] = *it_a;
    ++it_a;
  }

  while (it_b != b_end) {
    n->children_[out_i++] = *it_a;
    ++it_b;
  }
  assert(out_i == num_children);
  n->num_children_ = num_children;

  // TODO: fold this into the previous loop
  for (int i = 0; i < n->num_children_; i++) {
    auto child = n->children_[i];
    if (child) {
      n->bound_ += child->bound_;
    }
  }
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

  if (non_cell_points && top_choice->num_children_ < num_lets) {
    // TODO: these could all be the same node with a different EvalNode layout.
    for (int i = 0; i < num_lets; ++i) {
      if (!out[i]) {
        EvalNode* point_node = arena.NewNodeWithCapacity(0);
        point_node->points_ = point_node->bound_ = non_cell_points;
        point_node->cell_ = cell;
        point_node->letter_ = i;
        out[i] = point_node;
      }
    }
  }
  return out;
}
