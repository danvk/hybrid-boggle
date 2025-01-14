// At one point I thought that sending EvalNode between C++ and Python was a bottleneck.
// This C++ implementation of the Breaker proved that was not the case.

#include "tree_builder.h"
#include <utility>
#ifndef BREAKER_H
#define BREAKER_H

using std::string;
using std::vector;
using std::pair;

class Breaker {
 public:
  Breaker(TreeBuilder<3, 4>* etb, unsigned int best_score) : etb_(etb), best_score_(best_score) {}

  bool SetBoard(char* board) {
    return etb_->ParseBoard(board);
  }

  std::unordered_map<int, int> Break() {
    by_level_.clear();
    elim_level_.clear();
    cells_.clear();
    for (int i = 0; i < etb_->NumCells(); i++) {
      cells_.push_back(etb_->bd_[i]);
      std::cout << i << " " << cells_[i] << std::endl;
    }
    auto tree = etb_->BuildTree();
    std::cout << "num nodes: " << tree->NodeCount() << std::endl;

    string choices;
    for (int i = 0; i < etb_->NumCells(); i++) {
      choices.append(" ");
    }
    std::cout << "initial choices: " << choices << std::endl;
    AttackTree(tree.get(), 0, choices);

    return by_level_;
  }

  int PickABucket(const EvalNode* tree) {
    auto choice_mask = tree->choice_mask;
    for (auto order : SPLIT_ORDER) {
      if (choice_mask & (1 << order)) {
        return order;
      }
    }
    // std::cout << "pick: " << choice_mask << " " << pick << std::endl;
    return -1;
  }

  void SplitBucket(const EvalNode* tree, int level, string& choices) {
    auto cell = PickABucket(tree);
    if (cell == -1) {
      // it's just a board
      string board;
      for (auto c : choices) {
        board += c;
      }
      std::cout << "Unable to break board " << board << std::endl;
      return;
    }

    int n = cells_[cell].length();
    auto trees = tree->ForceCell(cell, n);

    vector<pair<char, const EvalNode*>> tagged_trees;
    if (std::holds_alternative<const EvalNode*>(trees)) {
      std::cout << "choice was not really a choice" << std::endl;
      auto t1 = std::get<const EvalNode*>(trees);
      tagged_trees.push_back(pair<char, const EvalNode*>('*', t1));
    } else {
      auto ts = std::get<vector<const EvalNode*>>(trees);
      // assert len(trees) == n
      for (int i = 0; i < ts.size(); i++) {
        tagged_trees.push_back(pair<char, const EvalNode*>(cells_[cell][i], ts[i]));
      }
    }

    for (const auto& p : tagged_trees) {
      auto letter = p.first;
      auto tree = p.second;
      choices[cell] = letter;
      AttackTree(tree, level + 1, choices);
    }
    choices[cell] = ' ';
  }

  void AttackTree(const EvalNode* tree, int level, string& choices) {
    by_level_[level] += 1;
    auto ub = tree->bound;
    if (ub <= best_score_) {
      elim_level_[level] += 1;
    } else {
      SplitBucket(tree, level, choices);
    }
  }

 private:
  TreeBuilder<3, 4>* etb_;
  unsigned int best_score_;
  std::unordered_map<int, int> by_level_;
  std::unordered_map<int, int> elim_level_;
  vector<string> cells_;

  static const int SPLIT_ORDER[12];
};

const int Breaker::SPLIT_ORDER[12] = {5, 6, 1, 9, 2, 10, 4, 7, 0, 8, 3, 11};

#endif // BREAKER_H
