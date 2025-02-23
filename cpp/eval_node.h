#ifndef EVAL_NODE_H
#define EVAL_NODE_H

#include <limits.h>
#include <iostream>
#include <map>
#include <memory>
#include <unordered_map>
#include <variant>
#include <vector>
#include <cassert>

using namespace std;

class EvalNode;

template<typename T>
class Arena {
 public:
  Arena() {
    // cout << "sizeof(T)=" << sizeof(T) << endl;
  }
  ~Arena() {
    FreeTheChildren();
  }

  void FreeTheChildren() {
    // cout << "Freeing " << owned_nodes.size() << " nodes" << endl;
    for (auto node : owned_nodes_) {
      // cout << "Freeing " << node << endl;
      delete node;
      // cout << "(done)" << endl;
    }
    owned_nodes_.clear();
  }

  int NumNodes() {
    return owned_nodes_.size();
  }

  // TODO: return a pair?
  uint32_t NewNode() {
    // TODO: allocate & free a million at once
    int n = owned_nodes_.size();
    owned_nodes_.push_back(new EvalNode);
    return n;
  }

  inline T* at(uint32_t n) {
    return owned_nodes_[n];
  }
  // friend EvalNode;

 private:
  vector<T*> owned_nodes_;
};

typedef Arena<EvalNode> EvalNodeArena;

unique_ptr<EvalNodeArena> create_eval_node_arena();

class EvalNode {
 public:
  EvalNode() : points_(0) {}

  void AddWord(vector<pair<int, int>> choices, int points, EvalNodeArena& arena);
  void AddWordWork(int num_choices, pair<int, int>* choices, const int* num_letters, int points, EvalNodeArena& arena);

  int8_t letter_;
  int8_t cell_;

  // points contributed by _this_ node.
  uint16_t points_;

  // cached computation across all children
  uint32_t bound_;

  static const int8_t ROOT_NODE = -2;
  static const int8_t CHOICE_NODE = -1;

  // These might be the various options on a cell or the various directions.
  vector<uint32_t> children_;

  int NodeCount(EvalNodeArena& arena) const;

  vector<pair<int, string>> OrderlyBound(
    int cutoff,
    const vector<string>& cells,
    const vector<int>& split_order,
    EvalNodeArena& arena
  ) const;

};

#endif  // EVAL_NODE_H
