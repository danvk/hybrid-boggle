#!/usr/bin/env python
"""Break a 2x2 board class via successive lifting."""

import argparse
import json
import sys

from cpp_boggle import Trie, create_eval_node_arena

from boggle.breaker import SPLIT_ORDER
from boggle.dimensional_bogglers import cpp_tree_builder
from boggle.eval_tree import (
    EvalNode,
    EvalTreeBoggler,
    PrintEvalTreeCounts,
    dedupe_subtrees,
)
from boggle.trie import make_py_trie


def tree_stats(t: EvalNode) -> str:
    return f"{t.bound=}, {t.unique_node_count()} unique nodes"
    # h = t.structural_hash()
    # return f"{t.bound=}, {t.unique_node_count()} unique nodes, hash={h}"
    # return f"{t.bound=}, {t.node_count()} nodes, {t.unique_node_count()} unique"
    # , {t.unique_node_count_by_hash()} structurally unique"


def main():
    parser = argparse.ArgumentParser(description="Lift all the way to breaking")
    parser.add_argument(
        "--dictionary",
        type=str,
        default="boggle-words.txt",
        help="Path to dictionary file with one word per line. Words must be "
        '"bogglified" via make_boggle_dict.py to convert "qu" -> "q".',
    )
    parser.add_argument(
        "--python",
        action="store_true",
        help="Use Python implementation of ibuckets instead of C++.",
    )
    parser.add_argument(
        "--compress", action="store_true", help="Compress EvalTree while lifting"
    )
    parser.add_argument(
        "--dedupe",
        action="store_true",
        help="De-dupe EvalTree initially and while lifting",
    )
    parser.add_argument("cutoff", type=int, help="Best known score for filtering.")
    parser.add_argument("board", type=str, help="Board class to lift.")
    args = parser.parse_args()

    cutoff = args.cutoff
    board = args.board

    cells = board.split(" ")
    dims = {
        4: (2, 2),
        9: (3, 3),
        12: (3, 4),
        16: (4, 4),
    }[len(cells)]

    if args.python:
        trie = make_py_trie("boggle-words.txt")
        etb = EvalTreeBoggler(trie, dims)
    else:
        trie = Trie.CreateFromFile("boggle-words.txt")
        etb = cpp_tree_builder(trie, dims)

    arena = create_eval_node_arena()
    etb.ParseBoard(board)
    t = etb.BuildTree(arena, dedupe=args.dedupe)
    print(tree_stats(t))
    # t.compress_in_place()
    # print(f"c -> {tree_stats(t)}")
    # dedupe_subtrees(t)
    # print(f"d -> {tree_stats(t)}")

    print("num max_subtrees:", sum(1 for _ in t.max_subtrees()))

    for k in range(len(cells)):
        i = SPLIT_ORDER[dims][k]
        print(f"lift {i}")
        t = t.lift_choice(
            i, len(cells[i]), arena, dedupe=args.dedupe, compress=args.compress
        )
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

        # if dims == (2, 2):
        #     with open(f"/tmp/lifted{i}.json", "w") as out:
        #         json.dump(t.to_json(etb), out)

    PrintEvalTreeCounts()


if __name__ == "__main__":
    main()
