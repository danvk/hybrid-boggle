import pytest
from inline_snapshot import external, outsource, snapshot

from boggle.arena import create_eval_node_arena_py
from boggle.eval_node import ChoiceNode, SumNode, eval_node_to_string
from boggle.test_utils import get_trie_otb

# There are more thorough tests in orderly_tree_test.py


def choice_node(cell, children):
    n = ChoiceNode()
    n.children = children
    n.cell = cell
    return n


def sum_node(*, points=0, children=[]) -> SumNode:
    n = SumNode()
    n.points = points
    n.children = children
    return n


def test_orderly_merge():
    cells = ["abc", "de"]
    num_letters = [len(c) for c in cells]
    t0 = choice_node(
        cell=0,
        children=[
            sum_node(points=1),
            sum_node(points=2),
        ],
    )
    t1 = choice_node(
        cell=1,
        children=[
            sum_node(points=1),
            sum_node(points=2),
        ],
    )
    root = sum_node(children=[t0, t1])
    root.set_bounds_for_testing()
    # print(root.to_dot(cells))
    arena = create_eval_node_arena_py()
    force = root.orderly_force_cell(0, num_letters[0], arena)
    assert len(force) == 3
    assert force[0] is not None


@pytest.mark.parametrize("is_python", [True, False])
def test_orderly_force22(is_python):
    _, otb = get_trie_otb("testdata/boggle-words-4.txt", (2, 2), is_python)
    board = "st ea ea tr"
    cells = board.split(" ")
    num_letters = [len(cell) for cell in cells]
    otb.parse_board(board)
    arena = otb.create_arena()
    t = otb.build_tree(arena)
    force = t.orderly_force_cell(0, num_letters[0], arena)

    txt = "\n\n".join(
        f"{i}: " + eval_node_to_string(t, cells, top_cell=0)
        for i, t in enumerate(force)
    )

    assert outsource(txt) == snapshot(external("7dd80d82a00c*.txt"))
