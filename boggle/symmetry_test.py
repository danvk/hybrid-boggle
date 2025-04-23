from inline_snapshot import snapshot

from boggle.symmetry import (
    all_symmetries,
    canonicalize,
    canonicalize_board,
    flip_x,
    flip_y,
    list_to_matrix,
    mat_to_str,
    rot90,
)


def test_rot90():
    mat = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    expected = [
        [7, 4, 1],
        [8, 5, 2],
        [9, 6, 3],
    ]
    assert rot90(mat) == expected


def test_rot90_asym():
    mat = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
        [10, 11, 12],
    ]
    expected = [
        [10, 7, 4, 1],
        [11, 8, 5, 2],
        [12, 9, 6, 3],
    ]
    assert rot90(mat) == expected


def test_flip_x():
    mat = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    expected = [
        [7, 8, 9],
        [4, 5, 6],
        [1, 2, 3],
    ]
    assert flip_x(mat) == expected


def test_flip_y():
    mat = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    expected = [
        [3, 2, 1],
        [6, 5, 4],
        [9, 8, 7],
    ]
    assert flip_y(mat) == expected


def test_eightfold_sym():
    mat = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    syms = all_symmetries(mat)
    assert len(syms) == 7
    unique = {mat_to_str(sym) for sym in [mat] + syms}
    assert len(unique) == 8


def test_fourfold_sym():
    mat = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
        [10, 11, 12],
    ]

    syms4 = all_symmetries(mat)
    assert len(syms4) == 3
    unique = {mat_to_str(sym) for sym in [mat] + syms4}
    assert len(unique) == 4
    for sym in syms4:
        assert len(sym) == 4
        assert len(sym[0]) == 3


def test_canonicalize():
    mat = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    assert canonicalize(mat) == mat
    for sym in all_symmetries(mat):
        assert canonicalize(sym) == mat


def test_list_to_matrix():
    board = "dnisetalsrep"
    mat = list_to_matrix(board)
    assert mat == [["d", "n", "i", "s"], ["e", "t", "a", "l"], ["s", "r", "e", "p"]]
    assert mat_to_str(mat) == board


def test_all_symmetries34():
    board = "dnisetalsrep"
    mat = list_to_matrix(board)
    assert [mat_to_str(m) for m in all_symmetries(mat)] == snapshot(
        ["srepetaldnis", "sindlatepers", "perslatesind"]
    )


def test_canonicalize_34():
    board = "srebetaldnip"
    mat = list_to_matrix(board)
    assert mat_to_str(mat) == board
    assert mat_to_str(canonicalize(mat)) == snapshot("berslatepind")


# P E R S
# L A T G
# S I N E
# T E R S


def test_canonicalize_board():
    assert canonicalize_board("perslatgsineters") == "perslatgsineters"
    assert canonicalize_board("plsteaiertnrsges") == "perslatgsineters"
    assert canonicalize_board("srepgtalenissret") == "perslatgsineters"
