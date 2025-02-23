#include "eval_node.h"

#include <bit>
#include <functional>
#include <limits>
#include <variant>
#include <vector>

using namespace std;

inline bool SortByLetter(const EvalNode* a, const EvalNode* b) {
  return a->letter_ < b->letter_;
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
  for (auto c : children_) {
    if (c->cell_ == cell) {
      choice_child = (EvalNode*)c;
      break;
    }
  }
  int old_choice_bound = 0;
  if (!choice_child) {
    choice_child = new EvalNode;
    choice_child->letter_ = CHOICE_NODE;
    choice_child->cell_ = cell;
    choice_child->bound_ = 0;
    arena.AddNode(choice_child);
    children_.push_back(choice_child);
  } else {
    old_choice_bound = choice_child->bound_;
  }

  EvalNode* letter_child = NULL;
  for (auto c : choice_child->children_) {
    if (c->letter_ == letter) {
      letter_child = (EvalNode*)c;
      break;
    }
  }
  if (!letter_child) {
    letter_child = new EvalNode;
    letter_child->cell_ = cell;
    letter_child->letter_ = letter;
    letter_child->bound_ = 0;
    arena.AddNode(letter_child);
    choice_child->children_.push_back(letter_child);
    sort(choice_child->children_.begin(), choice_child->children_.end(), SortByLetter);
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

bool EvalNode::StructuralEq(const EvalNode& other) const {
  if (letter_ != other.letter_ || cell_ != other.cell_) {
    return false;
  }
  if (bound_ != other.bound_) {
    return false;
  }
  if (points_ != other.points_) {
    return false;
  }
  vector<const EvalNode*> nnc, nno;
  for (auto c : children_) {
    if (c) nnc.push_back(c);
  }
  for (auto c : other.children_) {
    if (c) nno.push_back(c);
  }
  if (nnc.size() != nno.size()) {
    return false;
  }
  for (size_t i = 0; i < nnc.size(); ++i) {
    if (!nnc[i]->StructuralEq(*nno[i])) {
      return false;
    }
  }
  return true;
}

void EvalNode::PrintJSON() const {
  cout << "{\"type\": \"";
  if (letter_ == CHOICE_NODE) {
    cout << "CHOICE";
  } else if (letter_ == ROOT_NODE) {
    cout << "ROOT";
  } else {
    cout << (int)cell_ << "=? (" << (int)letter_ << ")";
  }
  cout << "\", \"cell\": " << (int)cell_;
  cout << ", \"bound\": " << bound_;
  if (points_) {
    cout << ", \"points\": " << (int)points_;
  }
  if (!children_.empty()) {
    cout << ", \"children\": [";
    bool has_commad = false;
    for (auto c : children_) {
      if (!c) {
        continue;
      }
      if (!has_commad) {
        has_commad = true;
      } else {
        cout << ", ";
      }
      c->PrintJSON();
    }
    cout << "]";
  }
  cout << "}";
}

int EvalNode::NodeCount() const {
  int count = 1;
  for (int i = 0; i < children_.size(); i++) {
    if (children_[i]) count += children_[i]->NodeCount();
  }
  return count;
}


unique_ptr<EvalNodeArena> create_eval_node_arena() {
  return unique_ptr<EvalNodeArena>(new EvalNodeArena);
}


template<typename T>
int Arena<T>::MarkAndSweep(T* root, uint32_t mark) {
  throw new runtime_error("MarkAndSweep not implemented");
}

template <typename T>
T* Arena<T>::NewNode() {
  throw new runtime_error("not implemented");
}

template <>
EvalNode* Arena<EvalNode>::NewNode() {
  EvalNode* n = new EvalNode;
  n->letter_ = EvalNode::ROOT_NODE;
  n->cell_ = 0;
  AddNode(n);
  return n;
}

vector<pair<int, string>> EvalNode::OrderlyBound(
  int cutoff,
  const vector<string>& cells,
  const vector<int>& split_order
) const {
  vector<vector<const EvalNode*>> stacks(cells.size());
  vector<pair<int, int>> choices;
  vector<int> stack_sums(cells.size(), 0);
  vector<pair<int, string>> failures;

  auto advance = [&](const EvalNode* node, vector<int>& sums) {
    assert(node->letter_ != CHOICE_NODE);
    for (auto child : node->children_) {
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
        for (auto n : node->children_) {
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
