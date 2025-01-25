from boggle.clean_tree import (
    ChoiceNode,
    SumNode,
    TreeBuilder,
    assert_invariants,
    eval_all,
    lift_choice,
)
from boggle.trie import make_py_trie


def test_lift_sum():
    root = SumNode(
        points=0,
        children=[
            ChoiceNode(cell=1, children=[1, 3]),
            ChoiceNode(cell=1, children=[2, 4]),
        ],
    )
    assert lift_choice(root, 0, 1) == root
    assert lift_choice(root, 1, 2) == ChoiceNode(
        cell=1,
        children=[3, 7],
        # Collapsed from:
        # SumNode(points=0, children=[1, 2]),
        # SumNode(points=0, children=[3, 4]),
    )


def test_lift_choice():
    root = ChoiceNode(
        cell=0,
        children=[
            ChoiceNode(cell=1, children=[1, 3]),
            ChoiceNode(cell=1, children=[2, 4]),
        ],
    )
    assert lift_choice(root, 0, 2) == root
    assert lift_choice(root, 2, 1) == root
    assert lift_choice(root, 1, 2) == ChoiceNode(
        cell=1,
        children=[
            ChoiceNode(cell=0, children=[1, 2]),
            ChoiceNode(cell=0, children=[3, 4]),
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
