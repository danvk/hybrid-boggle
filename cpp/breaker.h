#ifndef BREAKER_H
#define BREAKER_H

#include "arena.h"
#include "board_class_boggler.h"
#include "boggler.h"
#include "orderly_tree_builder.h"

using namespace std;

template <int M, int N>
class HybridTreeBreaker {
 public:
  HybridTreeBreaker(
      OrderlyTreeBuilder<M, N>& etb,
      Boggler<M, N>& boggler,
      int best_score,
      int switchover_score
  )
      : etb_(etb),
        boggler_(boggler),
        best_score_(best_score),
        switchover_score_(switchover_score),
        switchover_depth_(M * N - 4) {}

  bool SetBoard(string board) {
    auto result = etb_.ParseBoard(board.c_str());
    cells_.resize(M * N);
    for (int i = 0; i < M * N; i++) {
      cells_[i] = string(etb_.bd_[i]);
    }
    return result;
  }

  void Break() {
    for (int i = 0; i < M * N; i++) {
      num_letters_[i] = cells_[i].size();
    }
    failures_.clear();
    n_force_ = 0;
    n_bound_ = 0;
    n_test_ = 0;

    auto arena = etb_.CreateArena();
    auto tree = etb_.BuildTree(*arena);
    auto num_nodes = arena->NumNodes();
    cout << "init_nodes: " << num_nodes << ", init_bytes=" << arena->BytesAllocated()
         << endl;
    vector<pair<int, int>> choices;
    AttackTree(*tree, 1, choices, *arena);

    cout << "total_nodes: " << arena->NumNodes()
         << ", total_bytes=" << arena->BytesAllocated() << endl;
  }

  void AttackTree(
      SumNode& tree, int level, vector<pair<int, int>>& choices, EvalNodeArena& arena
  ) {
    if (tree.bound_ < best_score_) {
      // eliminated
    } else if (tree.bound_ <= switchover_score_ || level > switchover_depth_) {
      SwitchToScore(tree, level, choices);
    } else {
      ForceAndFilter(tree, level, choices, arena);
    }
  }

  void ForceAndFilter(
      SumNode& tree, int level, vector<pair<int, int>>& choices, EvalNodeArena& arena
  ) {
    auto cell = BucketBoggler<M, N>::SPLIT_ORDER[choices.size()];
    auto num_lets = cells_[cell].size();
    n_force_ += 1;
    auto arena_level = arena.SaveLevel();
    auto trees = tree.OrderlyForceCell(cell, num_lets, arena);

    assert(trees.size() == num_lets);
    choices.push_back({0, 0});
    for (int letter = 0; letter < num_lets; letter++) {
      auto t = trees[letter];
      if (!t) {
        continue;  // this can happen on truly dead-end paths
      }
      *choices.rbegin() = {cell, letter};
      AttackTree(*t, level + 1, choices, arena);
    }
    choices.pop_back();
    arena.ResetLevel(arena_level);
  }

  void SwitchToScore(SumNode& tree, int level, vector<pair<int, int>>& choices) {
    n_bound_ += 1;
    vector<int> remaining_cells;
    for (int i = choices.size(); i < M * N; i++) {
      remaining_cells.push_back(BucketBoggler<M, N>::SPLIT_ORDER[i]);
    }
    auto score_boards =
        tree.OrderlyBound(best_score_, cells_, remaining_cells, choices);
    n_test_ += score_boards.size();
    for (auto& [_score, board] : score_boards) {
      auto true_score = boggler_.Score(board.c_str());
      if (true_score >= best_score_) {
        cout << "Unable to break board " << board << " " << true_score << endl;
        failures_.push_back(string(board));
      }
    }
  }

 private:
  OrderlyTreeBuilder<M, N>& etb_;
  Boggler<M, N>& boggler_;
  int best_score_;
  int switchover_score_;
  int switchover_depth_;
  int num_letters_[M * N];

  vector<string> cells_;
  int n_force_;
  int n_bound_;
  int n_test_;
  vector<string> failures_;
};

#endif  // BREAKER_H
