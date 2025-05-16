#!/usr/bin/env python
"""Enumerate Hamiltonian circuits of the Boggle board."""

from boggle.neighbors import NEIGHBORS


def rec(cell: int, num_left: int, used: list[bool], seq: list[int], neighbors):
    if num_left == 0:
        print(seq)
        return 1  # success! a hamiltonian circuit

    # try each un-visited neighbor
    count = 0
    used[cell] = True
    for neighbor in neighbors[cell]:
        if not used[neighbor]:
            seq.append(neighbor)
            count += rec(neighbor, num_left - 1, used, seq, neighbors)
            seq.pop()

    used[cell] = False
    return count


def main():
    start = 0
    w, h = 2, 2
    n = w * h
    count = rec(start, n - 1, [False] * n, [start], NEIGHBORS[(w, h)])
    print(count)


if __name__ == "__main__":
    main()
