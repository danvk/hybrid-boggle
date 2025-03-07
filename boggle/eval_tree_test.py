import pytest
from cpp_boggle import create_eval_node_arena
from inline_snapshot import external, outsource, snapshot

from boggle.eval_tree import (
    CHOICE_NODE,
    ROOT_NODE,
    EvalNode,
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
    root = arena.new_root_node_with_capacity(4)
    cells = ["bcd", "aei", "nrd"]
    root.add_word([(0, 0), (1, 0), (2, 0)], 1, arena)  # ban
    root.add_word([(0, 1), (1, 0), (2, 0)], 1, arena)  # can
    root.add_word([(0, 0), (1, 0), (2, 1)], 1, arena)  # bar
    root.add_word([(0, 0), (1, 1), (2, 2)], 1, arena)  # bed
    root.add_word([(0, 0), (1, 2), (2, 2)], 1, arena)  # bid
    root.add_word([(0, 2), (1, 2), (2, 2)], 1, arena)  # did
    root.add_word([(0, 2), (2, 1), (1, 1)], 1, arena)  # dre

    # print(root.to_dot(cells))

    # This asserts that the C++ and Python trees stay in sync
    assert outsource(eval_node_to_string(root, cells)) == snapshot(
        external("8cd3c17dadcd*.txt")
    )


def choice_node(cell, children):
    n = EvalNode()
    n.children = children
    n.letter = CHOICE_NODE
    n.cell = cell
    n.points = 0
    return n


def letter_node(*, cell, letter, points=0, children=[]) -> EvalNode:
    n = EvalNode()
    n.letter = letter
    n.cell = cell
    n.points = points
    n.children = children
    return n


def test_orderly_merge():
    cells = ["abc", "de"]
    num_letters = [len(c) for c in cells]
    t0 = choice_node(
        cell=0,
        children=[
            letter_node(cell=0, letter=1, points=1),
            letter_node(cell=0, letter=2, points=2),
        ],
    )
    t1 = choice_node(
        cell=1,
        children=[
            letter_node(cell=1, letter=0, points=1),
            letter_node(cell=1, letter=1, points=2),
        ],
    )
    root = letter_node(cell=0, letter=ROOT_NODE, children=[t0, t1])
    root.set_computed_fields(num_letters)
    # print(root.to_dot(cells))
    arena = create_eval_node_arena_py()
    force = root.orderly_force_cell(0, num_letters[0], arena)
    assert len(force) == 3
    assert force[0] is not None
