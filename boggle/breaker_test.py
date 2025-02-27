from inline_snapshot import snapshot

from boggle.boggler import PyBoggler
from boggle.breaker import HybridTreeBreaker
from boggle.orderly_tree_builder import OrderlyTreeBuilder
from boggle.trie import make_py_trie


def test_breaker():
    trie = make_py_trie("testdata/boggle-words-4.txt")
    otb = OrderlyTreeBuilder(trie, dims=(2, 2))
    ATOZ = "".join(chr(x) for x in range(ord("a"), ord("z") + 1))
    board = " ".join([ATOZ] * 4)
    boggler = PyBoggler(trie, dims=(2, 2))

    breaker = HybridTreeBreaker(
        otb, boggler, (2, 2), 15, switchover_level=2, log_breaker_progress=False
    )

    breaker.SetBoard(board)
    details = breaker.Break()

    assert details == snapshot()
