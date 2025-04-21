import pytest
from cpp_boggle import Trie
from inline_snapshot import snapshot

from boggle.boggler import PyBoggler
from boggle.breaker import HybridTreeBreaker
from boggle.dimensional_bogglers import cpp_orderly_tree_builder
from boggle.orderly_tree_builder import OrderlyTreeBuilder
from boggle.trie import make_py_trie


def get_trie_otb(dict_file: str, dims: tuple[int, int], is_python: bool):
    if is_python:
        trie = make_py_trie(dict_file)
        otb = OrderlyTreeBuilder(trie, dims=dims)
    else:
        trie = Trie.CreateFromFile(dict_file)
        otb = cpp_orderly_tree_builder(trie, dims=dims)
    return trie, otb


@pytest.mark.parametrize(
    "is_python",
    [
        True,
        # False
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
    details.secs_by_level = {}
    details.elapsed_s = 0.0

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
            "failures": ["alte", "aste", "elta", "esta"],
            "elim_level": {2: 2},
            "secs_by_level": {},
            "bounds": {0: 21},
            "nodes": {0: 1186},
            "depth": {2: 3},
            "boards_to_test": 7,
            "init_nodes": 1186,
            "total_nodes": 1186,
            "freed_nodes": 0,
            "free_time_s": 0.0,
            "n_bound": 3,
            "n_force": 1,
        }
    )
