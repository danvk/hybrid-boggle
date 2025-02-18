import itertools


def get_letter_map(letter_grouping: str) -> dict[str, str]:
    """Returns a dict from letter -> canonical letter."""
    letter_map = {}
    for chunk in letter_grouping.split(" "):
        canonical = chunk[0]
        for alternate in chunk[1:]:
            letter_map[alternate] = canonical
    for i in range(26):
        letter = chr(ord("a") + i)
        if letter not in letter_map:
            letter_map[letter] = letter
    return letter_map


def ungroup_letters(board: str, reverse_letter_grouping: dict[str, str]):
    # board is a string containing canonical letters.
    # reverse_letter_grouping maps canonical characters to all the characters that are mapped onto them.
    # This yields each possible string that would be mapped to board.

    groups = [reverse_letter_grouping[char] for char in board]
    for combination in itertools.product(*groups):
        yield "".join(combination)


def reverse_letter_map(letter_map: dict[str, str]):
    out = {}
    for k, v in letter_map.items():
        out.setdefault(v, "")
        out[v] += k
    for k in out:
        out[k] = "".join(sorted(out[k]))
    return out


def filter_to_canonical(word: str, letter_map: dict[str, str]):
    return "".join(letter for letter in word if letter_map[letter] == letter)
