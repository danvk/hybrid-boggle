#!/usr/bin/env python

import argparse
import dataclasses
import itertools
import json
import multiprocessing
import random
import time
from collections import Counter
from dataclasses import dataclass

from cpp_boggle import Trie
from tqdm import tqdm

from boggle.board_id import from_board_id, is_canonical_board_id
from boggle.boggler import PyBoggler
from boggle.breaker import (
    BreakDetails,
    HybridTreeBreaker,
    IBucketBreaker,
    merge_details,
    print_details,
)
from boggle.dimensional_bogglers import Bogglers, BucketBogglers, TreeBuilders
from boggle.eval_tree import EvalTreeBoggler
from boggle.ibuckets import PyBucketBoggler
from boggle.trie import PyTrie, make_py_trie


@dataclass
class BreakingBundle:
    """Only the breaker is needed, but this helps keep its deps from being GC'd."""

    trie: PyTrie
    boggler: PyBoggler
    etb: EvalTreeBoggler
    breaker: IBucketBreaker | HybridTreeBreaker


def break_init(args):
    bundle = get_breaker(args)
    # See https://stackoverflow.com/a/30816116/388951 for this trick to avoid a global
    break_worker.bundle = bundle
    break_worker.args = args
    (me,) = multiprocessing.current_process()._identity
    with open(f"tasks-{me}.ndjson", "w"):
        pass

    print(f"Started worker #{me}")


def break_worker(task: str | int):
    bundle: BreakingBundle = break_worker.bundle
    breaker = bundle.breaker
    args = break_worker.args
    (me,) = multiprocessing.current_process()._identity

    best_score = args.best_score
    assert best_score > 0
    classes = args.classes.split(" ")
    dims = args.size // 10, args.size % 10

    if isinstance(task, int):
        board = from_board_id(classes, dims, task)
        assert breaker.SetBoard(board)
    else:
        break_class = task
        assert breaker.SetBoard(break_class)

    details = breaker.Break()
    if details.failures:
        for failure in details.failures:
            print(f"Found unbreakable board for {task}: {failure}")
        # good_boards += details.failures
    # depths[details.max_depth] += 1
    # times[round(10 * details.elapsed_s) / 10] += 1
    # all_details.append((task, details))
    with open(f"tasks-{me}.ndjson", "a") as out:
        summary = details.asdict()
        summary["id"] = task
        out.write(json.dumps(summary))
        out.write("\n")

    return details.failures


def get_breaker(args) -> BreakingBundle:
    """Each thread needs its own Trie, tree builder, boggler and breaker."""
    dims = args.size // 10, args.size % 10
    best_score = args.best_score

    if args.python:
        t = make_py_trie(args.dictionary)
        assert t
        etb = EvalTreeBoggler(t, dims)
        boggler = PyBoggler(t, dims)
    else:
        t = Trie.CreateFromFile(args.dictionary)
        assert t
        etb = TreeBuilders[dims](t)
        boggler = Bogglers[dims](t)

    if args.breaker == "hybrid":
        breaker = HybridTreeBreaker(
            etb, boggler, dims, best_score, switchover_level=args.switchover_level
        )
    elif args.breaker == "ibuckets":
        if args.python:
            etb = PyBucketBoggler(t, dims)
        else:
            etb = BucketBogglers[dims](t)
        breaker = IBucketBreaker(etb, dims, best_score, num_splits=args.num_splits)
    else:
        raise ValueError(args.breaker)
    return BreakingBundle(trie=t, etb=etb, boggler=boggler, breaker=breaker)


def main():
    parser = argparse.ArgumentParser(
        description="Find all 3x3 boggle boards with >=N points",
    )
    parser.add_argument(
        "classes", type=str, help="Space-separated list of letter classes"
    )
    parser.add_argument(
        "best_score",
        type=int,
        help="Print boards with a score >= to this. Filter boards below this. "
        "A higher number will result in a faster run.",
    )
    parser.add_argument(
        "--size",
        type=int,
        choices=(33, 34, 44),
        default=33,
        help="Size of the boggle board.",
    )
    parser.add_argument(
        "--dictionary",
        type=str,
        default="boggle-words.txt",
        help="Path to dictionary file with one word per line. Words must be "
        '"bogglified" via make_boggle_dict.py to convert "qu" -> "q".',
    )
    parser.add_argument(
        "--board_ids",
        help="Comma-separated list of board IDs. Omit to consider all "
        "canonically-rotated boards.",
    )
    parser.add_argument(
        "--max_boards",
        help="Limit the number of boards to consider.",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--random_seed",
        help="Explicitly set the random seed.",
        type=int,
        default=-1,
    )
    parser.add_argument(
        "--num_splits",
        type=int,
        default=4,
        help="Number of partitions to use when breaking a bucket. Only relevant with --breaker=ibuckets.",
    )
    parser.add_argument(
        # TODO: figure out how to set this based on tree size
        "--switchover_level",
        type=int,
        default=4,
        help="Depth at which to switch from lifting choices to exhaustively trying them. Only relevant with --breaker=hybrid.",
    )
    parser.add_argument(
        "--breaker",
        type=str,
        choices=("ibuckets", "hybrid"),
        default="hybrid",
        help="Breaking strategy to use.",
    )
    parser.add_argument(
        "--log_per_board_stats",
        action="store_true",
        help="Log stats on every board, not just a summary at the end.",
    )
    parser.add_argument(
        "--break_class",
        type=str,
        help="Set to a board class to override --random_ids, --max_boards, etc.",
    )
    parser.add_argument(
        "--num_threads",
        type=int,
        default=1,
        help="Number of concurrent breakers to run.",
    )
    parser.add_argument(
        "--python",
        action="store_true",
        help="Use Python implementation of ibuckets instead of C++. This is ~50x slower!",
    )
    args = parser.parse_args()
    if args.random_seed >= 0:
        random.seed(args.random_seed)

    best_score = args.best_score
    assert best_score > 0
    classes = args.classes.split(" ")
    num_classes = len(classes)
    w, h = dims = args.size // 10, args.size % 10
    assert 3 <= w <= 4
    assert 3 <= h <= 4
    max_index = num_classes ** (w * h)

    indices: list[int | str]
    if args.board_ids:
        indices = [int(x) for x in args.board_ids.split(",")]
    elif args.break_class:
        break_class = args.break_class
        assert len(break_class.split(" ")) == w * h
        indices = [break_class]
    else:
        # This gets a more useful, accurate error bar than going in order
        # and filtering inside the main loop.
        start_s = time.time()
        if args.max_boards:
            # This is dramatically faster than slicing the full permutation array.
            oversample = random.sample(range(max_index), k=16 * args.max_boards)
            indices = (
                idx
                for idx in oversample
                if is_canonical_board_id(num_classes, dims, idx)
            )
            indices = [*itertools.islice(indices, args.max_boards)]
        else:
            indices = [
                idx
                for idx in range(0, max_index)
                if is_canonical_board_id(num_classes, dims, idx)
            ]
            random.shuffle(indices)
        print(
            f"Found {len(indices)} canonical boards in {time.time() - start_s:.02f}s."
        )

    start_s = time.time()
    good_boards = []

    pool = multiprocessing.Pool(args.num_threads, break_init, (args,))
    it = pool.imap_unordered(break_worker, indices)

    good_boards = []
    # smoothing=0 means to show the average pace so far, which is the best estimator.
    for winners in tqdm(it, smoothing=0, total=len(indices)):
        good_boards.extend(winners)

    end_s = time.time()

    print(f"Broke {len(indices)} classes in {end_s-start_s:.02f}s.")
    print("All failures:")
    print("\n".join(good_boards))


if __name__ == "__main__":
    main()
