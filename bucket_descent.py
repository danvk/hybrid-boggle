#!/usr/bin/env python3
"""Try to find a good split of the letters into buckets."""

import random
from example import Trie, BucketBoggler33
from board_id import from_board_id


def realize_bucket(buckets: list[int]) -> list[str]:
    """Convert a bucketing of the letters to a string for ibuckets."""
    out = {}
    for i, b in enumerate(buckets):
        out.setdefault(b, []).append(i)
    return ["".join(chr(ord('a') + i) for i in out[b]) for b in range(len(out))]


def random_buckets(n: int) -> list[int]:
    """Splits a-z into n buckets, at random."""
    return [random.randint(0, n - 1) for _ in range(26)]


def mutate_buckets(buckets: list[int], n: int) -> list[int]:
    """Apply a random mutation to the list of buckets."""
    out = [*buckets]
    while True:
        idx = random.randint(0, 25)
        old = out[idx]
        while True:
            c = random.randint(0, n - 1)
            if c != old:
                break
        if len([b for b in out if b == old]) == 1:
            continue  # this would eliminate a bucket
        out[idx] = c
        if random.random() < 0.75:
            break
    return out


def bucket_score(bb: BucketBoggler33, buckets: list[int], board_indices: list[int]) -> float:
    """Score a bucketing of the letters."""
    classes = realize_bucket(buckets)
    return score_for_classes(bb, classes, board_indices)


def score_for_classes(bb: BucketBoggler33, classes: str, board_indices: list[int]) -> float:
    scores = []
    for idx in board_indices:
        bd = from_board_id(classes, (3, 3), idx)
        bb.ParseBoard(bd)
        scores.append(bb.UpperBound(1_000_000))
    return sum(scores) / len(scores)


def main():
    random.seed(2025)
    t = Trie.CreateFromFile("boggle-words.txt")
    assert t
    num_classes = 4
    w, h = 3, 3
    max_index = num_classes ** (w*h)
    bb = BucketBoggler33(t)

    board_indices = [
        random.randint(0, max_index)
        for _ in range(10)
    ]

    score = score_for_classes(bb, 'bdfgjvwxz aeiou lnrsy chkmpt', board_indices)
    print(f"Manual score: {score}")

    init = random_buckets(num_classes)
    print(f"Initial: {realize_bucket(init)}")
    score = bucket_score(bb, init, board_indices)
    print(f"Initial score: {score}")

    for i in range(1000):
        new = mutate_buckets(init, num_classes)
        new_score = bucket_score(bb, new, board_indices)
        if new_score < score:
            init = new
            score = new_score
            print(f"{i:05} New best: {score} {realize_bucket(init)}")


if __name__ == "__main__":
    main()
