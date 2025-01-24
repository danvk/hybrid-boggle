"""Encode bucket boggle as a constraint problem."""

import json
import sys
from collections import defaultdict

from boggle.boggler import LETTER_A, LETTER_Q, SCORES
from boggle.neighbors import NEIGHBORS
from boggle.trie import PyTrie, make_lookup_table, make_py_trie


class ConstraintBuilder:
    def __init__(self, trie: PyTrie, dims=(3, 3)):
        self.trie = trie
        self.dims = dims
        self.neighbors = NEIGHBORS[dims]

    def build(self, board: str):
        self.used = 0
        self.choices = []
        self.mark = self.trie.Mark() + 1
        self.trie.SetMark(self.mark)
        self.cells = [cell if cell != "." else "" for cell in board.split(" ")]
        assert len(self.cells) == self.dims[0] * self.dims[1]
        self.words = defaultdict[tuple[PyTrie, int], set[str]](set)
        # self.vars = dict[str, list[str]]()
        for i in range(len(self.cells)):
            self.make_choices(i, 0, self.trie)
        return self.words

    def make_choices(self, cell: int, length: int, t: PyTrie):
        """Fill in the choice node given the choices available on this cell."""
        for char in self.cells[cell]:
            cc = ord(char) - LETTER_A
            if t.StartsWord(cc):
                self.choices.append((cell, char))
                self.explore_neighbors(
                    cell, length + (2 if cc == LETTER_Q else 1), t.Descend(cc)
                )
                self.choices.pop()

    def explore_neighbors(self, cell: int, length: int, t: PyTrie):
        self.used ^= 1 << cell

        for ni in self.neighbors[cell]:
            if self.used & (1 << ni):
                continue
            self.make_choices(ni, length, t)

        if t.IsWord():
            word_score = SCORES[length]
            var_seq = tuple(f"{char}{cell}" for cell, char in sorted(self.choices))
            # var = "".join(var_seq)
            # self.vars[var] = var_seq
            k = (t, word_score)
            self.words[k].add(var_seq)

        self.used ^= 1 << cell


def to_cmsat(cells, best_score: int, eqs, trie: PyTrie, word_join="or"):
    # lookup = make_lookup_table(trie)
    # declare variables
    # choices
    for i, cell in enumerate(cells):
        vars = []
        for letter in cell:
            var = f"{letter}{i}"
            vars.append(var)
            print(f"(declare-const {var} Bool)")
        if len(vars) > 1:
            print(f"(assert (= (+ {' '.join(vars)}) 1))")

    # words
    terms = []
    for (t, score), paths in eqs.items():
        # word = lookup[t]
        # print(f"(declare-const {word} Bool)")
        and_paths = [("(and " + " ".join(path) + ")") for path in paths]
        if len(and_paths) == 1:
            term = and_paths[0]
        else:
            word_ors = " ".join(and_paths)
            term = f"({word_join} {word_ors})"

        if score > 1:
            term = f"(* {score} {term})"
        terms.append(term)

    word_sum = " ".join(terms)
    print(f"(assert (> (+ {word_sum}) {best_score}))")
    print("(check-sat)")
    # print("(get-model)")


def main():
    # trie = PyTrie()
    # trie.AddWord("tar")
    # trie.AddWord("tie")
    # trie.AddWord("tier")
    # trie.AddWord("tea")
    # trie.AddWord("the")
    # trie = make_py_trie("mini-dict.txt")
    trie = make_py_trie("boggle-words.txt")
    b = ConstraintBuilder(trie, (3, 3))
    # board = ". . . . lnrsy aeiou aeiou aeiou ."
    (board,) = sys.argv[1:]
    # board = "t i z ae z z r z z"
    cells = board.split(" ")
    eqs = b.build(board)

    sys.stderr.write(f"eq count: {len(eqs)}\n")
    # print(eqs)
    # print("---\n")
    best_score = 700
    to_cmsat(cells, best_score, eqs, trie, word_join="+")


if __name__ == "__main__":
    main()
