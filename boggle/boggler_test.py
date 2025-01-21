import functools

import pytest
from cpp_boggle import Trie

from boggle.boggler import PyBoggler
from boggle.dimensional_bogglers import cpp_boggler
from boggle.trie import make_py_trie


@functools.cache
def get_py_trie():
    return make_py_trie("boggle-words.txt")


@functools.cache
def get_cpp_trie():
    return Trie.CreateFromFile("boggle-words.txt")


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


@pytest.mark.parametrize("get_trie, Boggler", PARAMS)
def test44(get_trie, Boggler):
    t = get_trie()
    b = Boggler(t, (4, 4))
    assert b.score("abcdefghijklmnop") == 18
