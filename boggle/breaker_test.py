from collections import Counter

from inline_snapshot import snapshot

from boggle.boggler import PyBoggler
from boggle.breaker import HybridBreakDetails, HybridTreeBreaker
from boggle.orderly_tree_builder import OrderlyTreeBuilder
from boggle.trie import make_py_trie


# TODO: set up a C++ version of this
def test_breaker():
    trie = make_py_trie("testdata/boggle-words-4.txt")
    otb = OrderlyTreeBuilder(trie, dims=(2, 2))
    board = "aeiou lnrsy chkmpt aeiou"
    boggler = PyBoggler(trie, dims=(2, 2))

    breaker = HybridTreeBreaker(
        otb,
        boggler,
        (2, 2),
        15,
        switchover_level=2,
        log_breaker_progress=False,
    )

    breaker.SetBoard(board)
    details = breaker.Break()
    # blank out non-deterministic fields
    details.secs_by_level = {}
    details.elapsed_s = 0.0

    # poetry run python -m boggle.exhaustive_search --size 22 15 'aeiou lnrsy chkmpt aeiou' --python
    # 16 alte
    # 15 arte
    # 18 aste
    # 16 elta
    # 15 erta
    # 18 esta

    assert details == snapshot(
        HybridBreakDetails(
            num_reps=750,
            elapsed_s=0.0,
            failures=["alte", "aste", "elta", "esta"],
            elim_level=Counter({2: 2}),
            secs_by_level={},
            sum_union=0,
            bounds={0: 21},
            nodes={0: "n/a"},
            boards_to_test=7,
            expanded_to_test=7,
            init_nodes="n/a",
            total_nodes="n/a",
            freed_nodes=0,
            free_time_s=0.0,
        )
    )
