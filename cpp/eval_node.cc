#include "eval_node.h"

#include <bit>
#include <functional>
#include <limits>
#include <variant>
#include <vector>

using namespace std;

uint32_t cache_count = 1;
unordered_map<uint64_t, const EvalNode*> force_cell_cache;
uint64_t hash_collisions = 0;

const EvalNode* SqueezeChoiceChild(const EvalNode* child);
bool SqueezeSumNodeInPlace(EvalNode* node);

inline void IncrementCacheCount() {
  cache_count += 1;
  if (cache_count == 0) {
    // TODO: reset the marks in the eval tree here
    cout << "Overflow!" << endl;
    exit(1);
  }
}

int EvalNode::NodeCount() const {
  int count = 1;
  for (int i = 0; i < children_.size(); i++) {
    if (children_[i]) count += children_[i]->NodeCount();
  }
  return count;
}

unsigned int EvalNode::UniqueNodeCount() const {
  IncrementCacheCount();
  return UniqueNodeCountHelp(cache_count);
}

unsigned int EvalNode::UniqueNodeCountHelp(uint32_t mark) const {
  if (cache_key_ == cache_count) {
    return 0;
  }

  cache_key_ = cache_count;
  unsigned int count = 1;
  for (auto child : children_) {
    if (child) {
      count += child->UniqueNodeCountHelp(mark);
    }
  }
  return count;
}

uint32_t EvalNode::MarkAll() {
  IncrementCacheCount();
  MarkAllWith(cache_count);
  return cache_count;
}

void EvalNode::MarkAllWith(uint32_t mark) {
  cache_key_ = mark;
  for (auto c : children_) {
    if (c) {
      ((EvalNode*)c)->MarkAllWith(mark);
    }
  }
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
EvalNode::LiftChoice(int cell, int num_lets, EvalNodeArena& arena, bool dedupe, bool compress) const {
  IncrementCacheCount();
  if (letter_ == CHOICE_NODE && cell_ == cell) {
    // This is already in the right form. Nothing more to do!
    return this;
  }

  if ((choice_mask_ & (1 << cell)) == 0) {
    // There's no relevant choice below us, so we can bottom out.
    return this;
  }

  hash_collisions = 0;
  VectorArena vector_arena;  // goes out of scope at end of function
  auto one_or_choices = ForceCell(cell, num_lets, arena, vector_arena, dedupe, compress);
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
EvalNode::ForceCell(int cell, int num_lets, EvalNodeArena& arena, VectorArena& vector_arena, bool dedupe, bool compress) const {
  IncrementCacheCount();
  force_cell_cache.clear();
  auto out = ForceCellWork(cell, num_lets, arena, vector_arena, dedupe, compress);
  force_cell_cache.clear();
  return out;
}

variant<const EvalNode*, vector<const EvalNode*>*>
EvalNode::ForceCellWork(int cell, int num_lets, EvalNodeArena& arena, VectorArena& vector_arena, bool dedupe, bool compress) const {
  if (cache_key_ == cache_count) {
    uintptr_t v = cache_value_;
    if (v & 1) {
      // it's a vector
      v -= 1;
      return {(vector<const EvalNode*>*)v};
    } else {
      return {(const EvalNode*)v};
    }
  }

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
    cache_key_ = cache_count;
    cache_value_ = ((uintptr_t)out) + 1;
    return {out};
  }

  if ((choice_mask_ & (1 << cell)) == 0) {
    // There's no relevant choice below us, so we can bottom out.
    cache_key_ = cache_count;
    cache_value_ = (uintptr_t)this;
    return {this};
  }

  vector<variant<const EvalNode*, vector<const EvalNode*>*>> results;
  results.reserve(children_.size());
  for (auto child : children_) {
    if (child) {
      results.push_back(child->ForceCellWork(cell, num_lets, arena, vector_arena, dedupe, compress));
    } else {
      // TODO: can this happen? (evidently not)
      results.push_back({(EvalNode*)NULL});
    }
  }

  // TODO: is it necessary to construct this matrix explicitly?
  vector<vector<const EvalNode*>> aligned_results;
  aligned_results.reserve(results.size());
  for (int i = 0; i < results.size(); i++) {
    auto &r = results[i];
    if (holds_alternative<const EvalNode*>(r)) {
      auto r1 = std::get<const EvalNode*>(r);
      vector<const EvalNode*> me;
      me.reserve(num_lets);
      for (int j = 0; j < num_lets; j++) {
        me.push_back(r1);
      }
      aligned_results.push_back(std::move(me));
    } else {
      auto rn = std::get<vector<const EvalNode*>*>(r);
      aligned_results.push_back(*rn);
    }
  }

  auto out = new vector<const EvalNode*>;
  vector_arena.AddNode(out);
  out->reserve(num_lets);
  for (int i = 0; i < num_lets; i++) {
    vector<const EvalNode*> children;
    for (auto &result : aligned_results) {
      children.push_back(result[i]);
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
            hash_collisions++;
          }
        }
      }

      if (!out_node) {
        arena.AddNode(node);
        out_node = node;
        bool any_changes = false;
        if (compress && node->letter_ != CHOICE_NODE) {
          any_changes = SqueezeSumNodeInPlace(node);
        }
        if (dedupe) {
          force_cell_cache[h] = node;
          if (any_changes) {
            // TODO: check whether both hashes are necessary / helpful
            force_cell_cache[node->StructuralHash()] = node;
          }
        }
      }
    }
    out->push_back(out_node);
  }

  cache_key_ = cache_count;
  cache_value_ = ((uintptr_t)out) + 1;
  return out;
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

void EvalNode::FilterBelowThreshold(int min_score) {
  if (letter_ != CHOICE_NODE) {
    return;
  }
  for (int i = 0; i < children_.size(); i++) {
    auto child = children_[i];
    if (!child) {
      continue;
    }
    if (child->bound_ <= min_score) {
      children_[i] = NULL;
    } else {
      // This casts away the const-ness.
      ((EvalNode*)child)->FilterBelowThreshold(min_score);
    }
  }
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
  if (hash_) {
    return hash_;
  }
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
  hash_ = h;
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

// Absorb non-choice nodes into this sum node. Operates in-place.
// Returns a boolean indicating whether any changes were made.
bool SqueezeSumNodeInPlace(EvalNode* node) {
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
  if (!any_sum_children) {
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

  // There's something to absorb.
  // TODO: pre-reserve the right number of slots for new_children
  auto& new_children = choice;
  for (auto c : non_choice) {
    node->points_ += c->points_;
    // TODO: find vector method for appending one vector to another
    for (auto cc : c->children_) {
      new_children.push_back(cc);
    }
  }
  node->children_.swap(new_children);
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
    for (int cell = 0; cell < choices.size(); cell++) {
      auto idx = choices[cell];
      board[cell] = cells[cell][idx];
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

template<typename T>
void Arena<T>::MarkAndSweep(T* root) {
  cerr << "MarkAndSweep not implemented" << endl;
  exit(1);
}

template <>
void Arena<EvalNode>::MarkAndSweep(EvalNode* root) {
  uint32_t mark = root->MarkAll();
  // int num_deleted = 0;
  for (auto& node : owned_nodes_) {
    if (node->cache_key_ != mark) {
      delete node;
      node = NULL;
      // num_deleted++;
    }
  }

  // auto old_size = owned_nodes_.size();
  // TODO: this could be done in one pass by folding this into the for loop above.
  auto new_end = std::remove(owned_nodes_.begin(), owned_nodes_.end(), nullptr);
  owned_nodes_.erase(new_end, owned_nodes_.end());

  // cout << "Deleted " << num_deleted << " nodes, " << old_size << " -> " << owned_nodes_.size() << endl;
}
