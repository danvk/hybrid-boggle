# ibuckets with a "choice tree" to track a limited number of choices

from boggle.boggle import LETTER_A, LETTER_Q, SCORES, PyTrie
from boggle.ibuckets import NEIGHBORS, PyBucketBoggler, ScoreDetails
from boggle.max_tree import (
    MaxTree,
    TreeOrScalar,
    add_max_trees,
    max_of_max_trees,
    max_tree_max,
)


class TreeBucketBoggler(PyBucketBoggler):
    force_cells: set[int]
    max_tree: TreeOrScalar

    def __init__(self, trie: PyTrie):
        super().__init__(trie)

    def UpperBound(self, bailout_score: int, force_cells: set[int]) -> int:
        self.details_ = ScoreDetails(0, 0)
        self.used_ = 0
        self.runs_ += 1
        self.force_cells = force_cells
        max_tree: TreeOrScalar = 0
        for i in range(0, 9):
            max_score = self.DoAllDescents(i, 0, self.trie_)
            max_tree = add_max_trees(max_tree, max_score)
            # print(i, max_score)
            # TODO: bailout

        print(max_tree)
        # TODO: could return the tree here, it's incredibly useful for pruning.
        self.details_.max_nomark = max_tree_max(max_tree)
        self.max_tree = max_tree
        return min(self.details_.max_nomark, self.details_.sum_union)

    def DoAllDescents(self, idx: int, length: int, t: PyTrie) -> TreeOrScalar:
        if idx not in self.force_cells or len(self.bd_[idx]) <= 1:
            # This cell is not being handled specially.
            max_score: TreeOrScalar = 0
            for char in self.bd_[idx]:
                cc = ord(char) - LETTER_A
                if t.StartsWord(cc):
                    tscore = self.DoDFS(
                        idx, length + (2 if cc == LETTER_Q else 1), t.Descend(cc)
                    )
                    max_score = max_of_max_trees(max_score, tscore)
            return max_score
        else:
            # This cell is being forced and there is a choice to track.
            # MaxTree requires that all choices be filled out explicitly.
            choices = {k: 0 for k in self.bd_[idx]}
            vals = []
            for char in self.bd_[idx]:
                cc = ord(char) - LETTER_A
                if t.StartsWord(cc):
                    tscore = self.DoDFS(
                        idx, length + (2 if cc == LETTER_Q else 1), t.Descend(cc)
                    )
                    val = max_tree_max(tscore)
                    if val > 0:
                        choices[char] = tscore
                        vals.append(val)
            if not vals:
                return 0
            maxv = max(vals)
            if maxv == 0 or (len(vals) == len(choices) and min(vals) == maxv):
                return maxv
            return MaxTree(cell=idx, choices=choices)

    def DoDFS(self, i: int, length: int, t: PyTrie):
        score: TreeOrScalar = 0
        self.used_ ^= 1 << i

        for idx in NEIGHBORS[i]:
            if not self.used_ & (1 << idx):
                score = add_max_trees(score, self.DoAllDescents(idx, length, t))

        if t.IsWord():
            word_score = SCORES[length]
            score = add_max_trees(score, word_score)
            # if PRINT_WORDS:
            #     word = reverse_lookup(self.trie_, t)
            #     print(" +%2d (%d,%d) %s" % (word_score, i // 3, i % 3, word))
            if t.Mark() != self.runs_:
                self.details_.sum_union += word_score
                t.SetMark(self.runs_)

        self.used_ ^= 1 << i
        return score
