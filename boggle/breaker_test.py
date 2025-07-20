import pytest
from inline_snapshot import snapshot

from boggle.boggler import PyBoggler
from boggle.breaker import HybridTreeBreaker
from boggle.test_utils import get_trie_otb


@pytest.mark.parametrize(
    "is_python",
    [
        True,
        # False -- the byte and node counts don't agree
    ],
)
def test_breaker(is_python):
    trie, otb = get_trie_otb("testdata/boggle-words-4.txt", (2, 2), is_python)
    board = "aeiou lnrsy chkmpt aeiou"
    boggler = PyBoggler(trie, dims=(2, 2))

    breaker = HybridTreeBreaker(
        otb,
        boggler,
        (2, 2),
        15,
        switchover_score=20,
        max_depth=3,
        log_breaker_progress=False,
    )

    breaker.SetBoard(board)
    details = breaker.Break()
    # blank out non-deterministic fields
    details.secs_by_level = []
    details.elapsed_s = 0.0
    details.test_secs = 0.0
    details.bound_secs = []
    details.tree_secs = []

    # poetry run python -m boggle.exhaustive_search --size 22 15 'aeiou lnrsy chkmpt aeiou' --python
    # 16 alte
    # 15 arte
    # 18 aste
    # 16 elta
    # 15 erta
    # 18 esta

    assert details.asdict() == snapshot(
        {
            "num_reps": 750,
            "elapsed_s": 0.0,
            "failures": ["alte", "arte", "aste", "elta", "erta", "esta"],
            "elim_level": [0, 0, 2, 1],
            "secs_by_level": [],
            "bounds": [21, 21, 20],
            "depth": [0, 0, 2, 4],
            "boards_to_test": 6,
            "init_nodes": 1186,
            "total_nodes": 1372,
            "tree_bytes": 37952,
            "n_paths": 1492,
            "n_paths_uniq": 800,
            "tree_secs": [],
            "total_bytes": 43904,
            "n_bound": 6,
            "n_force": 2,
            "max_multi": 18,
            "bound_secs": [],
            "test_secs": 0.0,
            "best_board": (18, "aste"),
        }
    )
