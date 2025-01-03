from cpp_boggle import BucketBoggler33

from boggle.boggle import PyTrie
from boggle.ibuckets import PyBucketBoggler


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
