import pytest
from cpp_boggle import create_eval_node_arena
from inline_snapshot import external, outsource, snapshot

from boggle.eval_tree import (
    create_eval_node_arena_py,
    eval_node_to_string,
)

# TODO: make an orderly version of these invariant tests
# Invariants:
# - Each lift should produce a choice tree that matches max-nomark for directly evaluating the tree.
# - This should remain true for all combinations of compress + dedupe


@pytest.mark.parametrize(
    "create_arena", (create_eval_node_arena_py, create_eval_node_arena)
)
def test_add_word(create_arena):
    arena = create_arena()
    root = arena.new_node_with_capacity(4)
    cells = ["bcd", "aei", "nrd"]
    root.add_word([(0, 0), (1, 0), (2, 0)], 1, arena)  # ban
    root.add_word([(0, 1), (1, 0), (2, 0)], 1, arena)  # can
    root.add_word([(0, 0), (1, 0), (2, 1)], 1, arena)  # bar
    root.add_word([(0, 0), (1, 1), (2, 2)], 1, arena)  # bed
    root.add_word([(0, 0), (1, 2), (2, 2)], 1, arena)  # bid
    root.add_word([(0, 2), (1, 2), (2, 2)], 1, arena)  # did

    # print(root.to_dot(cells))

    # This asserts that the C++ and Python trees stay in sync
    assert outsource(eval_node_to_string(root, cells)) == snapshot(
        external("086ccf9f3935*.txt")
    )
