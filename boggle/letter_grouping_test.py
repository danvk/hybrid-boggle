from boggle.letter_grouping import get_letter_map, reverse_letter_map, ungroup_letters


def test_get_letter_map():
    letter_grouping = "cz uxj mk wv fb gy"
    assert get_letter_map(letter_grouping) == {
        "a": "a",
        "b": "f",
        "c": "c",
        "d": "d",
        "e": "e",
        "f": "f",
        "g": "g",
        "h": "h",
        "i": "i",
        "j": "u",
        "k": "m",
        "l": "l",
        "m": "m",
        "n": "n",
        "o": "o",
        "p": "p",
        "q": "q",
        "r": "r",
        "s": "s",
        "t": "t",
        "u": "u",
        "v": "w",
        "w": "w",
        "x": "u",
        "y": "g",
        "z": "c",
    }


def test_reverse_letter_map():
    letter_grouping = "cz uxj mk wv fb gy"
    mapping = get_letter_map(letter_grouping)
    rev = reverse_letter_map(mapping)
    assert rev["c"] == "cz"
    assert rev["a"] == "a"
    assert "b" not in rev


def test_ungroup_letters():
    letter_grouping = "cz uxj mk wv fb gy"
    mapping = get_letter_map(letter_grouping)
    rev = reverse_letter_map(mapping)
    board = "ceu"
    assert {*ungroup_letters(board, rev)} == {
        "ceu",
        "zeu",
        "cex",
        "zex",
        "cej",
        "zej",
    }

    board = "perslatesind"
    boards_to_test = [board]
    it = (b for board in boards_to_test for b in ungroup_letters(board, rev))
    assert board in [*it]
