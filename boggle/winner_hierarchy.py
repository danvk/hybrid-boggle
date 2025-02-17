#!/usr/bin/env python
"""Determine the relationship between high-scoring boards."""

import fileinput

from boggle.symmetry import all_symmetries, list_to_matrix, mat_to_str


def distance(a: str, b: str):
    return sum(1 if ac != bc else 0 for ac, bc in zip(a, b))


def symmetry_group(bd: str):
    mat = list_to_matrix(bd)
    no_rotations = len(mat) != len(mat[0])
    return [
        bd,
        *(mat_to_str(m) for m in all_symmetries(mat, no_rotations=no_rotations)),
    ]


def board_distance(a: str, b: str):
    """Hamming distance, allowing rotations."""
    return min(distance(a, br) for br in symmetry_group(b))


def closest(needle: str, haystack: list[str]):
    return min(haystack, key=lambda b: board_distance(needle, b))


def main():
    board_to_score = dict[str, int]()
    for line in fileinput.input():
        board, score_str = line.strip().split(": ")
        score = int(score_str)
        board_to_score[board] = score

    boards = [*board_to_score]
    boards.sort(key=lambda b: -board_to_score[b])

    parents = dict[str, str]()

    for i, board in enumerate(boards):
        score = board_to_score[board]
        if i == 0:
            print(f"{board}\t{score}")
            parents[board] = ""
            continue
        parent = closest(board, boards[:i])
        d = board_distance(board, parent)
        parent_score = board_to_score[parent]
        print("\t".join(str(x) for x in (board, score, d, parent, parent_score)))


if __name__ == "__main__":
    main()
