#!/usr/bin/env python
"""Break a 2x2 board class via successive lifting."""

import json
import sys

from boggle.breaker import SPLIT_ORDER
from boggle.eval_tree import (
    EvalNode,
    EvalTreeBoggler,
    PrintEvalTreeCounts,
    dedupe_subtrees,
)
from boggle.trie import make_py_trie


def tree_stats(t: EvalNode) -> str:
    return f"{t.bound=}, {t.unique_node_count()} unique nodes"
    # return f"{t.bound=}, {t.node_count()} nodes, {t.unique_node_count()} unique"
    # , {t.unique_node_count_by_hash()} structurally unique"


def main():
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
    etb.ParseBoard(board)
    cells = board.split(" ")
    t = etb.BuildTree(dedupe=True)
    print(tree_stats(t))
    # t.compress_in_place()
    # print(f"c -> {tree_stats(t)}")
    # dedupe_subtrees(t)
    # print(f"d -> {tree_stats(t)}")

    print("num max_subtrees:", sum(1 for _ in t.max_subtrees()))

    for k in range(len(cells)):
        i = SPLIT_ORDER[dims][k]
        print(f"lift {i}")
        t = t.lift_choice(i, len(cells[i]), dedupe=True, compress=True)
        if t.bound <= cutoff:
            print(f"Fully broken! {t.bound} <= {cutoff} {tree_stats(t)}")
            break
        # print(f"-> {tree_stats(t)}")
        # print("num max_subtrees:", sum(1 for _ in t.max_subtrees()))
        t.filter_below_threshold(cutoff)
        print(f"f -> {tree_stats(t)}")
        # print("num max_subtrees:", sum(1 for _ in t.max_subtrees()))
        # t.compress_in_place()
        # print(f"c -> {tree_stats(t)}")
        # dedupe_subtrees(t)
        # print(f"d -> {tree_stats(t)}")

        # max_bound = t.bound
        # for seq in t.max_subtrees():
        #     if seq[-1].bound < max_bound:
        #         continue
        #     choices = [-1 for _ in cells]
        #     for cell, letter in seq[:-1]:
        #         choices[cell] = letter
        #     board = "".join(cells[i][let] for i, let in enumerate(choices))
        #     print(f"{t.bound} {board} {choices}")

        if dims == (2, 2):
            with open(f"/tmp/lifted{i}.json", "w") as out:
                json.dump(t.to_json(etb), out)

    PrintEvalTreeCounts()


if __name__ == "__main__":
    main()
