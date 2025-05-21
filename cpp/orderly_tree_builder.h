#ifndef ORDERLY_TREE_BUILDER_H
#define ORDERLY_TREE_BUILDER_H

#include "eval_node.h"
#include "ibuckets.h"

using namespace std;

// TODO: templating on M, N probably isn't helpful, either.
template <int M, int N>
class OrderlyTreeBuilder : public BoardClassBoggler<M, N> {
 public:
  OrderlyTreeBuilder(Trie* t) : BoardClassBoggler<M, N>(t) {
    for (int i = 0; i < M * N; i++) {
      cell_to_order_[BucketBoggler<M, N>::SPLIT_ORDER[i]] = i;
    }
    used_ordered_ = 0;
  }
  virtual ~OrderlyTreeBuilder() {}

  // These are "dependent names", see
  // https://stackoverflow.com/a/1528010/388951.
  using BoardClassBoggler<M, N>::dict_;
  using BoardClassBoggler<M, N>::bd_;
  using BoardClassBoggler<M, N>::used_;

  /** Build an EvalTree for the current board. */
  const SumNode* BuildTree(EvalNodeArena& arena);

  unique_ptr<EvalNodeArena> CreateArena() { return create_eval_node_arena(); }

  int SumUnion() const { return 0; }

 private:
  SumNode* root_;
  int cell_to_order_[M * N];
  unsigned int used_ordered_;  // used cells mapped to their split order
  int choices_[M * N];         // cell order -> letter index
  int num_letters_[M * N];
  int num_dupes_;

  static const int shift_ = 64 - M * N;
  int letter_counts_[26];  // TODO: don't need the count here, a 52-bit mask would work
  uint32_t dupe_mask_;
  vector<unordered_set<uint64_t>*> found_words_;
  vector<vector<uint32_t>> word_lists_;
  unsigned int num_overflow_;

  void DoAllDescents(int cell, int n, int length, Trie* t, EvalNodeArena& arena);
  void DoDFS(int cell, int n, int length, Trie* t, EvalNodeArena& arena);
  bool CheckForDupe(Trie* t);
};

template <int M, int N>
const SumNode* OrderlyTreeBuilder<M, N>::BuildTree(EvalNodeArena& arena) {
  // auto start = chrono::high_resolution_clock::now();
  // cout << "alignment_of<EvalNode>=" << alignment_of<EvalNode>() << endl;
  root_ = arena.NewRootNodeWithCapacity(M * N);  // this will never be reallocated
  used_ = 0;

  word_lists_.reserve(1000);
  found_words_.reserve(1000);
  for (int i = 0; i < 26; i++) {
    letter_counts_[i] = 0;
  }
  dupe_mask_ = 0;
  num_overflow_ = 0;
  dict_->ResetMarks();
  for (int cell = 0; cell < M * N; cell++) {
    num_letters_[cell] = strlen(bd_[cell]);
  }
  word_lists_.push_back({});  // start with 1
  num_dupes_ = 0;

  for (int cell = 0; cell < M * N; cell++) {
    DoAllDescents(cell, 0, 0, dict_, arena);
  }
  auto root = root_;
  root_ = NULL;
  dict_->ResetMarks();
  // cout << "len(found_word)=" << found_words_.size()
  //      << ", num_overflow=" << num_overflow_ << endl;
  for (auto word_set : found_words_) {
    delete word_set;
  }
  found_words_.clear();

  cout << "Number of nodes: " << word_lists_.size() << endl;
  cout << "Dupes prevented: " << num_dupes_ << endl;
  unordered_map<int, int> counts;
  int max_count = 0;
  for (auto& wl : word_lists_) {
    int count = wl.size();
    counts[count] += 1;
    max_count = max(max_count, count);
  }
  for (int i = 0; i <= max_count; i++) {
    cout << i << "\t" << counts[i] << endl;
  }

  root->SetPointsAndBound(word_lists_);

  // arena.PrintStats();

  // This can be used to investigate the layout of EvalNode.
  /*
  cout << "sizeof(SumNode) = " << sizeof(SumNode) << endl;
  cout << "sizeof(ChoiceNode) = " << sizeof(ChoiceNode) << endl;
  cout << "root: " << (uintptr_t)root << endl;
  auto r = (uintptr_t)root;
  cout << "root->letter_: " << (uintptr_t)(&root->letter_) - r << endl;
  cout << "root->cell_: " << (uintptr_t)&root->cell_ - r << endl;
  cout << "root->points_: " << (uintptr_t)&root->points_ - r << endl;
  cout << "root->num_children_: " << (uintptr_t)&root->num_children_ - r << endl;
  cout << "root->capacity_: " << (uintptr_t)&root->capacity_ - r << endl;
  cout << "root->bound_: " << (uintptr_t)&root->bound_ - r << endl;
  cout << "root->children_: " << (uintptr_t)&root->children_ - r << endl;
  */
  return root;
}

template <int M, int N>
void OrderlyTreeBuilder<M, N>::DoAllDescents(
    int cell, int n, int length, Trie* t, EvalNodeArena& arena
) {
  auto old_mask = dupe_mask_;
  char* c = &bd_[cell][0];
  int j = 0;
  while (*c) {
    auto cc = *c - 'a';
    if (t->StartsWord(cc)) {
      int cell_order = cell_to_order_[cell];
      choices_[cell_order] = j;
      used_ ^= (1 << cell);
      used_ordered_ ^= (1 << cell_order);

      auto old_count = letter_counts_[cc]++;
      if (old_count == 1) {
        dupe_mask_ |= (1 << cc);
      }

      DoDFS(cell, n + 1, length + (cc == kQ ? 2 : 1), t->Descend(cc), arena);

      letter_counts_[cc]--;
      dupe_mask_ = old_mask;

      used_ordered_ ^= (1 << cell_order);
      used_ ^= (1 << cell);
    }
    c++;
    j++;
  }
}

template <int M, int N>
void OrderlyTreeBuilder<M, N>::DoDFS(
    int i, int n, int length, Trie* t, EvalNodeArena& arena
) {
  auto& neighbors = BucketBoggler<M, N>::NEIGHBORS[i];
  auto n_neighbors = neighbors[0];
  for (int j = 1; j <= n_neighbors; j++) {
    auto idx = neighbors[j];
    if ((used_ & (1 << idx)) == 0) {
      DoAllDescents(idx, n, length, t, arena);
    }
  }

  if (t->IsWord()) {
    auto word_score = kWordScores[length];
    // auto is_dupe = (dupe_mask_ > 0) && CheckForDupe(t);

    SumNode* word_node;
    auto new_root = root_->AddWordWork(
        choices_, used_ordered_, BucketBoggler<M, N>::SPLIT_ORDER, &word_node, arena
    );
    assert(new_root == root_);

    if (dupe_mask_ > 0) {
      // assert(word_node->points_ == 0);
      auto slot = (word_node->points_ << 24) + word_node->bound_;
      // auto slot = word_node->bound_;
      if (slot == 0) {
        slot = word_lists_.size();
        word_lists_.push_back({static_cast<uint32_t>(word_score), t->WordId()});
        // assert(slot < (1 << 24));
        word_node->bound_ = slot & 0xffffff;
        assert(word_node->bound_ != 0);
        assert(slot >> 24 == 0);
        word_node->points_ = slot >> 24;
        auto reslot = (word_node->points_ << 24) + word_node->bound_;
        assert(slot == reslot);
      } else {
        auto& word_list = word_lists_[slot];
        auto word_id = t->WordId();
        if (find(word_list.begin(), word_list.end(), word_id) == word_list.end()) {
          word_list.push_back(word_id);
        } else {
          num_dupes_ += 1;
        }
      }
    } else {
      word_node->points_ += word_score;
    }
  }
}

uint64_t GetChoiceMark(
    const int* choices,
    unsigned int used_ordered,
    const int* split_order,
    const int* num_letters,
    uint64_t max_value
) {
  uint64_t idx = 0;
  while (used_ordered) {
    int order_index = __builtin_ctz(used_ordered);
    int cell = split_order[order_index];
    int letter = choices[order_index];

    used_ordered &= used_ordered - 1;
    idx *= num_letters[cell];
    idx += letter;
    if (idx > max_value) {
      return max_value + 1;
    }
  }
  return idx;
}

template <int M, int N>
bool OrderlyTreeBuilder<M, N>::CheckForDupe(Trie* t) {
  uint64_t max_choice_mark = 1ULL << shift_;
  uint64_t choice_mark = GetChoiceMark(
      choices_,
      used_ordered_,
      BucketBoggler<M, N>::SPLIT_ORDER,
      this->num_letters_,
      max_choice_mark
  );

  if (choice_mark > max_choice_mark) {
    num_overflow_++;
    return false;
  }

  auto prev_paths = (unordered_set<uint64_t>*)(t->Mark());

  uint64_t this_mark = (static_cast<uint64_t>(used_ordered_) << shift_) + choice_mark;
  if (prev_paths == nullptr) {
    auto new_paths = new unordered_set<uint64_t>;
    // This is around the median for the board class for perslatgsineters (19005578)
    // with three buckets ("aeijou bcdfgmpqvwxz hklnrsty").
    new_paths->reserve(100);
    new_paths->insert(this_mark);
    t->Mark((uintptr_t)new_paths);
    found_words_.push_back(new_paths);
    return false;
  }

  auto result = prev_paths->emplace(this_mark);
  auto is_dupe = !result.second;
  return is_dupe;
}

#endif  // ORDERLY_TREE_BUILDER_H
