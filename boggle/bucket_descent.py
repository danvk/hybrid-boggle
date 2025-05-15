#!/usr/bin/env python3
"""Try to find a good split of the letters into buckets.

2: aeiosuy bcdfghjklmnpqrtvwxz (12656.0)
3: aeijou bcdfgmpqvwxz hklnrsty (2689.8)
4: aeiou bcfhpst qxyz dgjklmnrvw (849.9)
5: aejsv bcfgkmpt dhlnrw iou qxyz (437.5)

I've been doing most of my analysis with this bucketing (which excludes q):
4: bdfgjvwxz aeiou lnrsy chkmpt

This adds the q:
4: bdfgjqvwxz aeiou lnrsy chkmpt
"""

import random

from cpp_boggle import BucketBoggler33, Trie


def realize_bucket(buckets: list[int]) -> list[str]:
    """Convert a bucketing of the letters to a string for ibuckets."""
    out = {}
    for i, b in enumerate(buckets):
        out.setdefault(b, []).append(i)
    return ["".join(chr(ord("a") + i) for i in out[b]) for b in range(len(out))]


def random_buckets(n: int) -> list[int]:
    """Splits a-z into n buckets, at random."""
    buckets = [random.randint(0, n - 1) for _ in range(26)]
    for i in range(0, n):
        if i not in buckets:
            buckets[random.randint(0, 25)] = i
    return buckets


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
    return " ".join(classes[buckets[b]] for b in board)


def bucket_score(
    bb: BucketBoggler33, buckets: list[int], boards: list[list[int]]
) -> float:
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
    return [out[c] for c in "abcdefghijklmnopqrstuvwxyz"]


def main():
    random.seed(2025)
    t = Trie.create_from_file("wordlists/enable2k.txt")
    assert t
    num_classes = 5
    w, h = 3, 3
    bb = BucketBoggler33(t)

    boards = [[random.randint(0, 25) for _ in range(w * h)] for _ in range(10)]

    # manual = "bdfgjvwxzq aeiou lnrsy chkmpt"
    # manual = "aeiou bcdfghjklmnpqrstvwxyz"
    # manual = "aeiosuy bcdfghjklmnpqrtvwxz"
    manual = "aeiou bfgpst xyz djlmnrvw chkq"
    manual_buckets = class_to_buckets(manual)
    # print(manual_buckets)
    # print(realize_bucket(manual_buckets))
    # assert realize_bucket(manual_buckets) == manual.split()
    score = bucket_score(bb, manual_buckets, boards)
    print(f"Manual score: {score}")

    for _ in range(10):
        init = random_buckets(num_classes)
        print(f"Initial: {realize_bucket(init)}")
        score = bucket_score(bb, init, boards)
        print(f"Initial score: {score}")

        last_improvement = 0
        for i in range(20_000):
            new = mutate_buckets(init, num_classes)
            new_score = bucket_score(bb, new, boards)
            if new_score < score:
                init = new
                score = new_score
                last_improvement = i
                print(f"{i:05} New best: {score} {realize_bucket(init)}")
            elif i - last_improvement > 500:
                print("(stall)")
                break
        print("\n----\n")


if __name__ == "__main__":
    main()
