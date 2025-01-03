from cpp_boggle import BucketBoggler33, Trie

from boggle.boggle import PyTrie
from boggle.ibuckets import PyBucketBoggler

BIGINT = 1_000_000


def run_test_boards(Boggler):
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


def test_boards_py():
    run_test_boards(PyBucketBoggler)


def test_boards_cpp():
    run_test_boards(BucketBoggler33)


def run_test_bound(Boggler, TrieT):
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


def test_bound_py():
    run_test_bound(PyBucketBoggler, PyTrie)


def test_bound_cpp():
    run_test_bound(BucketBoggler33, Trie)
