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


def class_for_board(buckets: list[int], classes: list[str], board: list[int]) -> str:
    return ' '.join(classes[buckets[b]] for b in board)


def bucket_score(bb: BucketBoggler33, buckets: list[int], boards: list[list[int]]) -> float:
    """Score a bucketing of the letters."""
    classes = realize_bucket(buckets)
    scores = []
    for idx in boards:
        bd = class_for_board(buckets, classes, idx)
        bb.ParseBoard(bd)
        scores.append(bb.UpperBound(1_000_000))
    return sum(scores) / len(scores)


def class_to_buckets(classes: str) -> list[int]:
    """Convert a string of classes to a list of buckets."""
    out = {}
    for i, letters in enumerate(classes.split()):
        for c in letters:
            out[c] = i
    return [out[c] for c in 'abcdefghijklmnopqrstuvwxyz']


def main():
    random.seed(2025)
    t = Trie.CreateFromFile("boggle-words.txt")
    assert t
    num_classes = 4
    w, h = 3, 3
    bb = BucketBoggler33(t)

    boards = [
        [
            random.randint(0, 25)
            for _ in range(w * h)
        ]
        for _ in range(10)
    ]

    manual = 'bdfgjvwxzq aeiou lnrsy chkmpt'
    manual_buckets = class_to_buckets(manual)
    # print(manual_buckets)
    # print(realize_bucket(manual_buckets))
    # assert realize_bucket(manual_buckets) == manual.split()
    score = bucket_score(bb, manual_buckets, boards)
    print(f"Manual score: {score}")

    init = random_buckets(num_classes)
    print(f"Initial: {realize_bucket(init)}")
    score = bucket_score(bb, init, boards)
    print(f"Initial score: {score}")

    for i in range(1000):
        new = mutate_buckets(init, num_classes)
        new_score = bucket_score(bb, new, boards)
        if new_score < score:
            init = new
            score = new_score
            print(f"{i:05} New best: {score} {realize_bucket(init)}")


if __name__ == "__main__":
    main()
