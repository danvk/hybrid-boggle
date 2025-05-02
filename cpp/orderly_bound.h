#ifndef ORDERLY_BOUND_H
#define ORDERLY_BOUND_H

#include "boggler.h"
#include "eval_node.h"

// block-scope functions cannot be declared inline.
inline uint16_t advance(
    const SumNode* node, vector<int>& sums, vector<vector<const ChoiceNode*>>& stacks
) {
  for (int i = 0; i < node->num_children_; i++) {
    auto child = node->children_[i];
    stacks[child->cell_].push_back(child);
    sums[child->cell_] += child->bound_;
  }
  return node->points_;
}

// The first returned vector contains (bound, board) pairs with bound > cutoff.
// The bound is equal to the multiboggle score.
// The other vectors have some metrics
// TODO: remove the other vectors, they're not filled out
template <int M, int N>
tuple<vector<pair<int, string>>, vector<int>, vector<int>> OrderlyBound(
    SumNode* base_node,
    int cutoff,
    const vector<string>& cells,
    const vector<int>& split_order,
    const vector<pair<int, int>>& preset_cells,
    Boggler<M, N>& b,
    bool use_masked_score
) {
  vector<vector<const ChoiceNode*>> stacks(cells.size());
  vector<pair<int, int>> choices;
  vector<int> stack_sums(cells.size(), 0);
  vector<pair<int, string>> failures;
  int n_preset = preset_cells.size();
  vector<int> elim_at_level(1 + cells.size() - n_preset, 0);
  vector<int> visit_at_level(1 + cells.size() - n_preset, 0);

  // Set the preset cells once
  unsigned int ok_mask = 0;
  for (auto& [cell, choice] : preset_cells) {
    b.SetCellAtIndex(cell, cells[cell][choice] - 'a');
    ok_mask |= (1 << cell);
  }

  /*
  auto any_repeats = [&]() {
    uint32_t letters = 0;
    assert(cells.size() == sizeof(b.bd_) / sizeof(b.bd_[0]));

    for (int i = 0; i < cells.size(); i++) {
      if (ok_mask & (1 << i)) {
        unsigned int c = b.bd_[i];
        auto letter = 1 << c;
        if (letters & letter) {
          return true;
        }
        letters |= letter;
      }
    }
    return false;
  };
  */

  auto record_failure = [&](int bound) {
    string board(cells.size(), '.');
    for (const auto& choice : preset_cells) {
      board[choice.first] = cells[choice.first][choice.second];
    }
    for (const auto& choice : choices) {
      board[choice.first] = cells[choice.first][choice.second];
    }
    failures.push_back({bound, board});
  };

  function<void(int, int, vector<int>&)> rec =
      [&](int base_points, int num_splits, vector<int>& stack_sums) {
        // base_points represents the points coming from words that use only the preset
        // and previously-split cells.
        // TODO: masked evaluation here… but only if there are dupes?
        // int scored_base = b.MultiScoreWithMask(~ok_mask);
        /*
        if (scored_base != base_points) {
          printf("ok_mask: %d\n", ok_mask);
          printf("board: %s\n", b.ToString().c_str());
          printf("scored_base: %d\n", scored_base);
          printf("base_points: %d\n", base_points);
          printf("num_splits: %d\n", num_splits);
          printf("split_order.size(): %zu\n", split_order.size());
          printf(
              "stack_sums[%d] = %d\n",
              split_order[num_splits],
              stack_sums[split_order[num_splits]]
          );
        }
        */
        // assert(scored_base == base_points);
        // TODO: only use this when there are repeat letters, where it could help
        if (use_masked_score) {
          // TODO: no need to pass base_points recursively if this is true
          base_points = b.ScoreWithMask(~ok_mask);
        }

        int bound = base_points;
        for (int i = num_splits; i < split_order.size(); ++i) {
          bound += stack_sums[split_order[i]];
        }
        if (bound <= cutoff) {
          // elim_at_level[num_splits] += 1;
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
        vector<pair<SumNode* const*, SumNode* const*>> its;
        its.reserve(next_stack.size());
        for (auto& n : next_stack) {
          // assert(n->letter_ == CHOICE_NODE);
          // assert(n->cell_ == next_to_split);
          its.push_back({&n->children_[0], &n->children_[n->num_children_]});
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
          b.SetCellAtIndex(next_to_split, cells[next_to_split][letter] - 'a');
          assert((ok_mask & (1 << next_to_split)) == 0);
          ok_mask ^= (1 << next_to_split);
          choices.emplace_back(next_to_split, letter);
          int points = base_points;
          for (auto& [it, end] : its) {
            if (it != end && (*it)->letter_ == letter) {
              // visit_at_level[1 + num_splits] += 1;
              points += advance(*it, stack_sums, stacks);
              ++it;
            }
          }
          rec(points, num_splits + 1, stack_sums);
          choices.pop_back();
          ok_mask ^= (1 << next_to_split);
        }
      };

  vector<int> sums(cells.size(), 0);
  // visit_at_level[0] += 1;
  auto base_points = advance(base_node, sums, stacks);
  rec(base_points, 0, sums);
  return {failures, visit_at_level, elim_at_level};
}

#endif  // ORDERLY_BOUND_H
