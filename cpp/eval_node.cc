#include "eval_node.h"

#include <bit>
#include <functional>
#include <limits>
#include <variant>
#include <vector>

using namespace std;


template<>
uint32_t Arena<EvalNode>::NewNode() {
  // TODO: allocate & free a million at once
  int n = owned_nodes_.size();
  owned_nodes_.push_back(new EvalNode);
  return n;
}

void EvalNode::AddWordWork(int num_choices, pair<int, int>* choices, const int* num_letters, int points, EvalNodeArena& arena) {
  if (!num_choices) {
    points_ += points;
    bound_ += points;
    return;
  }

  auto cell = choices->first;
  auto letter = choices->second;
  choices++;
  num_choices--;

  EvalNode* choice_child = NULL;
  for (auto c_id : children_) {
    auto c = arena.at(c_id);
    if (c->cell_ == cell) {
      choice_child = c;
      break;
    }
  }
  int old_choice_bound = 0;
  if (!choice_child) {
    auto choice_child_id = arena.NewNode();
    choice_child = arena.at(choice_child_id);
    choice_child->letter_ = CHOICE_NODE;
    choice_child->cell_ = cell;
    choice_child->bound_ = 0;
    children_.push_back(choice_child_id);
  } else {
    old_choice_bound = choice_child->bound_;
  }

  EvalNode* letter_child = NULL;
  for (auto c_id : choice_child->children_) {
    auto c = arena.at(c_id);

    if (c->letter_ == letter) {
      letter_child = c;
      break;
    }
  }
  if (!letter_child) {
    auto letter_child_id = arena.NewNode();
    letter_child = arena.at(letter_child_id);
    letter_child = new EvalNode;
    letter_child->cell_ = cell;
    letter_child->letter_ = letter;
    letter_child->bound_ = 0;
    choice_child->children_.push_back(letter_child_id);
    sort(choice_child->children_.begin(), choice_child->children_.end(), [&](int32_t aid, int32_t bid) {
      auto a = arena.at(aid);
      auto b = arena.at(bid);
      return a->letter_ < b->letter_;
    });
  }
  letter_child->AddWordWork(num_choices, choices, num_letters, points, arena);

  if (letter_child->bound_ > old_choice_bound) {
    choice_child->bound_ = letter_child->bound_;
  }
  bound_ += (choice_child->bound_ - old_choice_bound);
}

void EvalNode::AddWord(vector<pair<int, int>> choices, int points, EvalNodeArena& arena) {
  vector<int> num_letters(choices.size(), 1);
  AddWordWork(choices.size(), choices.data(), num_letters.data(), points, arena);
}

int EvalNode::NodeCount(EvalNodeArena& arena) const {
  int count = 1;
  for (int i = 0; i < children_.size(); i++) {
    auto c = arena.at(children_[i]);
    if (c) count += c->NodeCount(arena);
  }
  return count;
}


unique_ptr<EvalNodeArena> create_eval_node_arena() {
  return unique_ptr<EvalNodeArena>(new EvalNodeArena);
}

vector<pair<int, string>> EvalNode::OrderlyBound(
  int cutoff,
  const vector<string>& cells,
  const vector<int>& split_order,
  EvalNodeArena& arena
) const {
  vector<vector<const EvalNode*>> stacks(cells.size());
  vector<pair<int, int>> choices;
  vector<int> stack_sums(cells.size(), 0);
  vector<pair<int, string>> failures;

  auto advance = [&](const EvalNode* node, vector<int>& sums) {
    assert(node->letter_ != CHOICE_NODE);
    for (auto cid : node->children_) {
      auto child = arena.at(cid);
      assert(child->letter_ == CHOICE_NODE);
      stacks[child->cell_].push_back(child);
      sums[child->cell_] += child->bound_;
    }
    return node->points_;
  };

  auto record_failure = [&](int bound) {
    string board(cells.size(), '.');
    for (const auto& choice : choices) {
      board[choice.first] = cells[choice.first][choice.second];
    }
    failures.push_back({bound, board});
  };

  function<void(int, int, vector<int>&)> rec = [&](int base_points, int num_splits, vector<int>& stack_sums) {
    int bound = base_points;
    for (int i = num_splits; i < split_order.size(); ++i) {
      bound += stack_sums[split_order[i]];
    }
    if (bound <= cutoff) {
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

    for (int letter = 0; letter < cells[next_to_split].size(); ++letter) {
      if (letter > 0) {
        stack_sums = base_sums;
        for (int i = 0; i < stacks.size(); ++i) {
          // TODO: don't do this, just leave garbage on the end.
          stacks[i].resize(stack_top[i]);
        }
      }
      choices.emplace_back(next_to_split, letter);
      int points = base_points;
      for (auto node : stacks[next_to_split]) {
        const EvalNode* letter_node = nullptr;
        for (auto nid : node->children_) {
          auto n = arena.at(nid);
          if (n->letter_ == letter) {
            letter_node = n;
            break;
          }
        }
        if (letter_node) {
          points += advance(letter_node, stack_sums);
        }
      }
      rec(points, num_splits + 1, stack_sums);
      choices.pop_back();
    }
  };

  vector<int> sums(cells.size(), 0);
  assert(advance(this, sums) == 0);
  rec(0, 0, sums);
  return failures;
}
