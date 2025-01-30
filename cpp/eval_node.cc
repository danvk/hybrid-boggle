#include "eval_node.h"

#include <variant>
#include <vector>

using namespace std;

uint32_t cache_count = 1;

int EvalNode::NodeCount() const {
  int count = 1;
  for (int i = 0; i < children.size(); i++) {
    if (children[i]) count += children[i]->NodeCount();
  }
  return count;
}

unsigned int EvalNode::UniqueNodeCount() const {
  cache_count += 1;
  return UniqueNodeCountHelp(cache_count);
}

unsigned int EvalNode::UniqueNodeCountHelp(uint32_t mark) const {
  if (cache_key == cache_count) {
    return cache_value;
  }

  cache_key = cache_count;
  unsigned int count = 1;
  for (auto child : children) {
    if (child) {
      count += child->UniqueNodeCountHelp(mark);
    }
  }
  cache_value = count;
  return count;
}

int EvalNode::RecomputeScore() const {
  if (letter == CHOICE_NODE) {
    // Choose the max amongst each possibility.
    int max_score = 0;
    for (int i = 0; i < children.size(); i++) {
      if (children[i])
        max_score = max(max_score, children[i]->RecomputeScore());
    }
    return max_score;
  } else {
    // Add in the contributions of all neighbors.
    // (or all initial squares if this is the root node)
    int score = points;
    for (int i = 0; i < children.size(); i++) {
      if (children[i])
        score += children[i]->RecomputeScore();
    }
    return score;
  }
}

const EvalNode*
EvalNode::LiftChoice(int force_cell, int num_lets, EvalNodeArena& arena, bool dedupe, bool compress) const {
  cache_count += 1;
  if (letter == CHOICE_NODE && cell == force_cell) {
    // This is already in the right form. Nothing more to do!
    return this;
  }

  if ((this->choice_mask & (1 << force_cell)) == 0) {
    // There's no relevant choice below us, so we can bottom out.
    return this;
  }

  VectorArena vector_arena;  // goes out of scope at end of function
  auto one_or_choices = ForceCell(force_cell, num_lets, arena, vector_arena);
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
  node->letter = CHOICE_NODE;
  node->cell = force_cell;
  node->points = 0;
  node->children.swap(choices);
  node->choice_mask = 1 << force_cell;
  for (auto child : node->children) {
    if (child) {
      node->choice_mask |= child->choice_mask;
      node->bound = max(node->bound, child->bound);
    }
  }
  return node;
}

variant<const EvalNode*, vector<const EvalNode*>*>
EvalNode::ForceCell(int force_cell, int num_lets, EvalNodeArena& arena, VectorArena& vector_arena) const {
  cache_count += 1;
  auto out = ForceCellWork(force_cell, num_lets, arena, vector_arena);
  return out;
}

variant<const EvalNode*, vector<const EvalNode*>*>
EvalNode::ForceCellWork(int force_cell, int num_lets, EvalNodeArena& arena, VectorArena& vector_arena) const {
  if (cache_key == cache_count) {
    uintptr_t v = cache_value;
    if (v & 1) {
      // it's a vector
      v -= 1;
      return {(vector<const EvalNode*>*)v};
    } else {
      return {(const EvalNode*)v};
    }
  }

  if (letter == EvalNode::CHOICE_NODE && cell == force_cell) {
    // This is the forced cell.
    // We've already tried each possibility, but they may not be aligned.
    auto out = new vector<const EvalNode*>;
    out->resize(num_lets);
    for (int i = 0; i < num_lets; i++) {
      out->at(i) = NULL;
    }
    for (auto child : children) {
      // TODO: is this "if" necessary?
      // if (child) {
      auto let = child->letter;
      if (child->points == 0 && child->children.size() == 1) {
        child = child->children[0];
      }
      out->at(let) = child;
      // assert(child.choice_mask & (1 << force_cell) == 0);
      // TODO: Python has: assert child.choice_mask & (1 << force_cell) == 0
      // }
    }
    cache_key = cache_count;
    cache_value = ((uintptr_t)out) + 1;
    return {out};
  }

  if ((choice_mask & (1 << force_cell)) == 0) {
    // There's no relevant choice below us, so we can bottom out.
    cache_key = cache_count;
    cache_value = (uintptr_t)this;
    return {this};
  }

  vector<variant<const EvalNode*, vector<const EvalNode*>*>> results;
  results.reserve(children.size());
  for (auto child : children) {
    if (child) {
      results.push_back(child->ForceCellWork(force_cell, num_lets, arena, vector_arena));
    } else {
      // TODO: can this happen?
      results.push_back({(EvalNode*)NULL});
    }
  }

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
    vector<const EvalNode*> node_children;
    for (auto &result : aligned_results) {
      if (result[i]) {
        node_children.push_back(result[i]);
      }
    }
    uint16_t node_choice_mask = 0;
    unsigned int node_bound = 0;
    if (letter == CHOICE_NODE) {
      for (auto child : node_children) {
        node_bound = std::max(node_bound, child->bound);
      }
      node_choice_mask = (1 << cell) & choice_mask;
    } else {
      node_bound = points;
      for (auto child : node_children) {
        node_bound += child->bound;
      }
    }
    EvalNode* node = NULL;
    if (node_bound) {
      node = new EvalNode;
      arena.AddNode(node);
      node->letter = letter;
      node->points = points;
      node->cell = cell;
      node->bound = node_bound;
      node->children.swap(node_children);
      node->choice_mask = node_choice_mask;
      for (auto child : node->children) {
        node->choice_mask |= child->choice_mask;
      }
      if (letter == ROOT_NODE) {
        // It would be nice to leave this as a ROOT_NODE to simplify finding the
        // edge of the max root tree vs. the eval tree.
        node->letter = i;
        node->cell = force_cell;
      }
    }
    out->push_back(node);
  }

  cache_key = cache_count;
  cache_value = ((uintptr_t)out) + 1;
  return out;
}

unsigned int EvalNode::ScoreWithForces(const vector<int>& forces, const vector<string>& cells) const {
  uint16_t force_choice_mask = 0;
  for (int i = 0; i < forces.size(); i++) {
    if (forces[i] >= 0) {
      force_choice_mask |= (1 << i);
    }
  }
  vector<int> num_letters;
  num_letters.reserve(cells.size());
  for (auto cell : cells) {
    num_letters.push_back(cell.size());
  }
  return ScoreWithForcesMask(forces, force_choice_mask, num_letters);
}

unsigned int EvalNode::ScoreWithForcesMask(const vector<int>& forces, uint16_t force_choice_mask, const vector<int>& num_letters) const {
  if (letter == CHOICE_NODE) {
    auto force = forces[cell];
    if (force >= 0) {
      int v = 0;
      if (children.size() == num_letters[cell]) {
        // dense
        auto child = children[force];
        if (child) {
          v = child->ScoreWithForcesMask(forces, force_choice_mask, num_letters);
        }
      } else {
        // sparse
        for (const auto& child : children) {
          if (child && child->letter == force) {
            v = child->ScoreWithForcesMask(forces, force_choice_mask, num_letters);
            break;
          }
        }
      }
      return v;
    }
  }

  if (!(choice_mask & force_choice_mask)) {
    // The force is irrelevant to this subtree, so we don't need to traverse it.
    return bound;
  }

  // Otherwise, this is the same as regular scoring
  if (letter == CHOICE_NODE) {
    unsigned int score = 0;
    for (const auto& child : children) {
      if (child) {
        score = std::max(score, child->ScoreWithForcesMask(forces, force_choice_mask, num_letters));
      }
    }
    return score;
  } else {
    unsigned int score = points;
    for (const auto& child : children) {
      if (child) {
        score += child->ScoreWithForcesMask(forces, force_choice_mask, num_letters);
      }
    }
    return score;
  }
}

void EvalNode::FilterBelowThreshold(int min_score) {
  if (letter != CHOICE_NODE) {
    return;
  }
  for (int i = 0; i < children.size(); i++) {
    auto child = children[i];
    if (!child) {
      continue;
    }
    if (child->bound <= min_score) {
      children[i] = NULL;
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
  if (letter != CHOICE_NODE) {
    out.push_back({this, path});
  } else {
    for (int i = 0; i < children.size(); i++) {
      auto child = children[i];
      if (child) {
        vector<pair<int, int>> new_path(path);
        new_path.push_back({cell, i});
        child->MaxSubtreesHelp(out, new_path);
      }
    }
  }
}

unique_ptr<EvalNodeArena> create_eval_node_arena() {
  return unique_ptr<EvalNodeArena>(new EvalNodeArena);
}

unique_ptr<VectorArena> create_vector_arena() {
  return unique_ptr<VectorArena>(new VectorArena);
}
