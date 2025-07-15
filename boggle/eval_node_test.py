from boggle.arena import create_eval_node_arena_py
from boggle.eval_node import ChoiceNode, SumNode

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
