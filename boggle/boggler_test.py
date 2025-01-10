import functools

from boggle.boggler import PyBoggler
from boggle.trie import make_py_trie


@functools.cache
def get_trie():
    return make_py_trie("boggle-words.txt")


# These should all match performance-boggle's solve binary


def test33():
    t = get_trie()
    b = PyBoggler(t, (3, 3))
    b.set_board("abcdefghi")
    assert b.score() == 20


# This tests proper orientation: 3x4 vs 4x3, row- vs. column-major.
def test34():
    t = get_trie()
    b = PyBoggler(t, (3, 4))

    # A E I
    # B F J
    # C G K
    # D H L
    b.set_board("abcdefghijkl")
    assert b.score() == 1

    # A B C
    # D E F
    # G H I
    # J K L
    b.set_board("adgjbehkcfil")
    assert b.score() == 34


def test44():
    t = get_trie()
    b = PyBoggler(t, (4, 4))
    b.set_board("abcdefghijklmnop")
    assert b.score() == 18
