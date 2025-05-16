#!/usr/bin/env python
"""Enumerate Hamiltonian circuits of the Boggle board.

- 2x2: 6 possible paths
- 2x3: 28 = 20 + 8 possible paths
- 3x3: 220 = 138 + 50 + 32 possible paths
- 3x4: 2757 = 1309 + 612 + 470 + 366
- 4x4: 68115 = 37948 + 17681 + 12486
"""

from boggle.neighbors import NEIGHBORS


def rec(cell: int, num_left: int, used: list[bool], seq: list[int], neighbors):
    if num_left == 0:
        # print(seq)
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
    w, h = 4, 4
    n = w * h
    total = 0
    # for start in (0, 1, 4):  # 3x3
    # for start in (0, 1, 4, 5):  # 3x4
    for start in (0, 1, 5):  # 4x4
        count = rec(start, n - 1, [False] * n, [start], NEIGHBORS[(w, h)])
        print(start, count)
        total += count
    print((w, h), total)


if __name__ == "__main__":
    main()
