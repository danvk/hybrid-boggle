#!/usr/bin/env python

import argparse
import itertools
import random
import time
from collections import Counter

from cpp_boggle import BucketBoggler33, BucketBoggler34, Trie
from tqdm import tqdm

from boggle.board_id import is_canonical_board_id
from boggle.breaker import BreakDetails, Breaker, merge_details, print_details
from boggle.ibuckets import PyBucketBoggler
from boggle.trie import make_py_trie

Bogglers = {
    (3, 3): BucketBoggler33,
    (3, 4): BucketBoggler34,
}


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
        choices=[33, 34],
        default=33,
        help="Size of the boggle board. 33 or 34.",
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
        help="Number of partitions to use when breaking a bucket.",
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
        "--ibuckets_implementation",
        choices=("C++", "python"),
        default="C++",
        help="Which ibuckets implementation to use. Python is _much_ slower!",
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

    if args.ibuckets_implementation == "python":
        t = make_py_trie(args.dictionary)
        assert t
        bb = PyBucketBoggler(t, dims)
    else:
        t = Trie.CreateFromFile(args.dictionary)
        assert t
        bb = Bogglers[dims](t)

    breaker = Breaker(bb, dims, best_score, num_splits=args.num_splits)
    break_class = None

    if args.board_ids:
        indices = [int(x) for x in args.board_ids.split(",")]
    elif args.break_class:
        break_class = args.break_class
        assert len(break_class.split(" ")) == w * h
        indices = [0]
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

    combined_details = None
    start_s = time.time()
    good_boards = []
    depths = Counter()
    times = Counter()
    log_per_board_stats = args.log_per_board_stats
    all_details: list[tuple[int, BreakDetails]] = []
    # smoothing=0 means to show the average pace so far, which is the best estimator.
    for idx in tqdm(indices, smoothing=0):
        if not break_class:
            breaker.FromId(classes, idx)
        else:
            assert breaker.bb.ParseBoard(break_class)
        details = breaker.Break()
        if details.failures:
            for failure in details.failures:
                print(f"Found unbreakable board for {idx}: {failure}")
            good_boards += details.failures
        depths[details.max_depth] += 1
        times[round(10 * details.elapsed_s) / 10] += 1
        all_details.append((idx, details))
        if log_per_board_stats:
            breaker.FromId(classes, idx)
            print(break_class if break_class else breaker.bb.as_string())
            print_details(details)
        combined_details = (
            details
            if combined_details is None
            else merge_details(combined_details, details)
        )
        if break_class:
            break
    end_s = time.time()

    print(f"Broke {len(indices)} classes in {end_s-start_s:.02f}s.")
    print("All failures:")
    print("\n".join(good_boards))
    print(f"Depths: {depths.most_common()}")
    print(f"Times (s): {times.most_common()}")

    print_details(combined_details)

    all_details.sort()
    with open("/tmp/details.txt", "w") as out:
        for idx, d in all_details:
            out.write(
                f"{idx}\t{d.num_reps}\t{d.max_depth}\t{len(d.failures)}\t{d.elapsed_s}\n"
            )


if __name__ == "__main__":
    main()
