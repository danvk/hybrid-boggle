#!/usr/bin/env python

import argparse
import glob
import itertools
import json
import math
import multiprocessing
import random
import time
from dataclasses import dataclass

from tqdm import tqdm

from boggle.args import (
    add_standard_args,
    get_trie_and_boggler_from_args,
    get_trie_from_args,
)
from boggle.board_id import from_board_id, is_canonical_board_id, parse_classes
from boggle.boggler import PyBoggler
from boggle.breaker import HybridTreeBreaker
from boggle.dimensional_bogglers import (
    BucketBogglers,
    cpp_orderly_tree_builder,
)
from boggle.ibucket_breaker import IBucketBreaker
from boggle.ibuckets import PyBucketBoggler
from boggle.letter_grouping import filter_to_canonical
from boggle.orderly_tree_builder import OrderlyTreeBuilder
from boggle.trie import PyTrie, get_letter_map


@dataclass
class BreakingBundle:
    """Only the breaker is needed, but this helps keep its deps from being GC'd."""

    trie: PyTrie
    boggler: PyBoggler
    etb: OrderlyTreeBuilder
    breaker: IBucketBreaker | HybridTreeBreaker
    ungrouped_trie: PyTrie


def get_process_id():
    ids = multiprocessing.current_process()._identity
    if len(ids) == 0:
        return 1  # single-threaded case
    assert len(ids) == 1
    return ids[0]


def break_init(args, needs_canonical_filter):
    bundle = get_breaker(args)
    # See https://stackoverflow.com/a/30816116/388951 for this trick to avoid a global
    break_worker.bundle = bundle
    break_worker.args = args
    break_worker.needs_canonical_filter = needs_canonical_filter
    me = get_process_id()
    with open(f"tasks-{me}.ndjson", "w"):
        pass


def break_worker(task: str | int):
    bundle: BreakingBundle = break_worker.bundle
    breaker = bundle.breaker
    args = break_worker.args
    needs_canonical_filter = break_worker.needs_canonical_filter
    me = get_process_id()

    best_score = args.best_score
    assert best_score > 0
    dims = args.size // 10, args.size % 10
    classes = parse_classes(args.classes, dims)
    if args.letter_grouping:
        letter_map = get_letter_map(args.letter_grouping)
        classes = [
            [filter_to_canonical(cls, letter_map) for cls in cell_classes]
            for cell_classes in classes
        ]
        # print(f'Filtered {args.classes} -> {" ".join(classes)}')

    if isinstance(task, int):
        if needs_canonical_filter and not is_canonical_board_id(
            [len(c) for c in classes], dims, task
        ):
            return []
        board = from_board_id(classes, task)
    else:
        board = task

    assert breaker.SetBoard(board)
    details = breaker.Break()
    if details.failures:
        for failure in details.failures:
            print(f"Found unbreakable board for {task}: {failure}")
        # good_boards += details.failures
    # depths[details.max_depth] += 1
    # times[round(10 * details.elapsed_s) / 10] += 1
    # all_details.append((task, details))
    with open(f"tasks-{me}.ndjson", "a") as out:
        # It's convenient to have id first when viewing.
        summary = {"id": task, **details.asdict()}
        if args.omit_times:
            del summary["elapsed_s"]
            del summary["free_time_s"]
            del summary["secs_by_level"]
        out.write(json.dumps(summary))
        out.write("\n")
        if args.log_per_board_stats:
            print(f"{task}: {board}")
            print(json.dumps(summary, indent=2))

    return details.failures


def get_breaker(args) -> BreakingBundle:
    """Each thread needs its own Trie, tree builder, boggler and breaker."""
    dims = args.size // 10, args.size % 10
    best_score = args.best_score

    # With grouping, HybridTreeBreaker needs an ungrouped boggler but a grouped Trie.
    ungrouped_trie = None
    if args.letter_grouping:
        ungrouped_trie, boggler = get_trie_and_boggler_from_args(args, no_grouping=True)
        t = get_trie_from_args(args)
    else:
        t, boggler = get_trie_and_boggler_from_args(args)

    builder = OrderlyTreeBuilder if args.python else cpp_orderly_tree_builder
    etb = builder(t, dims)

    if args.breaker == "hybrid":
        switchover_level = 2
        if args.switchover_level is not None:
            switchover_level = args.switchover_level
        elif args.switchover_sizes:
            switchover_level = [
                tuple(int(x) for x in pair.split(":"))
                for pair in args.switchover_sizes.split(",")
            ]
        breaker = HybridTreeBreaker(
            etb,
            boggler,
            dims,
            best_score,
            switchover_level=switchover_level,
            log_breaker_progress=args.log_breaker_progress,
            letter_grouping=args.letter_grouping,
        )
    elif args.breaker == "ibuckets":
        if args.python:
            etb = PyBucketBoggler(t, dims)
        else:
            etb = BucketBogglers[dims](t)
        breaker = IBucketBreaker(etb, dims, best_score, num_splits=args.num_splits)
    else:
        raise ValueError(args.breaker)
    return BreakingBundle(
        trie=t, etb=etb, boggler=boggler, breaker=breaker, ungrouped_trie=ungrouped_trie
    )


def main():
    parser = argparse.ArgumentParser(
        description="Find all MxN boggle boards with >=P points",
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
    add_standard_args(parser, random_seed=True, python=True)
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
        "--num_splits",
        type=int,
        default=4,
        help="Number of partitions to use when breaking a bucket. Only relevant with --breaker=ibuckets.",
    )
    switchovers = parser.add_mutually_exclusive_group()
    switchovers.add_argument(
        "--switchover_level",
        type=int,
        default=None,
        help="Depth at which to switch from lifting choices to exhaustively trying them. "
        "Default is 2, unless you set --switchover_sizes. Only relevant with --breaker=hybrid.",
    )
    switchovers.add_argument(
        "--switchover_sizes",
        type=str,
        default=None,
        help='Initial size -> switchover map. Format is "switch:size,switch:size". For example, '
        '"2:100,4:1000" would use switchover=0 for 0-99, 2 for 100-999, and 4 for 1000+.',
    )
    parser.add_argument(
        "--breaker",
        type=str,
        choices=("ibuckets", "hybrid"),
        default="hybrid",
        help="Breaking strategy to use.",
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
        "--resume_from",
        type=str,
        help="Glob pattern of ndjson output files from a previous run.",
    )
    parser.add_argument(
        "--log_per_board_stats",
        action="store_true",
        help="Log stats on every board to stdout, rather just to an ndjson file.",
    )
    parser.add_argument(
        "--log_breaker_progress",
        action="store_true",
        help="Log progress and stats during breaking, which may slow it down.",
    )
    parser.add_argument(
        "--omit_times",
        action="store_true",
        help="Omit times from logging, to get deterministic output.",
    )
    args = parser.parse_args()
    if args.random_seed >= 0:
        random.seed(args.random_seed)

    best_score = args.best_score
    assert best_score > 0
    w, h = dims = args.size // 10, args.size % 10
    assert 3 <= w <= 4
    assert 3 <= h <= 4
    classes = parse_classes(args.classes, dims)
    assert len(classes) == w * h
    num_classes = [len(c) for c in classes]
    max_index = math.prod(num_classes)

    completed_ids = set()
    if args.resume_from:
        n_files = 0
        for filename in glob.glob(args.resume_from):
            n_files += 1
            with open(filename) as input:
                for line in input:
                    task = json.loads(line)
                    completed_ids.add(task["id"])
        print(f"Recovered {len(completed_ids)} completed IDs from {n_files} files.")

    indices: list[int | str]
    needs_canonical_filter = False
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
                # if is_canonical_board_id(num_classes, dims, idx)
            ]
            random.shuffle(indices)
            # Filtering on the workers results in faster startup.
            needs_canonical_filter = True
        indices = [idx for idx in indices if idx not in completed_ids]
        boards_type = "total" if needs_canonical_filter else "canonical"
        print(
            f"Found {len(indices)} {boards_type} boards in {time.time() - start_s:.02f}s."
        )

    start_s = time.time()
    good_boards = []

    if args.num_threads > 1:
        pool = multiprocessing.Pool(
            args.num_threads, break_init, (args, needs_canonical_filter)
        )
        it = pool.imap_unordered(break_worker, indices)
    else:
        # This keeps stack traces simpler in the single-threaded case.
        break_init(args, needs_canonical_filter)
        it = (break_worker(task) for task in indices)

    good_boards = []
    # smoothing=0 means to show the average pace so far, which is the best estimator.
    for winners in tqdm(it, smoothing=0, total=len(indices)):
        good_boards.extend(winners)

    end_s = time.time()

    if not args.omit_times:
        print(f"Broke {len(indices)} classes in {end_s-start_s:.02f}s.")
    print(f"Found {len(good_boards)} breaking failure(s):")
    print("\n".join(good_boards))


if __name__ == "__main__":
    main()
