#include "eval_node.h"

#include <variant>
#include <vector>

using std::vector;
using std::variant;

int EvalNode::NodeCount() const {
  int count = 1;
  for (int i = 0; i < children.size(); i++) {
    if (children[i]) count += children[i]->NodeCount();
  }
  return count;
}

int EvalNode::RecomputeScore() const {
  if (letter == CHOICE_NODE) {
    // Choose the max amongst each possibility.
    int max_score = 0;
    for (int i = 0; i < children.size(); i++) {
      if (children[i])
        max_score = std::max(max_score, children[i]->RecomputeScore());
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

variant<const EvalNode*, vector<const EvalNode*>>
EvalNode::ForceCell(int force_cell, int num_lets) const {
  if (letter == EvalNode::CHOICE_NODE && cell == force_cell) {
    // This is the forced cell.
    // We've already tried each possibility, but they may not be aligned.
    vector<const EvalNode*> out;
    out.resize(num_lets);
    for (int i = 0; i < num_lets; i++) {
        out[i] = NULL;
    }
    for (auto child : children) {
        // TODO: is this "if" necessary?
        // if (child) {
        auto letter = child->letter;
        if (child->points == 0 && child->children.size() == 1) {
            child = child->children[0];
        }
        out[letter] = child;
        // TODO: Python has: assert child.choice_mask & (1 << force_cell) == 0
        // }
    }
    return {out};
  }

  if ((choice_mask & (1 << force_cell)) == 0) {
    // There's no relevant choice below us, so we can bottom out.
    return {this};
  }

  vector<variant<const EvalNode*, vector<const EvalNode*>>> results;
  results.reserve(children.size());
  for (auto child : children) {
    if (child) {
        results.push_back(child->ForceCell(force_cell, num_lets));
    } else {
        // TODO: can this happen?
        results.push_back({(EvalNode*)NULL});
    }
  }

  vector<vector<const EvalNode*>> aligned_results;
  aligned_results.reserve(results.size());
  for (int i = 0; i < results.size(); i++) {
    auto &r = results[i];
    if (std::holds_alternative<const EvalNode*>(r)) {
        auto r1 = std::get<const EvalNode*>(r);
        vector<const EvalNode*> me;
        me.reserve(num_lets);
        for (int j = 0; j < num_lets; j++) {
            me.push_back(r1);
        }
        aligned_results.push_back(std::move(me));
    } else {
        aligned_results.push_back(std::move(std::get<vector<const EvalNode*>>(r)));
    }
  }

  vector<const EvalNode*> out;
  out.reserve(num_lets);
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
        node->letter = letter;
        node->points = points;
        node->cell = cell;
        node->bound = node_bound;
        node->children.swap(node_children);
        node->choice_mask = node_choice_mask;
        for (auto child : node->children) {
            node->choice_mask |= child->choice_mask;
        }
    }
    out.push_back(node);
  }
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

unsigned int EvalNode::ScoreWithForcesMask(const vector<int>& forces, uint16_t force_choice_mask) const {
    if (letter == CHOICE_NODE) {
        auto force = forces[cell];
        if (force >= 0) {
            for (const auto& child : children) {
                if (child->letter == force) {
                    return child->ScoreWithForcesMask(forces, force_choice_mask);
                }
            }
            return 0;
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
            score = std::max(score, child->ScoreWithForcesMask(forces, force_choice_mask));
        }
        return score;
    } else {
        unsigned int score = points;
        for (const auto& child : children) {
            score += child->ScoreWithForcesMask(forces, force_choice_mask);
        }
        return score;
    }
}
