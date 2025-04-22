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

LETTER_TO_DICE = defaultdict(list)
for i, letters in enumerate(DICE):
    for letter in letters:
        LETTER_TO_DICE[letter].append(i)


def main():
    (board,) = sys.argv[1:]


if __name__ == "__main__":
    main()
