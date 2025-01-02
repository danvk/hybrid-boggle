#!/usr/bin/env python
"""Filter a word list to just valid Boggle words, and replace "qu" with "q"."""

import fileinput


def is_boggle_word(word: str):
    size = len(word)
    if size < 3 or size > 17:
        return False
    for i, let in enumerate(word):
        if let < "a" or let > "z":
            return False
        if let == "q" and (i + 1 >= size or word[i + 1] != "u"):
            return False
    return True


def bogglify_word(word: str) -> str | None:
    if not is_boggle_word(word):
        return None
    return word.replace("qu", "q")


def main():
    for line in fileinput.input():
        line = line.strip()
        word = bogglify_word(line)
        if word:
            print(word)


if __name__ == "__main__":
    main()
