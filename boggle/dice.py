import sys
from collections import defaultdict

DICE = [
    "aeaneg",
    "ahspco",
    "aspffk",
    "objoab",
    "iotmuc",
    "ryvdel",
    "lreixd",
    "eiunes",
    "wngeeh",
    "lnhnrz",
    "tstiyd",
    "owtoat",
    "erttyl",
    "toessi",
    "terwhv",
    "nuihmq",
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
