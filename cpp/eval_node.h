#ifndef EVAL_NODE_H
#define EVAL_NODE_H

#include <limits.h>
#include <map>
#include <vector>

// TODO: clean up memory after ForceCell
#define LEAK_LIKE_A_SIEVE true

class EvalNode {
 public:
  EvalNode() {}
  ~EvalNode() {
    for (int i = 0; i < children.size(); i++) {
      if (!LEAK_LIKE_A_SIEVE) {
        if (children[i]) delete children[i];
      }
    }
  }

  std::variant<const EvalNode*, std::vector<const EvalNode*>> ForceCell(int cell, int num_lets) const;

  // Must have forces.size() == M * N; set forces[i] = -1 to not force a cell.
  unsigned int ScoreWithForces(const std::vector<int>& forces) const;

  char letter;
  char cell;
  static const char ROOT_NODE = -2;
  static const char CHOICE_NODE = -1;

  // These might be the various options on a cell or the various directions.
  std::vector<const EvalNode*> children;

  // cached computation across all children
  unsigned int bound;

  // points contributed by _this_ node.
  unsigned int points;

  uint16_t choice_mask;

  int RecomputeScore() const;
  int NodeCount() const;

 private:
  unsigned int ScoreWithForcesMask(const std::vector<int>& forces, uint16_t choice_mask) const;
};

#endif  // EVAL_NODE_H
