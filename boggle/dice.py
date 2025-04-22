"""Determine the number of ways to roll a particular Boggle board.

This uses the dice from the original 19
"""

import sys
from collections import defaultdict

# https://www.bananagrammer.com/2013/10/the-boggle-cube-redesign-and-its-effect.html
# "New" Boggle dice, 1987 to ~2008
DICE = [
    "aaeegn",
    "achops",
    "affkps",
    "abjoob",
    "ciimot",
    "delrvy",
    "deilrx",
    "eeinsu",
    "eeghnw",
    "hlnnrz",
    "distty",
    "aoottw",
    "elrtty",
    "eiosst",
    "ehrtuv",
    "himnqu",
]

# "Classic" Boggle dice, 1976 to 1986
CLASSIC_DICE = [
    "aaciot",
    "abilty",
    "abjmoq",
    "acdemp",
    "acelrs",
    "adenvz",
    "ahmors",
    "biforx",
    "denosw",
    "dknotu",
    "eefhiy",
    "egkluy",
    "egintv",
    "ehinps",
    "elpstu",
    "gilruw",
]


# Preprocess: map each letter to dice that contain it
LETTER_TO_DICE = defaultdict(set)
for idx, die in enumerate(DICE):
    for ch in set(die):  # use set to avoid counting same die multiple times
        LETTER_TO_DICE[ch].add(idx)


def count_boggle_arrangements(grid):
    if len(grid) != 16:
        raise ValueError("Grid must be exactly 16 letters")

    used = [False] * 16
    count = 0

    def backtrack(pos, mult):
        nonlocal count
        if pos == 16:
            count += mult
            return

        # TODO: this doesn't consider that a letter could be on the same die multiple times
        letter = grid[pos].lower()
        for die_index in LETTER_TO_DICE.get(letter, []):
            if not used[die_index]:
                used[die_index] = True
                backtrack(pos + 1, mult * DICE[die_index].count(letter))
                used[die_index] = False

    backtrack(0, 1)
    return count


def main():
    for grid in sys.argv[1:]:
        assert len(grid) == 16
        print(grid, count_boggle_arrangements(grid))


if __name__ == "__main__":
    main()
