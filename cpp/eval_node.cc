#include "eval_node.h"

#include <bit>
#include <functional>
#include <limits>
#include <variant>
#include <vector>

using namespace std;

// uint64_t hash_collisions = 0;

static const bool MERGE_TREES = true;

inline bool SortByLetter(const EvalNode* a, const EvalNode* b) {
  return a->letter_ < b->letter_;
}

void EvalNode::AddWordWork(int num_choices, pair<int, int>* choices, const int* num_letters, int points, EvalNodeArena& arena) {
  if (!num_choices) {
    points_ += points;
    bound_ += points;
    return;
  }

  auto cell = choices->first;
  auto letter = choices->second;
  choices++;
  num_choices--;

  EvalNode* choice_child = NULL;
  for (auto c : children_) {
    if (c->cell_ == cell) {
      choice_child = (EvalNode*)c;
      break;
    }
  }
  int old_choice_bound = 0;
  if (!choice_child) {
    choice_child = new EvalNode;
    choice_child->letter_ = CHOICE_NODE;
    choice_child->cell_ = cell;
    choice_child->bound_ = 0;
    choice_child->choice_mask_ = num_letters[cell] > 1 ? (1 << cell) : 0;
    arena.AddNode(choice_child);
    children_.push_back(choice_child);
  } else {
    old_choice_bound = choice_child->bound_;
  }

  EvalNode* letter_child = NULL;
  for (auto c : choice_child->children_) {
    if (c->letter_ == letter) {
      letter_child = (EvalNode*)c;
      break;
    }
  }
  if (!letter_child) {
    letter_child = new EvalNode;
    letter_child->cell_ = cell;
    letter_child->letter_ = letter;
    letter_child->bound_ = 0;
    arena.AddNode(letter_child);
    choice_child->children_.push_back(letter_child);
    sort(choice_child->children_.begin(), choice_child->children_.end(), SortByLetter);
  }
  letter_child->AddWordWork(num_choices, choices, num_letters, points, arena);

  if (letter_child->bound_ > old_choice_bound) {
    choice_child->bound_ = letter_child->bound_;
  }
  choice_child->choice_mask_ |= letter_child->choice_mask_;
  choice_mask_ |= choice_child->choice_mask_;
  bound_ += (choice_child->bound_ - old_choice_bound);
}

void EvalNode::AddWord(vector<pair<int, int>> choices, int points, EvalNodeArena& arena) {
  vector<int> num_letters(choices.size(), 1);
  AddWordWork(choices.size(), choices.data(), num_letters.data(), points, arena);
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
  for (auto c : children_) {
    if (c) nnc.push_back(c);
  }
  for (auto c : other.children_) {
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
  if (!children_.empty()) {
    cout << ", \"children\": [";
    bool has_commad = false;
    for (auto c : children_) {
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

void EvalNode::SetComputedFields(vector<int>& num_letters) {
  for (auto c : children_) {
    if (c) {
      ((EvalNode*)c)->SetComputedFields(num_letters);
    }
  }

  if (letter_ == CHOICE_NODE) {
    choice_mask_ = num_letters[cell_] > 1 ? (1 << cell_) : 0;
    bound_ = 0;
    for (auto c : children_) {
      if (c) {
        bound_ = max(bound_, c->bound_);
      }
    }
  } else {
    choice_mask_ = 0;
    bound_ = points_;
    for (auto c : children_) {
      if (c) {
        bound_ += c->bound_;
      }
    }
  }

  for (auto c : children_) {
    if (c) {
      choice_mask_ |= c->choice_mask_;
    }
  }
}

const EvalNode* SqueezeChoiceChild(const EvalNode* child);
bool SqueezeSumNodeInPlace(EvalNode* node, EvalNodeArena& arena, bool should_merge);

int EvalNode::NodeCount() const {
  int count = 1;
  for (int i = 0; i < children_.size(); i++) {
    if (children_[i]) count += children_[i]->NodeCount();
  }
  return count;
}

unsigned int EvalNode::UniqueNodeCount(uint32_t mark) const {
  throw runtime_error("not implemented");
  return 0;
}

int EvalNode::RecomputeScore() const {
  if (letter_ == CHOICE_NODE) {
    // Choose the max amongst each possibility.
    int max_score = 0;
    for (int i = 0; i < children_.size(); i++) {
      if (children_[i])
        max_score = max(max_score, children_[i]->RecomputeScore());
    }
    return max_score;
  } else {
    // Add in the contributions of all neighbors.
    // (or all initial squares if this is the root node)
    int score = points_;
    for (int i = 0; i < children_.size(); i++) {
      if (children_[i])
        score += children_[i]->RecomputeScore();
    }
    return score;
  }
}

const EvalNode*
EvalNode::LiftChoice(int cell, int num_lets, EvalNodeArena& arena, uint32_t mark, bool dedupe, bool compress) const {
  if (letter_ == CHOICE_NODE && cell_ == cell) {
    // This is already in the right form. Nothing more to do!
    return this;
  }

  if ((choice_mask_ & (1 << cell)) == 0) {
    // There's no relevant choice below us, so we can bottom out.
    return this;
  }

  // hash_collisions = 0;
  VectorArena vector_arena;  // goes out of scope at end of function
  auto one_or_choices = ForceCell(cell, num_lets, arena, vector_arena, mark, dedupe, compress);
  vector<const EvalNode*> choices;
  if (holds_alternative<vector<const EvalNode*>*> (one_or_choices)) {
    auto rv = std::get<vector<const EvalNode*>*>(one_or_choices);
    rv->swap(choices);
  } else {
    auto one = std::get<const EvalNode*>(one_or_choices);
    for (int i = 0; i < num_lets; i++) {
      choices.push_back(one);
    }
  }
  auto node = new EvalNode;
  arena.AddNode(node);
  node->letter_ = CHOICE_NODE;
  node->cell_ = cell;
  node->points_ = 0;
  node->bound_ = 0;
  node->choice_mask_ = 1 << cell;
  for (auto child : choices) {
    node->bound_ = max(node->bound_, child->bound_);
    node->choice_mask_ |= child->choice_mask_;
  }
  node->children_.swap(choices);
  // cout << "Prevented " << hash_collisions << " hash collisions" << endl;
  return node;
}

variant<const EvalNode*, vector<const EvalNode*>*>
EvalNode::ForceCell(int cell, int num_lets, EvalNodeArena& arena, VectorArena& vector_arena, uint32_t mark, bool dedupe, bool compress) const {
  unordered_map<uint64_t, const EvalNode*> force_cell_cache;
  auto out = ForceCellWork(cell, num_lets, arena, vector_arena, mark, dedupe, compress, force_cell_cache);
  return out;
}

variant<const EvalNode*, vector<const EvalNode*>*>
EvalNode::ForceCellWork(int cell, int num_lets, EvalNodeArena& arena, VectorArena& vector_arena, uint32_t mark, bool dedupe, bool compress, unordered_map<uint64_t, const EvalNode*>& force_cell_cache) const {
  if (letter_ == EvalNode::CHOICE_NODE && cell_ == cell) {
    // This is the forced cell.
    // We've already tried each possibility, but they may not be aligned.
    auto out = new vector<const EvalNode*>(num_lets, NULL);
    for (auto child : children_) {
      if (child) {
        auto letter = child->letter_;
        if (compress) {
          // TODO: this doesn't seem to help
          child = SqueezeChoiceChild(child);
        }
        out->at(letter) = child;
        // assert(child.choice_mask & (1 << force_cell) == 0);
      }
    }
    vector_arena.AddNode(out);
    return {out};
  }

  if ((choice_mask_ & (1 << cell)) == 0) {
    // There's no relevant choice below us, so we can bottom out.
    return {this};
  }

  vector<variant<const EvalNode*, vector<const EvalNode*>*>> results;
  results.reserve(children_.size());
  for (auto child : children_) {
    if (child) {
      results.push_back(child->ForceCellWork(cell, num_lets, arena, vector_arena, mark, dedupe, compress, force_cell_cache));
    } else {
      // TODO: can this happen? (evidently not)
      results.push_back({(EvalNode*)NULL});
    }
  }

  auto out = new vector<const EvalNode*>;
  vector_arena.AddNode(out);
  out->reserve(num_lets);
  for (int i = 0; i < num_lets; i++) {
    vector<const EvalNode*> children;
    for (auto &result : results) {
      if (holds_alternative<const EvalNode*>(result)) {
        children.push_back(std::get<const EvalNode*>(result));
      } else {
        children.push_back(std::get<vector<const EvalNode*>*>(result)->at(i));
      }
    }

    uint16_t node_choice_mask = 0;
    unsigned int node_bound = 0;
    if (letter_ == CHOICE_NODE) {
      for (auto &child : children) {
        if (child) {
          node_bound = std::max(node_bound, child->bound_);
        }
      }
      node_choice_mask = (1 << cell_) & choice_mask_;
    } else {
      node_bound = points_;
      for (auto child : children) {
        if (child) {
          node_bound += child->bound_;
        }
      }
    }
    const EvalNode* out_node = NULL;
    if (node_bound) {
      EvalNode* node = new EvalNode;
      node->letter_ = letter_;
      node->points_ = points_;
      node->cell_ = cell_;
      node->bound_ = node_bound;
      node->children_.swap(children);
      node->choice_mask_ = node_choice_mask;
      if (letter_ == ROOT_NODE) {
        // It would be nice to leave this as a ROOT_NODE to simplify finding the
        // edge of the max root tree vs. the eval tree.
        node->letter_ = i;
        node->cell_ = cell;
      }
      for (auto child : node->children_) {
        if (child) {
          node->choice_mask_ |= child->choice_mask_;
        }
      }

      uint64_t h;
      if (dedupe) {
        h = node->StructuralHash();
        auto r = force_cell_cache.find(h);
        if (r != force_cell_cache.end()) {
          auto& match = r->second;
          // We don't compare points here because that could be changed by SqueezeSumNodeInPlace().
          // We want _equivalent_ nodes, not identical nodes.
          if (match->cell_ == node->cell_ && match->letter_ == node->letter_) {
            out_node = r->second;
            delete node;
          } else {
            // hash_collisions++;
          }
        }
      }

      if (!out_node) {
        arena.AddNode(node);
        out_node = node;
        bool any_changes = false;
        if (compress && node->letter_ != CHOICE_NODE) {
          any_changes = SqueezeSumNodeInPlace(node, arena, MERGE_TREES);
        }
        if (dedupe) {
          force_cell_cache[h] = node;
          if (any_changes) {
            force_cell_cache[node->StructuralHash()] = node;
          }
        }
      }
    }
    out->push_back(out_node);
  }

  return {out};
}

unsigned int EvalNode::ScoreWithForces(const vector<int>& forces) const {
  uint16_t choice_mask = 0;
  for (int i = 0; i < forces.size(); i++) {
    if (forces[i] >= 0) {
      choice_mask |= (1 << i);
    }
  }
  return ScoreWithForcesMask(forces, choice_mask);
}

unsigned int EvalNode::ScoreWithForcesMask(const vector<int>& forces, uint16_t choice_mask) const {
  if (letter_ == CHOICE_NODE) {
    auto force = forces[cell_];
    if (force >= 0) {
      if (points_ & (1 << force)) {
        unsigned int mask = points_ & ((1 << force) - 1);
        unsigned int idx = std::popcount(mask);
        auto child = children_[idx];
        if (child) {
          return child->ScoreWithForcesMask(forces, choice_mask);
        }
      }
      return 0;
    }
  }

  if (!(choice_mask_ & choice_mask)) {
    // The force is irrelevant to this subtree, so we don't need to traverse it.
    return bound_;
  }

  // Otherwise, this is the same as regular scoring
  if (letter_ == CHOICE_NODE) {
    unsigned int score = 0;
    for (const auto& child : children_) {
      if (child) {
        score = std::max(score, child->ScoreWithForcesMask(forces, choice_mask));
      }
    }
    return score;
  } else {
    unsigned int score = points_;
    for (const auto& child : children_) {
      if (child) {
        score += child->ScoreWithForcesMask(forces, choice_mask);
      }
    }
    return score;
  }
}

int EvalNode::FilterBelowThreshold(int min_score) {
  if (letter_ != CHOICE_NODE) {
    return 0;
  }
  int num_filtered = 0;
  for (int i = 0; i < children_.size(); i++) {
    auto child = children_[i];
    if (!child) {
      continue;
    }
    if (child->bound_ <= min_score) {
      children_[i] = NULL;
      num_filtered++;
    } else {
      // This casts away the const-ness.
      num_filtered += ((EvalNode*)child)->FilterBelowThreshold(min_score);
    }
  }
  return num_filtered;
}

vector<pair<const EvalNode*, vector<pair<int, int>>>> EvalNode::MaxSubtrees() const {
  vector<pair<const EvalNode*, vector<pair<int, int>>>> out;
  vector<pair<int, int>> path;
  MaxSubtreesHelp(out, path);
  return out;
}

void EvalNode::MaxSubtreesHelp(
    vector<pair<const EvalNode*, vector<pair<int, int>>>>& out,
    vector<pair<int, int>> path
) const {
  if (letter_ != CHOICE_NODE) {
    out.push_back({this, path});
  } else {
    for (int i = 0; i < children_.size(); i++) {
      auto child = children_[i];
      if (child) {
        vector<pair<int, int>> new_path(path);
        new_path.push_back({cell_, i});
        child->MaxSubtreesHelp(out, new_path);
      }
    }
  }
}

// Borrowed from Boost.ContainerHash via https://stackoverflow.com/a/78509978/388951
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
  }
  else { // 32-bits
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
  for (auto c : children_) {
    if (c) {
      hash_combine(h, c->StructuralHash());
    }
  }
  return h;
}

// Collapse sum nodes where possible.
const EvalNode* SqueezeChoiceChild(const EvalNode* child) {
  if (child->points_) {
    return child;
  }
  const EvalNode* non_null_child = NULL;
  for (auto c : child->children_) {
    if (c != NULL) {
      if (non_null_child) {
        return child;  // two non-null children
      }
      non_null_child = c;
    }
  }
  // return the non-null child if there's exactly one.
  return non_null_child ? non_null_child : child;
}

EvalNode* merge_trees(EvalNode* a, EvalNode* b, EvalNodeArena& arena);
void merge_choice_collisions_in_place(vector<const EvalNode*>& choices, EvalNodeArena& arena);

bool any_choice_collisions(const vector<const EvalNode*>& choices) {
  uint32_t cell_mask = 0;
  for (auto child : choices) {
    if (child && child->letter_ == EvalNode::CHOICE_NODE) {
      uint32_t cell_bit = 1 << child->cell_;
      if (cell_mask & cell_bit) {
        return true;
      }
      cell_mask |= cell_bit;
    }
  }
  return false;
}

// Absorb non-choice nodes into this sum node. Operates in-place.
// Returns a boolean indicating whether any changes were made.
bool SqueezeSumNodeInPlace(EvalNode* node, EvalNodeArena& arena, bool should_merge) {
  if (node->children_.empty()) {
    return false;
  }

  bool any_sum_children = false, any_null = false;
  for (auto c : node->children_) {
    if (c) {
      if (c->letter_ != EvalNode::CHOICE_NODE) {
        any_sum_children = true;
        break;
      }
    } else {
      any_null = true;
    }
  }

  bool any_collisions = any_choice_collisions(node->children_);

  if (!any_sum_children && !any_collisions) {
    if (any_null) {
      auto& children = node->children_;
      auto new_end = std::remove(children.begin(), children.end(), nullptr);
      children.erase(new_end, children.end());
      return true;
    }
    return false;
  }

  vector<const EvalNode*> non_choice;
  vector<const EvalNode*> choice;
  for (auto c : node->children_) {
    if (c) {
      if (c->letter_ == EvalNode::CHOICE_NODE) {
        choice.push_back(c);
      } else {
        non_choice.push_back(c);
      }
    }
  }

  // look for repeated choice cells
  if (should_merge && any_collisions) {
    merge_choice_collisions_in_place(choice, arena);
  }

  // There's something to absorb.
  // TODO: pre-reserve the right number of slots for new_children
  auto& new_children = choice;
  uint32_t new_points_from_children = 0;
  for (auto c : non_choice) {
    new_points_from_children += c->points_;
    new_children.insert(new_children.end(), c->children_.begin(), c->children_.end());
  }

  // new_children should be entirely choice nodes now, but there may be new collisions.
  if (should_merge && any_choice_collisions(new_children)) {
    merge_choice_collisions_in_place(new_children, arena);
  }
  node->children_.swap(new_children);

  // We need to take care here not to double-count points for the bound.
  node->points_ += new_points_from_children;
  uint32_t child_bound = 0;
  for (auto c : node->children_) {
    if (c) {
      child_bound += c->bound_;
    }
  }

  node->bound_ = node->points_ + child_bound;
  return true;
}

unique_ptr<EvalNodeArena> create_eval_node_arena() {
  return unique_ptr<EvalNodeArena>(new EvalNodeArena);
}

unique_ptr<VectorArena> create_vector_arena() {
  return unique_ptr<VectorArena>(new VectorArena);
}

void BoundRemainingBoardsHelp(
  const EvalNode* t,
  const vector<string>& cells,
  vector<int>& choices,
  int cutoff,
  vector<int> split_order,
  int split_order_index,
  vector<string>& results
) {
  int cell = -1;
  for (auto order : split_order) {
    if (choices[order] == -1) {
      cell = order;
      break;
    }
  }
  if (cell == -1) {
    string board(cells.size(), '.');
    for (int j = 0; j < choices.size(); j++) {
      auto idx = choices[j];
      board[j] = cells[j][idx];
    }
    results.push_back(board);
    return;
  }

  int n = cells[cell].size();
  for (int idx = 0; idx < n; idx++) {
    choices[cell] = idx;
    auto ub = t->ScoreWithForces(choices);
    if (ub > cutoff) {
      BoundRemainingBoardsHelp(t, cells, choices, cutoff, split_order, split_order_index, results);
    }
  }
  choices[cell] = -1;
}

vector<string> EvalNode::BoundRemainingBoards(
  vector<string> cells,
  int cutoff,
  vector<int> split_order
) {
  // TODO: maybe this can be in Python and this function just takes num_letters
  vector<int> num_letters;
  for (auto cell : cells) {
    num_letters.push_back(cell.size());
  }
  vector<string> results;
  vector<int> choices(cells.size(), -1);
  vector<int> remaining_split_order;
  for (auto& mt : MaxSubtrees()) {
    auto& t = mt.first;
    auto& seq = mt.second;
    for (auto& choice : choices) choice = -1;
    for (const auto& s : seq) {
      auto cell = s.first;
      auto letter = s.second;
      choices[cell] = letter;
    }
    remaining_split_order.clear();
    for (auto order : split_order) {
      if (choices[order] == -1) {
        remaining_split_order.push_back(order);
      }
    }
    BoundRemainingBoardsHelp(t, cells, choices, cutoff, remaining_split_order, 0, results);
  }
  return results;
}

void EvalNode::SetChoicePointMask(const vector<int>& num_letters) {
  if (letter_ == CHOICE_NODE) {
    if (points_ == 0) {
      int n = num_letters[cell_];
      if (children_.size() == n) {
        // dense -- the children are all set, but may be null.
        points_ = (1 << n) - 1;
      } else {
        // sparse
        int last_letter = -1;
        for (const auto& child : children_) {
          if (child) {
            points_ += (1 << child->letter_);
            last_letter = child->letter_;
          } else {
            last_letter++;
            points_ += (1 << last_letter);
          }
        }
      }
    } else {
      return;  // we've already visited this node (DAG optimization)
    }
  }

  for (auto c : children_) {
    if (c) {
      ((EvalNode*)c)->SetChoicePointMask(num_letters);
    }
  }
}

void EvalNode::ResetChoicePointMask() {
  if (letter_ == CHOICE_NODE) {
    points_ = 0;
  }
  for (auto c : children_) {
    if (c) {
      ((EvalNode*)c)->ResetChoicePointMask();
    }
  }
}

template<typename T>
int Arena<T>::MarkAndSweep(T* root, uint32_t mark) {
  throw new runtime_error("MarkAndSweep not implemented");
}

template <typename T>
T* Arena<T>::NewNode() {
  throw new runtime_error("not implemented");
}

template <>
EvalNode* Arena<EvalNode>::NewNode() {
  EvalNode* n = new EvalNode;
  n->letter_ = EvalNode::ROOT_NODE;
  n->cell_ = 0;
  AddNode(n);
  return n;
}

const EvalNode* merge_trees(const EvalNode* a, const EvalNode* b, EvalNodeArena& arena);

// This relies on a and b being sorted by letter_.
void merge_choice_children(const EvalNode* na, const EvalNode* nb, EvalNodeArena& arena, vector<const EvalNode*>& out) {
  auto it_a = na->children_.begin();
  auto it_b = nb->children_.begin();
  const auto& a_end = na->children_.end();
  const auto& b_end = nb->children_.end();
  while (it_a != a_end && it_b != b_end) {
    const auto& a = *it_a;
    if (!a) {
      ++it_a;
      continue;
    }
    const auto& b = *it_b;
    if (!b) {
      ++it_b;
      continue;
    }
    if (a->letter_ < b->letter_) {
      out.push_back(a);
      ++it_a;
    } else if (b->letter_ < a->letter_) {
      out.push_back(b);
      ++it_b;
    } else {
      out.push_back(merge_trees(a, b, arena));
      ++it_a;
      ++it_b;
    }
  }
  while (it_a != a_end) {
    if (*it_a) {
      out.push_back(*it_a);
    }
    ++it_a;
  }
  while (it_b != b_end) {
    if (*it_b) {
      out.push_back(*it_b);
    }
    ++it_b;
  }
}

// TODO: make this operate in-place so that it doesn't need to allocate memory.
const EvalNode* merge_trees(const EvalNode* a, const EvalNode* b, EvalNodeArena& arena) {
  assert(a->cell_ == b->cell_);

  if (a->letter_ == EvalNode::CHOICE_NODE && b->letter_ == EvalNode::CHOICE_NODE) {
    vector<const EvalNode*> children;
    merge_choice_children(a, b, arena, children);

    EvalNode* n = new EvalNode();
    arena.AddNode(n);
    n->letter_ = EvalNode::CHOICE_NODE;
    n->cell_ = a->cell_;
    n->children_.swap(children);
    n->points_ = 0;
    n->bound_ = 0;
    for (auto child : n->children_) {
      if (child) {
        n->bound_ = max(n->bound_, child->bound_);
      }
    }
    n->choice_mask_ = a->choice_mask_ | b->choice_mask_;
    return n;
  } else if (a->letter_ == b->letter_) {
    // two sum nodes
    vector<const EvalNode*> children = a->children_;
    children.insert(children.end(), b->children_.begin(), b->children_.end());
    sort(children.begin(), children.end(), [](const EvalNode* a, const EvalNode* b) {
      return a->cell_ < b->cell_;
    });

    EvalNode* n = new EvalNode();
    arena.AddNode(n);
    n->letter_ = a->letter_;
    n->cell_ = a->cell_;
    n->children_.swap(children);
    n->points_ = a->points_ + b->points_;
    n->bound_ = n->points_;
    for (auto child : n->children_) {
      if (child) {
        n->bound_ += child->bound_;
      }
    }
    n->choice_mask_ = a->choice_mask_ | b->choice_mask_;
    SqueezeSumNodeInPlace(n, arena, true);
    return n;
  }
  throw runtime_error("Cannot merge CHOICE_NODE with non-choice");
}


void merge_choice_collisions_in_place(
  vector<const EvalNode*>& choices,
  EvalNodeArena& arena
) {
  sort(choices.begin(), choices.end(), [](const EvalNode* a, const EvalNode* b) {
    return a->cell_ < b->cell_;
  });

  auto it = choices.begin();
  while (it != choices.end()) {
    auto next_it = std::next(it);
    while (next_it != choices.end() && (*it)->cell_ == (*next_it)->cell_) {
      *it = merge_trees(*it, *next_it, arena);
      *next_it = nullptr;  // these will be removed below
      ++next_it;
    }
    it = next_it;
  }

  // Remove null values from the choices vector.
  choices.erase(std::remove(choices.begin(), choices.end(), nullptr), choices.end());
}

// block-scope functions cannot be declared inline.
inline uint16_t advance(
  const EvalNode* node,
  vector<int>& sums,
  vector<vector<const EvalNode*>>& stacks
) {
  // assert(node->letter_ != CHOICE_NODE);
  for (auto child : node->children_) {
    // assert(child->letter_ == CHOICE_NODE);
    stacks[child->cell_].push_back(child);
    sums[child->cell_] += child->bound_;
  }
  return node->points_;
}

vector<pair<int, string>> EvalNode::OrderlyBound(
  int cutoff,
  const vector<string>& cells,
  const vector<int>& split_order,
  const vector<pair<int, int>>* preset_cells
) const {
  vector<vector<const EvalNode*>> stacks(cells.size());
  vector<pair<int, int>> choices;
  vector<int> stack_sums(cells.size(), 0);
  vector<pair<int, string>> failures;

  auto record_failure = [&](int bound) {
    string board(cells.size(), '.');
    if (preset_cells) {
      for (const auto& choice : *preset_cells) {
        board[choice.first] = cells[choice.first][choice.second];
      }
    }
    for (const auto& choice : choices) {
      board[choice.first] = cells[choice.first][choice.second];
    }
    failures.push_back({bound, board});
  };

  function<void(int, int, vector<int>&)> rec = [&](int base_points, int num_splits, vector<int>& stack_sums) {
    int bound = base_points;
    for (int i = num_splits; i < split_order.size(); ++i) {
      bound += stack_sums[split_order[i]];
    }
    if (bound <= cutoff) {
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
    // TODO: maybe make these pairs of iterators?
    vector<vector<const EvalNode *>::const_iterator> its;
    vector<vector<const EvalNode *>::const_iterator> end_its;
    its.reserve(next_stack.size());
    end_its.reserve(next_stack.size());
    for (auto& n : next_stack) {
      // assert(n->letter_ == CHOICE_NODE);
      // assert(n->cell_ == next_to_split);
      its.push_back(n->children_.begin());
      end_its.push_back(n->children_.end());
    }

    int num_letters = cells[next_to_split].size();
    for (int letter = 0; letter < num_letters; ++letter) {
      if (letter > 0) {
        // TODO: it should be possible to avoid this copy with another stack.
        stack_sums = base_sums;
        for (int i = 0; i < stacks.size(); ++i) {
          // This will not de-allocate anything, just reduce size.
          // https://cplusplus.com/reference/vector/vector/resize/
          stacks[i].resize(stack_top[i]);
        }
      }
      choices.emplace_back(next_to_split, letter);
      int points = base_points;
      int n = its.size();
      for (int i = 0; i < n; i++) {
        auto& it = its[i];
        auto end = end_its[i];
        if (it != end && (*it)->letter_ == letter) {
          points += advance(*it, stack_sums, stacks);
          ++it;
        }
      }
      rec(points, num_splits + 1, stack_sums);
      choices.pop_back();
    }
  };

  vector<int> sums(cells.size(), 0);
  auto base_points = advance(this, sums, stacks);
  rec(base_points, 0, sums);
  return failures;
}
