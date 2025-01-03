import pytest
from cpp_boggle import BucketBoggler33, Trie

from boggle.boggle import PyTrie
from boggle.ibuckets import PyBucketBoggler

BIGINT = 1_000_000


PARAMS = [(PyBucketBoggler, PyTrie), (BucketBoggler33, Trie)]


@pytest.mark.parametrize("Boggler, TrieT", PARAMS)
def test_boards(Boggler, TrieT):
    bb = Boggler(None)

    assert not bb.ParseBoard("")
    assert not bb.ParseBoard("abc def")
    assert not bb.ParseBoard("a b c d e f g h i j")
    assert not bb.ParseBoard("a b c d e  g h i")

    assert bb.ParseBoard("a b c d e f g h i")
    for i in range(0, 9):
        assert bb.Cell(i) == chr(ord("a") + i)
    assert bb.NumReps() == 1

    bb.SetCell(0, "abc")
    bb.SetCell(8, "pqrs")
    bb.SetCell(7, "htuv")

    assert bb.Cell(0) != "a"
    assert bb.Cell(0) == "abc"
    assert bb.Cell(7) == "htuv"
    assert bb.Cell(8) == "pqrs"
    assert 3 * 4 * 4 == bb.NumReps()


@pytest.mark.parametrize("Boggler, TrieT", PARAMS)
def test_bound(Boggler, TrieT):
    t = TrieT()
    t.AddWord("sea")
    t.AddWord("seat")
    t.AddWord("seats")
    t.AddWord("tea")
    t.AddWord("teas")

    bb = Boggler(t)

    assert bb.ParseBoard("a b c d e f g h i")
    assert 0 == bb.UpperBound(BIGINT)
    assert 0 == bb.Details().sum_union
    assert 0 == bb.Details().max_nomark

    # s e h
    # e a t
    # p u c
    assert bb.ParseBoard("s e p e a u h t c")
    score = bb.UpperBound(BIGINT)
    assert 4 == bb.Details().sum_union  # sea(t), tea(s)
    assert 6 == bb.Details().max_nomark  # seat*2, sea*2, tea
    assert 1 + 1 + 1 + 1 == score  # all words
    assert 4 == bb.UpperBound(BIGINT)

    # a board where both [st]ea can be found, but not simultaneously
    # st z z
    #  e a s
    assert bb.ParseBoard("st z z e a s z z z")
    score = bb.UpperBound(BIGINT)
    assert 3 == bb.Details().sum_union  # tea(s) + sea
    assert 2 == bb.Details().max_nomark  # tea(s)
    assert 2 == score
    assert 2 == bb.UpperBound(BIGINT)

    # Add in a "seat", test its (sum union's) shortcomings. Can't have 'seats'
    # and 'teas' on the board simultaneously, but it still counts both.
    # st z z
    #  e a st
    #  z z s
    bb.SetCell(5, "st")
    bb.SetCell(8, "s")

    score = bb.UpperBound(BIGINT)
    assert 2 + 4 == bb.Details().sum_union  # all but "hiccup"
    assert 4 == bb.Details().max_nomark  # sea(t(s))
    assert 4 == score


@pytest.mark.parametrize("Boggler, TrieT", PARAMS)
def test_q(Boggler, TrieT):
    t = TrieT()
    t.AddWord("qa")  # qua = 1
    t.AddWord("qas")  # qua = 1
    t.AddWord("qest")  # quest = 2

    bb = Boggler(t)

    # q a s
    # a e z
    # s t z
    assert bb.ParseBoard("q a s a e z s t z")
    score = bb.UpperBound(BIGINT)
    assert 4 == bb.Details().sum_union
    assert 6 == bb.Details().max_nomark  # (qa + qas)*2 + qest
    assert 4 == score

    # Make sure "qu" gets parsed as "either 'qu' or 'u'"
    # qu a s
    # a e z
    # s t z
    assert bb.ParseBoard("qu a s a e z s t z")
    score = bb.UpperBound(BIGINT)
    assert 4 == bb.Details().sum_union
    assert 6 == bb.Details().max_nomark  # (qa + qas)*2 + qest
    assert 4 == score


@pytest.mark.parametrize("Boggler, TrieT", PARAMS)
def test_tea_tier(Boggler, TrieT):
    # https://www.danvk.org/wp/2009-08-11/a-few-more-boggle-examples/

    t = TrieT()
    t.AddWord("tar")
    t.AddWord("tie")
    t.AddWord("tier")
    t.AddWord("tea")

    bb = Boggler(t)

    #  t i z
    # ae z z
    #  r z z
    assert bb.ParseBoard("t i z ae z z r z z")
    assert 3 == bb.UpperBound(BIGINT)
    assert 3 == bb.Details().sum_union
    assert 3 == bb.Details().max_nomark
