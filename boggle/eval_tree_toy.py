import json
import sys
import time

from boggle.eval_tree import EvalTreeBoggler, PrintEvalTreeCounts, ResetEvalTreeCount
from boggle.ibuckets import PyBucketBoggler
from boggle.trie import make_py_trie

BIGINT = 1_000_000


class Timer:
    def __init__(self, label: str):
        self.label = label

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, type, value, traceback):
        self.time = (time.perf_counter() - self.start) * 1e3
        self.readout = f"{self.label}: {self.time:.3f} ms"
        print(self.readout)


def try_all(bb, force_cell=-1):
    print(bb.as_string())
    cells = bb.as_string().split(" ")
    for i, cell in enumerate(cells):
        if (force_cell != -1 and i != force_cell) or len(cell) == 1:
            continue
        max_cell = 0
        with Timer(f"force {i}"):
            for c in cell:
                cp = [*cells]
                cp[i] = c
                assert bb.ParseBoard(" ".join(cp))
                score = bb.UpperBound(500_000)
                d = bb.Details()
                print(f"{i}/{c}", score, d.max_nomark, d.sum_union, bb.as_string())
                max_cell = max(max_cell, score)
        print(f"{i}: {max_cell}")


def try_all2(bb: PyBucketBoggler, cell1: int, cell2: int):
    cells = bb.as_string().split(" ")
    max_cell = 0
    for choice1 in cells[cell1]:
        for choice2 in cells[cell2]:
            cp = [*cells]
            cp[cell1] = choice1
            cp[cell2] = choice2
            assert bb.ParseBoard(" ".join(cp))
            score = bb.UpperBound(500_000)
            # d = bb.Details()
            # print(
            #     f"{cell1}={choice1}, {cell2}={choice2}",
            #     score,
            #     d.max_nomark,
            #     d.sum_union,
            #     bb.as_string(),
            # )
            max_cell = max(max_cell, score)
    print(f"max (explicit): {max_cell}")


def main_viz():
    (board,) = sys.argv[1:]
    pyt = make_py_trie("wordlists/enable2k.txt")
    etb = EvalTreeBoggler(pyt, (3, 4))
    etb.ParseBoard(board)
    tree = etb.BuildTree()
    json.dump(tree.to_json(etb, 5), sys.stdout, indent=2)


def main():
    (board,) = sys.argv[1:]
    pyt = make_py_trie("wordlists/enable2k.txt")
    pbb = PyBucketBoggler(pyt, (3, 4))
    pbb.ParseBoard(board)

    with Timer("PyBucketBoggler"):
        score = pbb.UpperBound(BIGINT)
    print(f"PyBucketBoggler: {score} {pbb.Details()}")

    pyt.ResetMarks()
    etb = EvalTreeBoggler(pyt, (3, 4))
    etb.ParseBoard(board)
    with Timer("Construct EvalTree"):
        tree = etb.BuildTree()
    print("num nodes:", tree.node_count())
    print(f"score (construction): {tree.bound}", etb.Details())
    PrintEvalTreeCounts()
    print("---")

    # with Timer("Rescore"):
    #     score = tree.recompute_score()
    # print(f"recomputed score: {score}")
    # print(tree.to_string(etb))
    # tree.print_words(etb)

    # with Timer("prune"):
    # tree.prune()
    # print("num nodes:", tree.node_count())
    # with Timer("rescore"):
    #     score = tree.recompute_score()
    # print(f"recomputed score: {score}")

    print("score with forces")
    print("6=a", tree.score_with_forces({6: 0}))
    print("6=a, 5=a", tree.score_with_forces({5: 0, 6: 0}))
    print("---")

    with Timer("EvalTree force 5"):
        subtrees = tree.force_cell(5, len(etb.bd_[5]))
    assert len(subtrees) == len(etb.bd_[5])
    five_trees = subtrees
    counts = {}
    for letter, subtree in zip(etb.bd_[5], subtrees):
        # subtree.check_consistency()
        print(f"5={letter}: {subtree.bound}")
        counts[letter] = subtree.node_count()
    PrintEvalTreeCounts()
    print("---")

    # with Timer("compress"):
    #     for subtree in subtrees:
    #         subtree.compress()
    for letter, subtree in zip(etb.bd_[5], subtrees):
        # subtree.check_consistency()
        c = subtree.node_count()
        pct = 100 * (c - counts[letter]) / counts[letter]
        print(f"5={letter}: {counts[letter]} -> {c} ({pct:.2f}%)")

    # print("remaining choice nodes:")
    singletons = 0
    for node in five_trees[0].all_nodes():
        if node.cell == 5 and node.letter == -1:
            print(node)
            assert False
        if len(node.children) == 1:
            singletons += 1
    print(f"{singletons=} / {five_trees[0].node_count()}")

    print("---")
    print("PyBucketBoggler try all 5s")
    pyt.ResetMarks()
    pbb.ParseBoard(board)
    try_all(pbb, 5)
    # pbb.print_words = True
    # pbb.bd_[5] = pbb.bd_[5][0]
    # pbb.bd_[6] = pbb.bd_[6][0]
    # print(pbb.as_string())
    # print(pbb.UpperBound(BIGINT), pbb.Details())

    print("---")
    ResetEvalTreeCount()
    with Timer("EvalTree force 5, 6"):
        # subtrees = tree.force_cell(5, len(etb.bd_[5]))
        subsubtrees = [subtree.force_cell(6, len(etb.bd_[6])) for subtree in five_trees]
    assert len(subsubtrees) == len(etb.bd_[5])
    assert len(subsubtrees[0]) == len(etb.bd_[6])
    max2 = 0
    counts = {}
    for letter5, subtrees in zip(etb.bd_[5], subsubtrees):
        for letter6, subtree in zip(etb.bd_[6], subtrees):
            # nc = subtree.node_count()
            # subtree.prune()
            # subtree.check_consistency()
            # print(
            #     f"5={letter5}, 6={letter6}: {subtree.bound}"
            #     # /{subtree.recompute_score()} ({nc} -> {subtree.node_count()} nodes)"
            # )
            max2 = max(max2, subtree.bound)
            counts[(letter5, letter6)] = subtree.node_count()
    print(f"max: {max2}")
    PrintEvalTreeCounts()

    # with Timer("compress"):
    #     for subtrees in subsubtrees:
    #         for subtree in subtrees:
    #             subtree.compress()
    for letter5, subtrees in zip(etb.bd_[5], subsubtrees):
        for letter6, subtree in zip(etb.bd_[6], subtrees):
            b = counts[(letter5, letter6)]
            c = subtree.node_count()
            pct = 100 * (c - b) / b
            print(f"5={letter5}, 6={letter6}: {b} -> {c} ({pct:.2f}%)")

    print("---")
    print("PyBucketBoggler try all 5+6s")
    pyt.ResetMarks()
    pbb.ParseBoard(board)
    with Timer("explicit 5, 6"):
        try_all2(pbb, 5, 6)

    print("---")
    print("EvalTree, force5 + score_with_forces(6)")
    with Timer("Tree5 + Force6"):
        max_score = 0
        for letter6 in range(len(etb.bd_[6])):
            for tree in five_trees:
                score = tree.score_with_forces({6: letter6})
                max_score = max(score, max_score)
    print(f"Tree5 + Force6: {max_score}")

    pbb.collect_words = True
    cells = board.split(" ")
    assert "a" in cells[5]
    cells[5] = "a"
    assert "e" in cells[6]
    cells[6] = "e"
    pbb.ParseBoard(" ".join(cells))
    pbb.target_word = "tarweed"
    pbb.UpperBound(500_000)
    with open("/tmp/words.pbb.txt", "w") as out:
        out.write("\n".join(pbb.words))
        out.write("\n")

    tree_words = subsubtrees[0][1].all_words(pbb.lookup_table)
    with open("/tmp/words.etb.txt", "w") as out:
        out.write("\n".join(tree_words))
        out.write("\n")
    # print(subsubtrees[0][0].to_string(etb))

    subsubtrees[0][1].print_paths("tarweed", pbb.lookup_table)


if __name__ == "__main__":
    # main()
    main_viz()
