#!/usr/bin/env python

import argparse
import glob
import itertools
import json
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
from boggle.board_id import from_board_id, is_canonical_board_id
from boggle.boggler import PyBoggler
from boggle.breaker import (
    HybridTreeBreaker,
    IBucketBreaker,
)
from boggle.dimensional_bogglers import (
    BucketBogglers,
    cpp_orderly_tree_builder,
    cpp_tree_builder,
)
from boggle.eval_tree import EvalTreeBoggler
from boggle.ibuckets import PyBucketBoggler
from boggle.orderly_tree_builder import OrderlyTreeBuilder
from boggle.trie import PyTrie, get_letter_map


@dataclass
class BreakingBundle:
    """Only the breaker is needed, but this helps keep its deps from being GC'd."""

    trie: PyTrie
    boggler: PyBoggler
    etb: EvalTreeBoggler
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
    classes = args.classes.split(" ")
    dims = args.size // 10, args.size % 10

    if isinstance(task, int):
        if needs_canonical_filter and not is_canonical_board_id(
            len(classes), dims, task
        ):
            return []
        board = from_board_id(classes, dims, task)
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
        summary = details.asdict()
        if args.omit_times:
            del summary["elapsed_s"]
            del summary["free_time_s"]
            del summary["secs_by_level"]
        summary["id"] = task
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

    # (args.python, args.tree_builder)
    builder = {
        (True, "orderly"): OrderlyTreeBuilder,
        (True, "natural"): EvalTreeBoggler,
        (False, "orderly"): cpp_orderly_tree_builder,
        (False, "natural"): cpp_tree_builder,
    }
    etb = builder[(args.python, args.tree_builder)](t, dims)

    if args.breaker == "hybrid":
        breaker = HybridTreeBreaker(
            etb,
            boggler,
            dims,
            best_score,
            switchover_level=args.switchover_level,
            free_after_score=args.free_after_score,
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
        "--tree_builder",
        choices=("natural", "orderly"),
        default="natural",
        help="Tree builder to use.",
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
        "--free_after_score",
        action="store_true",
        help="Wait to free memory until after score_with_forces in HybridBreaker. "
        "This is a ~5%% performance hit but significantly reduces the time that memory is held.",
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
    classes = args.classes.split(" ")
    num_classes = len(classes)
    w, h = dims = args.size // 10, args.size % 10
    assert 3 <= w <= 4
    assert 3 <= h <= 4
    max_index = num_classes ** (w * h)

    if args.letter_grouping:
        letter_map = get_letter_map(args.letter_grouping)
        for lets in classes:
            for c in lets:
                assert letter_map[c] == c, f"Letter classes must be canonical ({c})"

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
