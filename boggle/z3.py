"""Encode bucket boggle as a constraint problem."""

import json
import sys
from collections import defaultdict

from boggle.boggler import LETTER_A, LETTER_Q, SCORES
from boggle.eval_tree import CHOICE_NODE, EvalNode, EvalTreeBoggler
from boggle.neighbors import NEIGHBORS
from boggle.trie import PyTrie, make_lookup_table, make_py_trie


def collect_equations(t: EvalNode, eqs: list):
    # TODO: could use trie nodes to get word labels for pointy sum nodes
    # TODO: could do a form of DAG optimization here to reduce # of equations
    if t.letter == CHOICE_NODE:
        choices = []
        for c in t.children:
            if c:
                child_id = collect_equations(c, eqs)
                choices.append((c.cell, c.letter, child_id))
        me_id = f"n_{len(eqs)}"
        eqs.append((me_id, "choice", choices))
    else:
        # sum node
        terms = [t.points]
        for c in t.children:
            if c:
                child_id = collect_equations(c, eqs)
                terms.append(child_id)
        me_id = f"n_{len(eqs)}"
        eqs.append((me_id, "sum", terms))

    return me_id


def to_cmsat(cells, best_score: int, root_id, eqs):
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
    for eq_id, eq_type, terms in eqs:
        print(f"(declare-const {eq_id} Int)")
        if eq_type == "sum":
            print(f"(assert (= {eq_id} (+ {' '.join(str(t) for t in terms)})))")
        else:
            products = [
                f"(* {cells[cell][let]}{cell} {term_id})"
                for (cell, let, term_id) in terms
            ]
            print(f"(assert (= {eq_id} (+ {' '.join(products)})))")

    print(f"(assert (> {root_id} {best_score}))")
    print("(check-sat)")
    print("(get-model)")


def main():
    # trie = PyTrie()
    # trie.AddWord("tar")
    # trie.AddWord("tie")
    # trie.AddWord("tier")
    # trie.AddWord("tea")
    # trie.AddWord("the")
    # trie = make_py_trie("mini-dict.txt")
    (
        cutoff_str,
        board,
    ) = sys.argv[1:]
    trie = make_py_trie("boggle-words.txt")
    cutoff = int(cutoff_str)
    cells = board.split(" ")
    dims = {
        4: (2, 2),
        9: (3, 3),
        12: (3, 4),
        16: (4, 4),
    }[len(cells)]
    etb = EvalTreeBoggler(trie, dims)
    assert etb.ParseBoard(board)
    tree = etb.BuildTree(None, dedupe=False)
    eqs = []
    root_id = collect_equations(tree, eqs)
    sys.stderr.write(f"eq count: {len(eqs)}\n")
    # print(eqs)
    # print("---\n")
    to_cmsat(cells, cutoff, root_id, eqs)


if __name__ == "__main__":
    main()
