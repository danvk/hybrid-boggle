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
    cout << "sizeof(T)=" << sizeof(T) << endl;
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

  void AddNode(T* node) {
    // for (auto n : owned_nodes_) {
    //   if (n == node) {
    //     cout << "Double add!" << endl;
    //   }
    // }
    owned_nodes_.push_back(node);
  }

  // For testing
  T* NewNode();

  // Returns the number of nodes deleted
  int MarkAndSweep(T* root, uint32_t mark);

  // friend EvalNode;

 private:
  vector<T*> owned_nodes_;
};

typedef Arena<EvalNode> EvalNodeArena;

unique_ptr<EvalNodeArena> create_eval_node_arena();

class EvalNode {
 public:
  EvalNode() : points_(0) {}
  virtual ~EvalNode() {}

  void AddWord(vector<pair<int, int>> choices, int points, EvalNodeArena& arena);
  void AddWordWork(int num_choices, pair<int, int>* choices, const int* num_letters, int points, EvalNodeArena& arena);

  bool StructuralEq(const EvalNode& other) const;
  void PrintJSON() const;

  int8_t letter_;
  int8_t cell_;

  // points contributed by _this_ node.
  uint16_t points_;

  static const int8_t ROOT_NODE = -2;
  static const int8_t CHOICE_NODE = -1;

  // These might be the various options on a cell or the various directions.
  // TODO: the "const" here is increasingly a joke.
  vector<const EvalNode*> children_;

  // cached computation across all children
  uint32_t bound_;

  int NodeCount() const;

  vector<pair<int, string>> OrderlyBound(
    int cutoff,
    const vector<string>& cells,
    const vector<int>& split_order
  ) const;

};

#endif  // EVAL_NODE_H
