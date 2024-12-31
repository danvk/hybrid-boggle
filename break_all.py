#!/usr/bin/env python

import argparse
import itertools
import random
import time
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from example import BucketBoggler33, BucketBoggler34, Trie
from tqdm import tqdm

from board_id import from_board_id, is_canonical_board_id


@dataclass
class BreakDetails:
    max_depth: int
    num_reps: int
    start_time_s: float
    elapsed_s: float
    failures: list[str]


SPLIT_ORDER_33 = (4, 5, 3, 1, 7, 0, 2, 6, 8)


def to_idx(x, y):
    return x * 4 + y


SPLIT_ORDER_34 = tuple(
    to_idx(x, y)
    for x, y in (
        (1, 1),
        (1, 2),  # middle
        (0, 1),
        (2, 1),
        (0, 2),
        (2, 2),  # middle sides
        (1, 0),
        (1, 3),  # top/bottom middle
        (0, 0),
        (2, 0),
        (0, 3),
        (2, 3),  # corners
    )
)
assert len(SPLIT_ORDER_34) == 12

SPLIT_ORDER = {
    (3, 3): SPLIT_ORDER_33,
    (3, 4): SPLIT_ORDER_34,
}
Bogglers = {
    (3, 3): BucketBoggler33,
    (3, 4): BucketBoggler34,
}

type BucketBoggler = BucketBoggler33 | BucketBoggler34


class Breaker:
    def __init__(self, boggler: BucketBoggler, dims: tuple[int, int], best_score: int):
        self.bb = boggler
        self.best_score = best_score
        self.details_ = None
        self.elim_ = 0
        self.orig_reps_ = 0
        self.dims = dims
        self.split_order = SPLIT_ORDER[dims]

    def FromId(self, classes, idx: int):
        board = from_board_id(classes, self.dims, idx)
        return self.bb.ParseBoard(board)

    def Break(self) -> BreakDetails:
        self.details_ = BreakDetails(
            max_depth=0,
            num_reps=0,
            elapsed_s=0.0,
            start_time_s=0.0,
            failures=[],
        )
        self.elim_ = 0
        self.orig_reps_ = self.bb.NumReps()
        self.details_.start_time_s = time.time()
        self.AttackBoard()
        self.details_.elapsed_s = time.time() - self.details_.start_time_s
        self.details_.num_reps = self.orig_reps_
        # TODO: debug output
        return self.details_

    def PickABucket(self, level: int) -> list[str]:
        pick = -1
        splits = []

        # TODO: lots of comments in C++ source with ideas for exploration here.
        for order in self.split_order:
            # TODO: could do this all in Python to avoid C++ <-> Py
            if len(self.bb.Cell(order)) > 1:
                pick = order
                break

        if pick == -1:
            return pick, splits

        cell = self.bb.Cell(pick)
        cell_len = len(cell)
        if cell_len == 26:
            # TODO: is this ever useful?
            splits = ["aeiou", "sy", "bdfgjkmpvwxzq", "chlnrt"]
        elif cell_len >= 9:
            # TODO: 4 splits is an interesting choice here
            splits = ["".join(split) for split in even_split(cell, 4)]
        else:
            splits = [*cell]

        return pick, splits

    def SplitBucket(self, level: int) -> None:
        cell, splits = self.PickABucket(level)
        if cell == -1:
            # it's just a board
            board = self.bb.as_string().replace(" ", "")
            print(f"Unable to break board: {board}")
            self.details_.failures.append(board)
            return

        bd = self.bb.as_string().split(" ")
        for i, split in enumerate(splits):
            bd[cell] = split
            # C++ version uses ParseBoard() + Cell() here.
            assert self.bb.ParseBoard(" ".join(bd))
            self.AttackBoard(level + 1, i + 1, len(splits))

    def AttackBoard(self, level: int = 0, num: int = 1, out_of: int = 1) -> None:
        # TODO: debug output
        # reps = self.bb.NumReps()
        if self.bb.UpperBound(self.best_score) <= self.best_score:
            self.elim_ += self.bb.NumReps()
            self.details_.max_depth = max(self.details_.max_depth, level)
        else:
            self.SplitBucket(level)


# TODO: there's probably a more concise way to express this.
# Or maybe not https://stackoverflow.com/a/54802737/388951
def even_split[T](xs: Sequence[T], num_buckets: int) -> list[list[T]]:
    splits = [[]]
    length = len(xs)
    for i, x in enumerate(xs):
        if num_buckets * i >= (len(splits) * length):
            splits.append([])
        splits[-1].append(x)
    return splits


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
    args = parser.parse_args()
    if args.random_seed >= 0:
        random.seed(args.random_seed)

    best_score = args.best_score
    assert best_score > 0
    t = Trie.CreateFromFile(args.dictionary)
    assert t
    classes = args.classes.split(" ")
    num_classes = len(classes)
    w, h = dims = args.size // 10, args.size % 10
    assert 3 <= w <= 4
    assert 3 <= h <= 4
    max_index = num_classes ** (w * h)

    bb = Bogglers[dims](t)
    breaker = Breaker(bb, dims, best_score)

    if args.board_ids:
        indices = [int(x) for x in args.board_ids.split(",")]
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
    depths = Counter()
    times = Counter()
    all_details: list[tuple[int, BreakDetails]] = []
    # smoothing=0 means to show the average pace so far, which is the best estimator.
    for idx in tqdm(indices, smoothing=0):
        breaker.FromId(classes, idx)
        details = breaker.Break()
        if details.failures:
            for failure in details.failures:
                print(f"Found unbreakable board for {idx}: {failure}")
            good_boards += details.failures
        depths[details.max_depth] += 1
        times[round(10 * details.elapsed_s) / 10] += 1
        all_details.append((idx, details))
    end_s = time.time()

    print(f"Broke {len(indices)} classes in {end_s-start_s:.02f}s.")
    print("All failures:")
    print("\n".join(good_boards))
    print(f"Depths: {depths.most_common()}")
    print(f"Times (s): {times.most_common()}")

    all_details.sort()
    with open("/tmp/details.txt", "w") as out:
        for idx, d in all_details:
            out.write(
                f"{idx}\t{d.num_reps}\t{d.max_depth}\t{len(d.failures)}\t{d.elapsed_s}\n"
            )


if __name__ == "__main__":
    main()
