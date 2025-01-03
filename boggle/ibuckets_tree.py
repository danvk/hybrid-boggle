# ibuckets with a "choice tree" to track a limited number of choices

from dataclasses import dataclass

from boggle.boggle import LETTER_A, LETTER_Q, SCORES, PyTrie
from boggle.ibuckets import NEIGHBORS, PyBucketBoggler, ScoreDetails


@dataclass
class MaxTree:
    cell: int
    choices: dict[str, int]


type TreeOrScalar = int | MaxTree


def add_max_trees(a: TreeOrScalar, b: TreeOrScalar) -> TreeOrScalar:
    pass


def max_of_max_trees(a: TreeOrScalar, b: TreeOrScalar) -> TreeOrScalar:
    pass


def max_tree_max(t: TreeOrScalar) -> int:
    pass


class TreeBucketBoggler(PyBucketBoggler):
    force_cell: int

    def __init__(self, trie: PyTrie):
        super().__init__(trie)

    def UpperBound(self, bailout_score: int, force_cell: int) -> int:
        self.details_ = ScoreDetails(0, 0)
        self.used_ = 0
        self.runs_ += 1
        self.force_cell = force_cell
        max_tree: TreeOrScalar = 0
        for i in range(0, 9):
            max_score = self.DoAllDescents(i, 0, self.trie_)
            max_tree = add_max_trees(max_tree, max_score)
            # TODO: bailout

        self.details_.max_nomark = max_tree_max(max_tree)
        return min(self.details_.max_nomark, self.details_.sum_union)

    def DoAllDescents(self, idx: int, length: int, t: PyTrie) -> TreeOrScalar:
        if idx != self.force_cell or len(self.bd_[idx]) <= 1:
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
            score = MaxTree(cell=idx, choices={})
            for char in self.bd_[idx]:
                cc = ord(char) - LETTER_A
                if t.StartsWord(cc):
                    tscore = self.DoDFS(
                        idx, length + (2 if cc == LETTER_Q else 1), t.Descend(cc)
                    )
                    assert type(tscore) is int
                    score.choices[char] = tscore
            return score

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
