from boggle.clean_tree import (
    ChoiceNode,
    SumNode,
    TreeBuilder,
    assert_invariants,
    eval_all,
    filter_below_threshold,
    lift_choice,
    max_bound,
    merge_choices,
    squeeze_choice_node,
    squeeze_sum_node,
)
from boggle.trie import make_py_trie


def test_lift_sum():
    root = SumNode(
        points=0,
        children=[
            ChoiceNode(cell=1, children=[1, 3], points=0),
            ChoiceNode(cell=1, children=[2, 4], points=0),
        ],
    )
    assert lift_choice(root, 0, 1) == root
    assert lift_choice(root, 1, 2) == ChoiceNode(
        cell=1,
        children=[None, 4],
        points=3,
        # Collapsed from:
        # SumNode(points=0, children=[1, 2]),
        # SumNode(points=0, children=[3, 4]),
    )

    pointy_root = SumNode(
        points=1,
        children=[
            ChoiceNode(cell=1, children=[1, 3], points=2),
            ChoiceNode(cell=1, children=[2, 4], points=3),
        ],
    )
    assert lift_choice(pointy_root, 0, 1) == pointy_root
    print("go!")
    assert lift_choice(pointy_root, 1, 2) == ChoiceNode(
        cell=1,
        children=[None, 4],
        points=9,
        # Collapsed from:
        # SumNode(points=1, children=[1, 2]),
        # SumNode(points=1, children=[3, 4]),
    )


def test_lift_choice():
    root = ChoiceNode(
        cell=0,
        children=[
            ChoiceNode(cell=1, children=[1, 3], points=0),
            ChoiceNode(cell=1, children=[2, 4], points=0),
        ],
        points=0,
    )
    assert lift_choice(root, 0, 2) == root
    assert lift_choice(root, 2, 1) == root
    assert lift_choice(root, 1, 2) == ChoiceNode(
        cell=1,
        children=[
            ChoiceNode(cell=0, children=[None, 1], points=0),
            ChoiceNode(cell=0, children=[None, 1], points=2),
        ],
        points=1,
    )

    pointy_root = ChoiceNode(
        cell=0,
        children=[
            ChoiceNode(cell=1, children=[1, 3], points=2),
            ChoiceNode(cell=1, children=[2, 4], points=3),
            None,
        ],
        points=1,
    )
    assert lift_choice(pointy_root, 0, 2) == pointy_root
    assert lift_choice(pointy_root, 2, 1) == pointy_root
    assert lift_choice(pointy_root, 1, 2) == ChoiceNode(
        cell=1,
        children=[
            ChoiceNode(cell=0, children=[3, 5, None], points=0),
            ChoiceNode(cell=0, children=[5, 7, None], points=0),
        ],
        points=1,
    )


def test_squeeze_choice_node():
    pointy_root = ChoiceNode(
        cell=0,
        children=[
            ChoiceNode(cell=1, children=[1, 3], points=2),
            ChoiceNode(cell=1, children=[2, 4], points=3),
            None,
        ],
        points=1,
    )
    assert squeeze_choice_node(pointy_root) == pointy_root
    assert (
        squeeze_choice_node(
            ChoiceNode(
                cell=0,
                children=[
                    ChoiceNode(cell=1, children=[1, 3], points=3),
                    ChoiceNode(cell=1, children=[2, 4], points=4),
                    1,
                ],
                points=0,
            )
        )
        == pointy_root
    )


def test_squeeze_sum_node():
    assert squeeze_sum_node(SumNode(points=2, children=[])) == 2
    assert squeeze_sum_node(SumNode(points=0, children=[2, 3])) == 5
    assert squeeze_sum_node(SumNode(points=2, children=[2, 3])) == 7

    choice_node = ChoiceNode(cell=0, children=[2, 3], points=0)
    assert squeeze_sum_node(
        SumNode(points=2, children=[2, choice_node, 3])
    ) == ChoiceNode(cell=0, points=7, children=[2, 3])  # could squeeze more!
    assert squeeze_sum_node(SumNode(points=2, children=[choice_node, 3])) == ChoiceNode(
        cell=0, points=5, children=[2, 3]
    )

    assert squeeze_sum_node(SumNode(points=0, children=[choice_node])) == choice_node
    assert squeeze_sum_node(SumNode(points=1, children=[choice_node])) == ChoiceNode(
        cell=0, points=1, children=[2, 3]
    )

    choice_node2 = ChoiceNode(
        cell=0, children=[3, ChoiceNode(cell=1, children=[1, 2], points=0)], points=0
    )
    assert squeeze_sum_node(
        SumNode(points=1, children=[choice_node, choice_node2])
    ) == ChoiceNode(
        cell=0, points=1, children=[5, ChoiceNode(cell=1, points=3, children=[1, 2])]
    )
    assert squeeze_sum_node(
        SumNode(points=1, children=[choice_node, 3, choice_node2])
    ) == ChoiceNode(
        cell=0, points=4, children=[5, ChoiceNode(cell=1, points=3, children=[1, 2])]
    )


def test_merge_choices():
    choice_node1 = ChoiceNode(points=1, cell=0, children=[2, 3])
    choice_node2 = ChoiceNode(
        points=2, cell=0, children=[3, ChoiceNode(cell=1, children=[1, 2], points=0)]
    )
    assert merge_choices([choice_node1, choice_node2]) == ChoiceNode(
        cell=0, points=3, children=[5, ChoiceNode(cell=1, points=3, children=[1, 2])]
    )


def test_filter_below_threshold():
    minitree = ChoiceNode(cell=0, points=0, children=[5, 6])
    assert 6 == max_bound(minitree)
    assert 6 == filter_below_threshold(minitree, 5)
    assert minitree == ChoiceNode(cell=0, points=0, children=[None, 6])

    tree = ChoiceNode(
        cell=0,
        points=1,
        children=[
            ChoiceNode(
                points=2,
                cell=1,
                children=[2, 3, 4],
            ),
            SumNode(points=3, children=[2, 3]),
        ],
    )
    assert 9 == max_bound(tree)
    assert 9 == filter_below_threshold(tree, 6)
    assert tree == ChoiceNode(
        cell=0,
        points=1,
        children=[
            ChoiceNode(points=2, cell=1, children=[None, None, 4]),
            SumNode(points=3, children=[2, 3]),
        ],
    )


def test_lift_invariants_22():
    trie = make_py_trie("boggle-words-4.txt")
    board = "ny ae ch ."
    cells = board.split(" ")
    etb = TreeBuilder(trie, dims=(2, 2))
    t = etb.build_tree(board)
    assert_invariants(t, cells)

    scores = eval_all(t, cells)

    # Try lifting each cell; this should not affect any scores.
    for i, cell in enumerate(cells):
        if len(cell) <= 1:
            continue
        tl = lift_choice(t, i, len(cell))
        lift_scores = eval_all(tl, cells)
        assert lift_scores == scores
        assert_invariants(t, cells)


def test_lift_invariants_33():
    trie = make_py_trie("boggle-words-9.txt")
    board = ". . . . lnrsy e aeiou aeiou ."
    # board = ". . . . rs e io au ."
    cells = board.split(" ")
    etb = TreeBuilder(trie, dims=(3, 3))
    t = etb.build_tree(board)
    assert_invariants(t, cells)

    scores = eval_all(t, cells)

    # Try lifting each cell; this should not affect any scores.
    for i, cell in enumerate(cells):
        if len(cell) <= 1:
            continue
        tl = lift_choice(t, i, len(cell))
        lift_scores = eval_all(tl, cells)
        assert lift_scores == scores
        assert_invariants(t, cells)


# TODO:
# - test invariant that sum nodes have no children that are sum nodes or ints
# - test lift invariant on 3x3 board: '. . . . lnrsy e aeiou aeiou .'
