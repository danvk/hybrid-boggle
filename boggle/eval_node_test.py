import pytest
from boggle.split_order import SPLIT_ORDER
from cpp_boggle import create_eval_node_arena
from inline_snapshot import external, outsource, snapshot

from boggle.arena import create_eval_node_arena_py
from boggle.eval_node import ROOT_NODE, ChoiceNode, SumNode, eval_node_to_string

# There are more thorough tests in orderly_tree_test.py


@pytest.mark.parametrize(
    "create_arena", (create_eval_node_arena_py, create_eval_node_arena)
)
def test_add_word(create_arena):
    arena = create_arena()
    root = arena.new_root_node_with_capacity(4)
    cells = ["bcd", "aei", "nrd"]

    regular_order = [0, 1, 2]
    other_order = [0, 2, 1]

    # all three choices are used
    used_ordered = 0b111

    root.add_word([0, 0, 0], used_ordered, regular_order, 1, arena)  # ban
    root.add_word([1, 0, 0], used_ordered, regular_order, 1, arena)  # can
    root.add_word([0, 0, 1], used_ordered, regular_order, 1, arena)  # bar
    root.add_word([0, 1, 2], used_ordered, regular_order, 1, arena)  # bed
    root.add_word([0, 2, 2], used_ordered, regular_order, 1, arena)  # bid
    root.add_word([2, 2, 2], used_ordered, regular_order, 1, arena)  # did
    root.add_word([2, 1, 1], used_ordered, other_order, 1, arena)  # dre

    # This asserts that the C++ and Python trees stay in sync
    print(eval_node_to_string(root, cells))
    assert outsource(eval_node_to_string(root, cells)) == snapshot(
        external("8cd3c17dadcd*.txt")
    )


def choice_node(cell, children):
    n = ChoiceNode()
    n.children = children
    n.cell = cell
    return n


def letter_node(*, letter, points=0, children=[]) -> SumNode:
    n = SumNode()
    n.letter = letter
    n.points = points
    n.children = children
    return n


def test_orderly_merge():
    cells = ["abc", "de"]
    num_letters = [len(c) for c in cells]
    t0 = choice_node(
        cell=0,
        children=[
            letter_node(letter=1, points=1),
            letter_node(letter=2, points=2),
        ],
    )
    t1 = choice_node(
        cell=1,
        children=[
            letter_node(letter=0, points=1),
            letter_node(letter=1, points=2),
        ],
    )
    root = letter_node(letter=ROOT_NODE, children=[t0, t1])
    root.set_computed_fields(num_letters)
    # print(root.to_dot(cells))
    arena = create_eval_node_arena_py()
    force = root.orderly_force_cell(0, num_letters[0], arena)
    assert len(force) == 3
    assert force[0] is not None
