import functools

import pytest
from cpp_boggle import Trie
from inline_snapshot import snapshot

from boggle.boggler import SCORES, PyBoggler
from boggle.dimensional_bogglers import cpp_boggler
from boggle.trie import make_py_trie


@functools.cache
def get_py_trie():
    return make_py_trie("wordlists/enable2k.txt")


@functools.cache
def get_cpp_trie():
    return Trie.create_from_file("wordlists/enable2k.txt")


PARAMS = [
    (get_py_trie, PyBoggler),
    (get_cpp_trie, cpp_boggler),
]


# These should all match performance-boggle's solve binary


@pytest.mark.parametrize("get_trie, Boggler", PARAMS)
def test33(get_trie, Boggler):
    t = get_trie()
    b = Boggler(t, (3, 3))
    assert b.score("abcdefghi") == 20
    assert b.score("streaedlp") == 545


# This tests proper orientation: 3x4 vs 4x3, row- vs. column-major.
@pytest.mark.parametrize("get_trie, Boggler", PARAMS)
def test34(get_trie, Boggler):
    t = get_trie()
    b = Boggler(t, (3, 4))

    # A E I
    # B F J
    # C G K
    # D H L
    assert b.score("abcdefghijkl") == 1

    # A B C
    # D E F
    # G H I
    # J K L
    assert b.score("adgjbehkcfil") == 34
    assert b.score("perslatesind") == 1651


@pytest.mark.parametrize("get_trie, Boggler", PARAMS)
def test44(get_trie, Boggler):
    t = get_trie()
    b = Boggler(t, (4, 4))
    assert b.score("abcdefghijklmnop") == 18
    assert b.score("perslatgsineters") == 3625


@pytest.mark.parametrize("get_trie, Boggler", PARAMS)
def test55(get_trie, Boggler):
    t = get_trie()
    b = Boggler(t, (5, 5))
    assert b.score("sepesdsracietilmanesligdr") == 10406
    assert b.score("ititinstietbulseutiarsaba") == 810


@pytest.mark.parametrize("get_trie, Boggler", PARAMS)
def test_find_words(get_trie, Boggler):
    t = get_trie()
    b = Boggler(t, (4, 4))
    assert (b.find_words("abcdefghijklmnop", False)) == snapshot(
        [
            [5, 8, 4],
            [5, 8, 13],
            [5, 8, 13, 10],
            [5, 8, 13, 14],
            [6, 11, 14, 15],
            [8, 13, 10],
            [9, 8, 13],
            [9, 8, 13, 10],
            [10, 13, 8, 5, 4],
            [10, 13, 14, 15],
            [10, 14, 15],
            [11, 14, 15],
            [12, 8, 13, 10],
            [13, 8, 12],
            [15, 11, 14, 13, 10],
            [15, 14, 11],
        ]
    )

    three_board = "abc.def.gei....."
    three_uniq = [path for path in b.find_words(three_board, False) if len(path) > 3]
    words_uniq = ["".join(three_board[i] for i in path) for path in three_uniq]
    three_multi = [path for path in b.find_words(three_board, True) if len(path) > 3]
    words_multi = ["".join(three_board[i] for i in path) for path in three_multi]
    assert three_uniq == snapshot(
        [
            [0, 1, 5, 4],
            [1, 0, 4, 5],
            [1, 0, 4, 8, 5],
            [1, 5, 0, 4],
            [1, 5, 9, 6],
            [2, 5, 4, 9],
            [4, 5, 6, 10],
            [5, 4, 8, 9],
            [6, 5, 9, 4],
            [8, 5, 9, 4],
        ]
    )
    assert words_uniq == snapshot(
        [
            "abed",
            "bade",
            "badge",
            "bead",
            "beef",
            "cede",
            "defi",
            "edge",
            "feed",
            "geed",
        ]
    )
    assert three_multi == snapshot(
        [
            [0, 1, 5, 4],
            [1, 0, 4, 5],
            [1, 0, 4, 8, 5],
            [1, 0, 4, 8, 9],
            [1, 0, 4, 9],
            [1, 5, 0, 4],
            [1, 5, 9, 6],
            [2, 5, 4, 9],
            [4, 5, 6, 10],
            [4, 9, 6, 10],
            [5, 4, 8, 9],
            [6, 5, 9, 4],
            [8, 5, 9, 4],
        ]
    )

    assert set(words_multi) == set(words_uniq)

    b3 = Boggler(t, (3, 3))
    three_board = "abcdefgei"
    paths_multi = [path for path in b3.find_words(three_board, True) if len(path) > 3]
    words_multi3 = ["".join(three_board[i] for i in path) for path in paths_multi]
    assert sorted(words_multi) == sorted(words_multi3)


@pytest.mark.parametrize("get_trie, Boggler", PARAMS)
def test_multiboggle_score(get_trie, Boggler):
    t = get_trie()
    # {bee, fee, beef} * 2
    b = Boggler(t, (3, 3))
    assert PyBoggler.multiboggle_score(b, "ee.bf.ee.") == 6
    # assert b.score("ee.bf.ee.") == 3

    b = Boggler(t, (4, 4))
    assert PyBoggler.multiboggle_score(b, "eeesrvrreeesrsrs") == 13253
    assert b.score("eeesrvrreeesrsrs") == 189

    q_bd = "besbrrneeeehbteq"
    assert PyBoggler.multiboggle_score(b, q_bd) == 965

    q_bd_score = b.score(q_bd)
    assert q_bd_score == 201
    words = b.find_words(q_bd, False)
    assert (
        sum(
            SCORES[sum(2 if q_bd[cell] == "q" else 1 for cell in path)]
            for path in words
        )
        == q_bd_score
    )
