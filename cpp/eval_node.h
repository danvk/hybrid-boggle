#ifndef EVAL_NODE_H
#define EVAL_NODE_H

#include <limits.h>
#include <iostream>
#include <map>
#include <vector>

using namespace std;

class EvalNodeArena;

class EvalNode {
 public:
  EvalNode() {}
  virtual ~EvalNode() {}

  variant<const EvalNode*, vector<const EvalNode*>>
  ForceCell(int cell, int num_lets, EvalNodeArena& arena) const;

  // Must have forces.size() == M * N; set forces[i] = -1 to not force a cell.
  unsigned int ScoreWithForces(const vector<int>& forces) const;

  char letter;
  char cell;
  static const char ROOT_NODE = -2;
  static const char CHOICE_NODE = -1;

  // These might be the various options on a cell or the various directions.
  vector<const EvalNode*> children;

  // cached computation across all children
  unsigned int bound;

  // points contributed by _this_ node.
  unsigned int points;

  uint16_t choice_mask;

  int RecomputeScore() const;
  int NodeCount() const;

 private:
  unsigned int ScoreWithForcesMask(const vector<int>& forces, uint16_t choice_mask) const;
};

class EvalNodeArena {
 public:
  ~EvalNodeArena() {
    FreeTheChildren();
  }

  void FreeTheChildren() {
    // cout << "Freeing " << owned_nodes.size() << " nodes" << endl;
    for (auto node : owned_nodes) {
      // cout << "Freeing " << node << endl;
      delete node;
      // cout << "(done)" << endl;
    }
    owned_nodes.clear();
  }

  int NumNodes() {
    return owned_nodes.size();
  }

  void AddNode(EvalNode* node) {
    // for (auto n : owned_nodes) {
    //   if (n == node) {
    //     cout << "Double add!" << endl;
    //   }
    // }
    owned_nodes.push_back(node);
  }

  friend EvalNode;

 private:
  vector<EvalNode*> owned_nodes;
};

unique_ptr<EvalNodeArena> create_eval_node_arena();

#endif  // EVAL_NODE_H
