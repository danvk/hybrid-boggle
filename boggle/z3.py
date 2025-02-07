"""Encode bucket boggle as a constraint problem."""

import json
import sys
from collections import defaultdict

from boggle.boggler import LETTER_A, LETTER_Q, SCORES
from boggle.eval_tree import CHOICE_NODE, EvalNode, EvalTreeBoggler
from boggle.neighbors import NEIGHBORS
from boggle.trie import PyTrie, make_lookup_table, make_py_trie

MARK = 2


def collect_equations(t: EvalNode, cells, eqs: list):
    if t.cache_key == MARK:
        return t.cache_value

    # TODO: could use trie nodes to get word labels for pointy sum nodes
    # TODO: could do a form of DAG optimization here to reduce # of equations
    if t.letter == CHOICE_NODE:
        choices = []
        for c in t.children:
            if c:
                letter_id = f"{cells[c.cell][c.letter]}{c.cell}"
                child_id = collect_equations(c, cells, eqs)
                choices.append((letter_id, child_id))
        if len(choices) == 1 and choices[0][1] == 1:
            t.cache_key = MARK
            t.cache_value = choices[0][0]
            return choices[0][0]
        me_id = f"n_{len(eqs)}"
        eqs.append((me_id, "choice", choices))
    else:
        # sum node
        terms = [t.points] if t.points else []
        for c in t.children:
            if c:
                child_id = collect_equations(c, cells, eqs)
                terms.append(child_id)
        if len(terms) > 1:
            me_id = f"n_{len(eqs)}"
            eqs.append((me_id, "sum", terms))
        else:
            t.cache_key = MARK
            t.cache_value = terms[0]
            return terms[0]

    t.cache_key = MARK
    t.cache_value = me_id
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
            products = []
            for letter_id, term_id in terms:
                if term_id == 1:
                    products.append(letter_id)
                else:
                    products.append(f"(* {letter_id} {term_id})")

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
    tree = etb.BuildTree(None, dedupe=True)
    eqs = []
    root_id = collect_equations(tree, cells, eqs)
    sys.stderr.write(f"eq count: {len(eqs)}\n")
    # print(eqs)
    # print("---\n")
    to_cmsat(cells, cutoff, root_id, eqs)


if __name__ == "__main__":
    main()
