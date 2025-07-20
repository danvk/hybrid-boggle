import pytest
from inline_snapshot import external, outsource, snapshot

from boggle.arena import create_eval_node_arena_py
from boggle.eval_node import ChoiceNode, SumNode, eval_node_to_string
from boggle.make_dot import to_dot
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


def dupe_label(n: ChoiceNode | SumNode):
    if isinstance(n, ChoiceNode):
        return str(n.bound)
    return str(n.bound) + ("" if not n.has_dupes else "*")


@pytest.mark.parametrize("is_python", [True])
def test_orderly_force22(is_python):
    _, otb = get_trie_otb("testdata/boggle-words-4.txt", (2, 2), is_python)
    board = "st ea ea tr"
    cells = board.split(" ")
    num_letters = [len(cell) for cell in cells]
    otb.parse_board(board)
    arena = otb.create_arena()
    t = otb.build_tree(arena)

    with open("tree.dot", "w") as out:
        dot = to_dot(t, cells)
        out.write(dot)

    force_deep = t.orderly_force_cell(0, num_letters[0], arena)
    force_1 = t.orderly_force_cell(0, num_letters[0], arena, max_depth=1)
    force_2 = t.orderly_force_cell(0, num_letters[0], arena, max_depth=2)
    assert outsource(eval_node_to_string(force_1[0], cells)) == snapshot(
        external("ecd96b328f0d*.txt")
    )
    assert outsource(eval_node_to_string(force_1[1], cells)) == snapshot(
        external("622d45112e41*.txt")
    )
    assert outsource(eval_node_to_string(force_2[0], cells)) == snapshot(
        external("c549d5088ad0*.txt")
    )
    assert outsource(eval_node_to_string(force_2[1], cells)) == snapshot(
        external("4eecf39fe7b3*.txt")
    )

    assert force_1[0].has_dupes
    force_1[0].compact_in_place(arena, max_depth=1)
    assert outsource(eval_node_to_string(force_1[0], cells)) == snapshot(
        external("c549d5088ad0*.txt")
    )
    with open("force+compact.dot", "w") as out:
        out.write(to_dot(force_1[0], cells, node_label_fn=dupe_label))
    assert not force_1[0].has_dupes
    force_1[1].compact_in_place(arena, max_depth=1)
    assert outsource(eval_node_to_string(force_1[1], cells)) == snapshot(
        external("4eecf39fe7b3*.txt")
    )

    for a, b in zip(force_1, force_2):
        assert eval_node_to_string(a, cells) == eval_node_to_string(b, cells)

    # for depth in (None, 1, 2, 3):
    #     depth_str = "deep" if depth is None else f"depth{depth}"
    #     force = t.orderly_force_cell(0, num_letters[0], arena, max_depth=(depth or 100))
    #     for i, ft in enumerate(force):
    #         with open(f"force{i}-{depth_str}.dot", "w") as out:
    #             dot = to_dot(ft, cells, node_label_fn=dupe_label)
    #             out.write(dot)

    t001 = force_deep[0].orderly_force_cell(1, num_letters[1], arena)
    with open("force-0010.dot", "w") as out:
        out.write(to_dot(t001[0], cells, node_label_fn=dupe_label))
    assert outsource(eval_node_to_string(t001[0], cells)) == snapshot(
        external("c47f9c12f776*.txt")
    )

    with open("force-00.d1.dot", "w") as out:
        out.write(to_dot(force_1[0], cells, node_label_fn=dupe_label))
    t001 = force_1[0].orderly_force_cell(1, num_letters[1], arena)
    with open("force-0010.d1.dot", "w") as out:
        out.write(to_dot(t001[0], cells, node_label_fn=dupe_label))
    assert outsource(eval_node_to_string(t001[0], cells)) == snapshot(
        external("c47f9c12f776*.txt")
    )
