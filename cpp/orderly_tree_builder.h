#ifndef ORDERLY_TREE_BUILDER_H
#define ORDERLY_TREE_BUILDER_H

#include <array>
#include <functional>
#include <iomanip>
#include <span>
#include <vector>

#include "constants.h"
#include "equal_ranges.h"
#include "eval_node.h"
#include "ibuckets.h"

using namespace std;

struct TreeBuilderStats {
  float collect_s;
  float sort_s;
  float build_s;
  uint32_t n_paths;
  uint32_t n_uniq;
};

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

  using BoardClassBoggler<M, N>::dict_;
  using BoardClassBoggler<M, N>::bd_;
  using BoardClassBoggler<M, N>::used_;

  const SumNode* BuildTree(EvalNodeArena& arena, vector<uint32_t>& out_score_prefixes);

  unique_ptr<EvalNodeArena> CreateArena() { return create_eval_node_arena(); }

  struct WordPath {
    array<uint8_t, 2 * M * N> path;
    uint32_t word_id : 24;
    uint8_t points : 8;
  };

  TreeBuilderStats GetStats() const { return stats_; }

 private:
  SumNode* root_;
  int cell_to_order_[M * N];
  unsigned int used_ordered_;
  int choices_[M * N];
  vector<WordPath> words_;
  TreeBuilderStats stats_;

  void DoAllDescents(int cell, int n, int length, Trie* t, EvalNodeArena& arena);
  void DoDFS(int cell, int n, int length, Trie* t, EvalNodeArena& arena);
  void AddWord(int* choices, unsigned int used_ordered, uint32_t word_id, int length);

  static bool WordComparator(const WordPath& a, const WordPath& b);
  static void UniqueWordList(vector<WordPath>& words);
  void PrintWordList();
};

template <unsigned long N>
int PathLength(const array<uint8_t, N>& a) {
  int len = 0;
  for (int i = 0; i < N; i += 2, len++) {
    if (a[i] == '\0') break;
  }
  return len;
}

template <int M, int N>
const SumNode* OrderlyTreeBuilder<M, N>::BuildTree(EvalNodeArena& arena, vector<uint32_t>& out_score_prefixes) {
  TreeBuilderStats stats;
  auto start = chrono::high_resolution_clock::now();
  
  words_.clear();
  words_.reserve(20'000'000);

  for (int cell = 0; cell < M * N; cell++) {
    DoAllDescents(cell, 0, 0, dict_, arena);
  }
  auto end1 = chrono::high_resolution_clock::now();
  stats.collect_s = chrono::duration_cast<chrono::milliseconds>(end1 - start).count() / 1000.0;

  if (words_.empty()) {
    auto root_ref = arena.NewSumNodeWithCapacity(0);
    return arena.ToPtr<SumNode>(root_ref);
  }

  sort(words_.begin(), words_.end(), WordComparator);
  auto end2 = chrono::high_resolution_clock::now();
  stats.sort_s = chrono::duration_cast<chrono::milliseconds>(end2 - end1).count() / 1000.0;
  stats.n_paths = words_.size();

  UniqueWordList(words_);
  auto end3 = chrono::high_resolution_clock::now();
  stats.n_uniq = words_.size();

  // Build Score Prefixes
  out_score_prefixes.clear();
  out_score_prefixes.reserve(words_.size() + 1);
  out_score_prefixes.push_back(0);
  uint32_t running_score = 0;
  for (const auto& w : words_) {
      running_score += w.points;
      out_score_prefixes.push_back(running_score);
  }

  // BFS Implementation
  struct PendingSum { NodeRef node; int start; int end; };
  struct PendingChoice { NodeRef node; int start; int end; };
  
  vector<PendingSum> current_sum_nodes;
  
  // Initialize Root
  int root_depth = 0;
  int root_start = 0;
  int root_end = words_.size();
  int root_points = 0;
  if (PathLength(words_[root_start].path) == root_depth) {
    root_points = words_[root_start].points;
    ++root_start;
  }
  
  auto root_ranges = equal_ranges(words_, 2 * root_depth, root_start, root_end);
  auto root_ref = arena.NewSumNodeWithCapacity(root_ranges.size());
  auto root = arena.ToPtr<SumNode>(root_ref);
  root->points_ = root_points;
  root->range_start_ = root_start;
  root->range_end_ = root_end;
  root->bound_ = root_points + (out_score_prefixes[root_end] - out_score_prefixes[root_start]);
  
  uint32_t root_child_cells = 0;
  for(const auto& r : root_ranges) root_child_cells |= (1 << (r.cell - 1));
  root->child_cells_ = root_child_cells;

  current_sum_nodes.push_back({root_ref, root_start, root_end});
  
  int depth = 0;
  while (!current_sum_nodes.empty()) {
    vector<PendingChoice> next_choice_nodes;
    for (const auto& task : current_sum_nodes) {
        auto node = arena.ToPtr<SumNode>(task.node);
        int start = task.start;
        int end = task.end;
        
        auto ranges = equal_ranges(words_, 2 * depth, start, end);
        
        for (int i = 0; i < ranges.size(); ++i) {
            const auto& [cell, r_start, r_end] = ranges[i];
            
            auto child_ranges = equal_ranges(words_, 2 * depth + 1, r_start, r_end);
            
            auto child_ref = arena.NewChoiceNodeWithCapacity(child_ranges.size());
            auto child = arena.ToPtr<ChoiceNode>(child_ref);
            child->range_start_ = r_start;
            child->range_end_ = r_end;
            child->bound_ = out_score_prefixes[r_end] - out_score_prefixes[r_start];
            uint32_t letters = 0;
            for(const auto& cr : child_ranges) letters |= (1 << (cr.cell - 1));
            child->child_letters_ = letters;
            
            node->children_[i] = child_ref;
            next_choice_nodes.push_back({child_ref, r_start, r_end});
        }
    }
    
    if (next_choice_nodes.empty()) break;
    
    vector<PendingSum> next_sum_nodes;
    for (const auto& task : next_choice_nodes) {
        auto node = arena.ToPtr<ChoiceNode>(task.node);
        int start = task.start;
        int end = task.end;
        
        auto ranges = equal_ranges(words_, 2 * depth + 1, start, end);
        
        for (int i = 0; i < ranges.size(); ++i) {
            const auto& [letter, r_start, r_end] = ranges[i];
            
            int next_points = 0;
            int next_start = r_start;
            if (PathLength(words_[next_start].path) == depth + 1) {
                next_points = words_[next_start].points;
                ++next_start;
            }
            size_t next_len = r_end - next_start;
            
            if (next_len == 0 && next_points <= NUM_INTERNED) {
                // Canonical leaves
                // Bound is implicitly set by Canonical Node (points_ == bound_)
                node->children_[i] = arena.ToRef(arena.GetCanonicalNode(next_points));
            } else {
                auto child_ranges = equal_ranges(words_, 2 * (depth + 1), next_start, r_end);
                auto child_ref = arena.NewSumNodeWithCapacity(child_ranges.size());
                auto child = arena.ToPtr<SumNode>(child_ref);
                child->points_ = next_points;
                child->range_start_ = next_start;
                child->range_end_ = r_end;
                child->bound_ = next_points + (out_score_prefixes[r_end] - out_score_prefixes[next_start]);
                uint32_t cells = 0;
                for(const auto& cr : child_ranges) cells |= (1 << (cr.cell - 1));
                child->child_cells_ = cells;
                
                node->children_[i] = child_ref;
                next_sum_nodes.push_back({child_ref, next_start, r_end});
            }
        }
    }
    
    current_sum_nodes = move(next_sum_nodes);
    depth++;
  }
  
  // No bottom-up pass needed!

  auto end4 = chrono::high_resolution_clock::now();
  stats.build_s = chrono::duration_cast<chrono::milliseconds>(end4 - end3).count() / 1000.0;
  words_.clear();
  words_.shrink_to_fit();
  stats_ = stats;

  return arena.ToPtr<SumNode>(root_ref);
}

// ... rest of file ...
#define REC(idx) do { if ((used_ & (1 << idx)) == 0) { DoAllDescents(idx, n, length, t, arena); } } while (0)
#define REC3(a, b, c) REC(a); REC(b); REC(c)
#define REC5(a, b, c, d, e) REC3(a, b, c); REC(d); REC(e)
#define REC8(a, b, c, d, e, f, g, h) REC5(a, b, c, d, e); REC3(f, g, h)

// ... DoDFS implementations (same as before) ...
// I will keep the DoDFS parts from previous write.
// Since I'm using write_file with content, I need to provide full content.
// I'll copy the DoDFS part again.

// 2x2
template<>
void OrderlyTreeBuilder<2, 2>::DoDFS(
    int i, int n, int length, Trie* t, EvalNodeArena& arena
) {
  if (t->IsWord()) {
    AddWord(choices_, used_ordered_, t->WordId(), length);
  }
  switch(i) {
    case 0: REC3(1, 2, 3); break;
    case 1: REC3(0, 2, 3); break;
    case 2: REC3(0, 1, 3); break;
    case 3: REC3(0, 1, 2); break;
  }
}

// 2x3
template<>
void OrderlyTreeBuilder<2, 3>::DoDFS(
    int i, int n, int length, Trie* t, EvalNodeArena& arena
) {
  if (t->IsWord()) {
    AddWord(choices_, used_ordered_, t->WordId(), length);
  }
  switch(i) {
    case 0: REC3(1, 3, 4); break;
    case 1: REC5(0, 2, 3, 4, 5); break;
    case 2: REC3(1, 4, 5); break;
    case 3: REC3(0, 1, 4); break;
    case 4: REC5(0, 1, 2, 3, 5); break;
    case 5: REC3(1, 2, 4); break;
  }
}

// 3x3
template<>
void OrderlyTreeBuilder<3, 3>::DoDFS(
    int i, int n, int length, Trie* t, EvalNodeArena& arena
) {
  if (t->IsWord()) {
    AddWord(choices_, used_ordered_, t->WordId(), length);
  }
  switch(i) {
    case 0: REC3(1, 3, 4); break;
    case 1: REC5(0, 2, 3, 4, 5); break;
    case 2: REC3(1, 4, 5); break;
    case 3: REC5(0, 1, 4, 6, 7); break;
    case 4: REC8(0, 1, 2, 3, 5, 6, 7, 8); break;
    case 5: REC5(1, 2, 4, 7, 8); break;
    case 6: REC3(3, 4, 7); break;
    case 7: REC5(3, 4, 5, 6, 8); break;
    case 8: REC3(4, 5, 7); break;
  }
}

// 3x4
template<>
void OrderlyTreeBuilder<3, 4>::DoDFS(
    int i, int n, int length, Trie* t, EvalNodeArena& arena
) {
  if (t->IsWord()) {
    AddWord(choices_, used_ordered_, t->WordId(), length);
  }
  switch(i) {
    case 0: REC3(1, 4, 5); break;
    case 1: REC5(0, 2, 4, 5, 6); break;
    case 2: REC5(1, 3, 5, 6, 7); break;
    case 3: REC3(2, 6, 7); break;
    case 4: REC5(0, 1, 5, 8, 9); break;
    case 5: REC8(0, 1, 2, 4, 6, 8, 9, 10); break;
    case 6: REC8(1, 2, 3, 5, 7, 9, 10, 11); break;
    case 7: REC5(2, 3, 6, 10, 11); break;
    case 8: REC3(4, 5, 9); break;
    case 9: REC5(4, 5, 6, 8, 10); break;
    case 10: REC5(5, 6, 7, 9, 11); break;
    case 11: REC3(6, 7, 10); break;
  }
}

// 4x4
template<>
void OrderlyTreeBuilder<4, 4>::DoDFS(
    int i, int n, int length, Trie* t, EvalNodeArena& arena
) {
  if (t->IsWord()) {
    AddWord(choices_, used_ordered_, t->WordId(), length);
  }
  switch(i) {
    case 0: REC3(1, 4, 5); break;
    case 1: REC5(0, 2, 4, 5, 6); break;
    case 2: REC5(1, 3, 5, 6, 7); break;
    case 3: REC3(2, 6, 7); break;
    case 4: REC5(0, 1, 5, 8, 9); break;
    case 5: REC8(0, 1, 2, 4, 6, 8, 9, 10); break;
    case 6: REC8(1, 2, 3, 5, 7, 9, 10, 11); break;
    case 7: REC5(2, 3, 6, 10, 11); break;
    case 8: REC5(4, 5, 9, 12, 13); break;
    case 9: REC8(4, 5, 6, 8, 10, 12, 13, 14); break;
    case 10: REC8(5, 6, 7, 9, 11, 13, 14, 15); break;
    case 11: REC5(6, 7, 10, 14, 15); break;
    case 12: REC3(8, 9, 13); break;
    case 13: REC5(8, 9, 10, 12, 14); break;
    case 14: REC5(9, 10, 11, 13, 15); break;
    case 15: REC3(10, 11, 14); break;
  }
}

// 4x5
template<>
void OrderlyTreeBuilder<4, 5>::DoDFS(
    int i, int n, int length, Trie* t, EvalNodeArena& arena
) {
  if (t->IsWord()) {
    AddWord(choices_, used_ordered_, t->WordId(), length);
  }
  switch(i) {
    case 0: REC3(1, 5, 6); break;
    case 1: REC5(0, 2, 5, 6, 7); break;
    case 2: REC5(1, 3, 6, 7, 8); break;
    case 3: REC5(2, 4, 7, 8, 9); break;
    case 4: REC3(3, 8, 9); break;
    case 5: REC5(0, 1, 6, 10, 11); break;
    case 6: REC8(0, 1, 2, 5, 7, 10, 11, 12); break;
    case 7: REC8(1, 2, 3, 6, 8, 11, 12, 13); break;
    case 8: REC8(2, 3, 4, 7, 9, 12, 13, 14); break;
    case 9: REC5(3, 4, 8, 13, 14); break;
    case 10: REC5(5, 6, 11, 15, 16); break;
    case 11: REC8(5, 6, 7, 10, 12, 15, 16, 17); break;
    case 12: REC8(6, 7, 8, 11, 13, 16, 17, 18); break;
    case 13: REC8(7, 8, 9, 12, 14, 17, 18, 19); break;
    case 14: REC5(8, 9, 13, 18, 19); break;
    case 15: REC3(10, 11, 16); break;
    case 16: REC5(10, 11, 12, 15, 17); break;
    case 17: REC5(11, 12, 13, 16, 18); break;
    case 18: REC5(12, 13, 14, 17, 19); break;
    case 19: REC3(13, 14, 18); break;
  }
}

// 5x5
template<>
void OrderlyTreeBuilder<5, 5>::DoDFS(
    int i, int n, int length, Trie* t, EvalNodeArena& arena
) {
  if (t->IsWord()) {
    AddWord(choices_, used_ordered_, t->WordId(), length);
  }
  switch(i) {
    case 0: REC3(1, 5, 6); break;
    case 1: REC5(0, 2, 5, 6, 7); break;
    case 2: REC5(1, 3, 6, 7, 8); break;
    case 3: REC5(2, 4, 7, 8, 9); break;
    case 4: REC3(3, 8, 9); break;
    case 5: REC5(0, 1, 6, 10, 11); break;
    case 6: REC8(0, 1, 2, 5, 7, 10, 11, 12); break;
    case 7: REC8(1, 2, 3, 6, 8, 11, 12, 13); break;
    case 8: REC8(2, 3, 4, 7, 9, 12, 13, 14); break;
    case 9: REC5(3, 4, 8, 13, 14); break;
    case 10: REC5(5, 6, 11, 15, 16); break;
    case 11: REC8(5, 6, 7, 10, 12, 15, 16, 17); break;
    case 12: REC8(6, 7, 8, 11, 13, 16, 17, 18); break;
    case 13: REC8(7, 8, 9, 12, 14, 17, 18, 19); break;
    case 14: REC5(8, 9, 13, 18, 19); break;
    case 15: REC5(10, 11, 16, 20, 21); break;
    case 16: REC8(10, 11, 12, 15, 17, 20, 21, 22); break;
    case 17: REC8(11, 12, 13, 16, 18, 21, 22, 23); break;
    case 18: REC8(12, 13, 14, 17, 19, 22, 23, 24); break;
    case 19: REC5(13, 14, 18, 23, 24); break;
    case 20: REC3(15, 16, 21); break;
    case 21: REC5(15, 16, 17, 20, 22); break;
    case 22: REC5(16, 17, 18, 21, 23); break;
    case 23: REC5(17, 18, 19, 22, 24); break;
    case 24: REC3(18, 19, 23); break;
  }
}

#undef REC
#undef REC3
#undef REC5
#undef REC8

template <int M, int N>
void OrderlyTreeBuilder<M, N>::AddWord(
    int* choices, unsigned int used_ordered, uint32_t word_id, int length
) {
  words_.emplace_back(WordPath());
  WordPath& word = *words_.rbegin();
  const auto& split_order = BucketBoggler<M, N>::SPLIT_ORDER;

  int idx = 0;
  word.path.fill('\0');
  while (used_ordered) {
    int order_index = std::countr_zero(used_ordered);
    int cell = split_order[order_index];
    int letter = choices[order_index];
    word.path[idx++] = 1 + cell;
    word.path[idx++] = 1 + letter;
    used_ordered &= used_ordered - 1;
  }
  word.points = kWordScores[length];
  word.word_id = word_id;
}

template <int M, int N>
bool OrderlyTreeBuilder<M, N>::WordComparator(const WordPath& a, const WordPath& b) {
  const auto& ap = a.path;
  const auto& bp = b.path;
  auto result = memcmp(ap.data(), bp.data(), 2 * M * N);
  if (result != 0) {
    return result < 0;
  }

  return a.word_id < b.word_id;
}

template <int M, int N>
void OrderlyTreeBuilder<M, N>::UniqueWordList(vector<WordPath>& words) {
  int write_idx = 1;
  WordPath last = words[0];
  auto n = words.size();
  for (int i = 1; i < n; i++) {
    const auto& w = words[i];
    int result = memcmp(w.path.data(), last.path.data(), 2 * M * N);
    if (result != 0) {
      if (i != write_idx) {
        words[write_idx] = w;
      }
      last = words[write_idx];
      write_idx++;
    } else if (w.word_id != last.word_id) {
      words[write_idx - 1].points += w.points;
      last.word_id = w.word_id;
    }
  }
  words.erase(words.begin() + write_idx, words.end());
}

template <int M, int N>
void OrderlyTreeBuilder<M, N>::PrintWordList() {
  int i = 0;
  for (const auto& w : words_) {
    cout << std::setw(3) << (i++) << " [";
    for (int k = 0; k < 2 * M * N; k += 2) {
      if (w.path[k] == '\0') {
        break;
      }
      if (k) cout << ", ";
      cout << "(" << (int)(w.path[k] - 1) << ", " << (int)(w.path[k + 1] - 1) << ")";
    }
    cout << "] (" << (int)w.points << ") ";
    auto t = dict_->FindWordId(w.word_id);
    cout << "(" << Trie::ReverseLookup(dict_, t) << ")" << endl;
  }
}

#endif  // ORDERLY_TREE_BUILDER_H