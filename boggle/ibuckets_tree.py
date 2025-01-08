# ibuckets with a "choice tree" to track a limited number of choices

from boggle.boggle import LETTER_A, LETTER_Q, SCORES
from boggle.ibuckets import PyBucketBoggler, ScoreDetails
from boggle.max_tree import MaxTree, MaxTreeUniverse
from boggle.trie import PyTrie


class TreeBucketBoggler(PyBucketBoggler):
    force_cells: set[int]
    max_tree: MaxTree
    universe: MaxTreeUniverse

    def __init__(self, trie: PyTrie, dims: tuple[int, int], max_depth: int):
        super().__init__(trie, dims)
        self.max_depth = max_depth

    def UpperBound(self, force_cells: set[int]) -> int:
        self.universe = MaxTreeUniverse([*self.bd_], max_depth=self.max_depth)
        self.details_ = ScoreDetails(0, 0)
        self.used_ = 0
        self.runs_ += 1
        self.force_cells = force_cells
        max_tree = self.universe.zero
        for i in range(len(self.bd_)):
            max_score = self.DoAllDescents(i, 0, self.trie_)
            max_tree = self.universe.add(max_tree, max_score)
            # print(i, max_score)
            # TODO: bailout

        # self.universe.print(max_tree)
        # TODO: could return the tree here, it's incredibly useful for pruning.
        self.details_.max_nomark = self.universe.max_value(max_tree)
        self.max_tree = max_tree
        return min(self.details_.max_nomark, self.details_.sum_union)

    def DoAllDescents(self, idx: int, length: int, t: PyTrie) -> MaxTree:
        if idx not in self.force_cells or len(self.bd_[idx]) <= 1:
            # This cell is not being handled specially.
            max_score: MaxTree = self.universe.scalar(0)
            for char in self.bd_[idx]:
                cc = ord(char) - LETTER_A
                if t.StartsWord(cc):
                    tscore = self.DoDFS(
                        idx, length + (2 if cc == LETTER_Q else 1), t.Descend(cc)
                    )
                    max_score = self.universe.max(max_score, tscore)
            return max_score
        else:
            # This cell is being forced and there is a choice to track.
            choices = {k: self.universe.zero for k in self.bd_[idx]}
            vals = []
            for char in self.bd_[idx]:
                cc = ord(char) - LETTER_A
                if t.StartsWord(cc):
                    tscore = self.DoDFS(
                        idx, length + (2 if cc == LETTER_Q else 1), t.Descend(cc)
                    )
                    val = self.universe.max_value(tscore)
                    if val > 0:
                        choices[char] = tscore
                        vals.append(val)
            if not vals:
                return self.universe.zero
            maxv = max(vals)
            if maxv == 0:
                return self.universe.zero
            elif len(vals) == len(choices) and min(vals) == maxv:
                return self.universe.scalar(maxv)
            out = self.universe.from_choices(cell=idx, choices=choices)
            return out

    def DoDFS(self, i: int, length: int, t: PyTrie):
        score = self.universe.zero
        self.used_ ^= 1 << i

        for idx in self.neighbors[i]:
            if not self.used_ & (1 << idx):
                score = self.universe.add(score, self.DoAllDescents(idx, length, t))

        if t.IsWord():
            word_score = SCORES[length]
            score = self.universe.add_scalar(score, word_score)
            # if PRINT_WORDS:
            #     word = reverse_lookup(self.trie_, t)
            #     print(" +%2d (%d,%d) %s" % (word_score, i // 3, i % 3, word))
            if t.Mark() != self.runs_:
                self.details_.sum_union += word_score
                t.SetMark(self.runs_)

        self.used_ ^= 1 << i
        return score
