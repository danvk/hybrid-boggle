import pytest
from boggle.arena import create_eval_node_arena_py
from boggle.eval_node import ChoiceNode, SumNode

# There are more thorough tests in orderly_tree_test.py


def choice_node(*, children) -> ChoiceNode:
    n = ChoiceNode()
    n.children = children
    return n


def sum_node(*, points=0, children=None) -> SumNode:
    n = SumNode()
    n.points = points
    n.children = children or {}
    return n


def test_orderly_merge():
    cells = ["abc", "de"]
    num_letters = [len(c) for c in cells]
    t0 = choice_node(
        children=[
            sum_node(points=1),
            sum_node(points=2),
        ],
    )
    t0.child_letters = (1 << 0) | (1 << 1)
    t1 = choice_node(
        children=[
            sum_node(points=1),
            sum_node(points=2),
        ],
    )
    t1.child_letters = (1 << 0) | (1 << 1)
    root = sum_node(children={0: t0, 1: t1})
    root.set_bounds_for_testing()
    # print(root.to_dot(cells))
    arena = create_eval_node_arena_py()
    force = root.orderly_force_cell(0, num_letters[0], arena)
    assert len(force) == 3
    assert force[0] is not None


def test_subtract_tree():
    # Tree A:
    # Root (SumNode, pts=10)
    #   Cell 0 (ChoiceNode, letters A, B)
    #     A -> SumNode(pts=5)
    #     B -> SumNode(pts=3)

    # Tree B:
    # Root (SumNode, pts=4)
    #   Cell 0 (ChoiceNode, letters A)
    #     A -> SumNode(pts=2)

    t_a = sum_node(
        points=10,
        children={
            0: choice_node(
                children=[
                    sum_node(points=5),  # A
                    sum_node(points=3),  # B
                ]
            )
        },
    )
    t_a.children[0].child_letters = (1 << 0) | (1 << 1)
    t_a.set_bounds_for_testing()

    t_b = sum_node(
        points=4,
        children={
            0: choice_node(
                children=[
                    sum_node(points=2)  # A
                ]
            )
        },
    )
    t_b.children[0].child_letters = 1 << 0
    t_b.set_bounds_for_testing()

    res = t_a.subtract_tree(t_b)

    assert res.points == 10 - 4
    assert res.children[0].child_letters == (1 << 0) | (1 << 1)

    # Child A: 5 - 2 = 3
    assert res.children[0].children[0].points == 3
    # Child B: 3 - 0 = 3 (preserved)
    assert res.children[0].children[1].points == 3

    # Bound calculation
    # Child A bound: 3
    # Child B bound: 3
    # Choice 0 bound: max(3, 3) = 3
    # Root bound: 6 + 3 = 9
    assert res.bound == 9

    # Error case: extra child in other
    t_c = sum_node(
        points=0,
        children={
            1: choice_node(children=[])  # Extra cell
        },
    )
    with pytest.raises(ValueError, match="Other tree has child at cell 1"):
        t_a.subtract_tree(t_c)

    # Error case: extra letter in other
    t_d = sum_node(
        points=0,
        children={
            0: choice_node(children=[sum_node()])
        },
    )
    t_d.children[0].child_letters = 1 << 2  # Letter C
    with pytest.raises(ValueError, match="Other tree has child letters .* not in self"):
        t_a.subtract_tree(t_d)
