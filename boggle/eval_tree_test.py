import itertools
import math

import pytest
from cpp_boggle import EvalNode as CppEvalNode
from cpp_boggle import TreeBuilder33, Trie, create_eval_node_arena

from boggle.eval_tree import (
    CHOICE_NODE,
    ROOT_NODE,
    EvalNode,
    EvalTreeBoggler,
    create_eval_node_arena_py,
    eval_tree_from_json,
    merge_trees,
)
from boggle.ibuckets import PyBucketBoggler
from boggle.trie import PyTrie, make_lookup_table, make_py_trie

# TODO: add assertions about choice_mask


# This matches ibuckets_test.py test_bounds
def test_eval_tree_match():
    t = PyTrie()
    t.AddWord("sea")
    t.AddWord("seat")
    t.AddWord("seats")
    t.AddWord("tea")
    t.AddWord("teas")

    bb = EvalTreeBoggler(t, (3, 3))

    assert bb.ParseBoard("a b c d e f g h i")
    t = bb.BuildTree()
    assert 0 == bb.Details().sum_union
    assert 0 == bb.Details().max_nomark
    assert 0 == t.recompute_score()

    # s e h
    # e a t
    # p u c
    assert bb.ParseBoard("s e p e a u h t c")
    t = bb.BuildTree()
    assert 4 == bb.Details().sum_union  # sea(t), tea(s)
    assert 6 == bb.Details().max_nomark  # seat*2, sea*2, tea
    assert 6 == t.recompute_score()
    t.prune()
    assert 6 == t.recompute_score()
    assert 6 == t.bound

    # print(t.to_string(bb))

    # a board where both [st]ea can be found, but not simultaneously
    # st z z
    #  e a s
    assert bb.ParseBoard("st z z e a s z z z")
    t = bb.BuildTree()
    assert 3 == bb.Details().sum_union  # tea(s) + sea
    assert 2 == bb.Details().max_nomark  # tea(s)
    assert 2 == t.recompute_score()
    t.prune()
    assert 2 == t.recompute_score()
    assert 2 == t.bound

    # Add in a "seat", test its (sum union's) shortcomings. Can't have 'seats'
    # and 'teas' on the board simultaneously, but it still counts both.
    # st z z
    #  e a st
    #  z z s
    bb.SetCell(5, "st")
    bb.SetCell(8, "s")

    t = bb.BuildTree()
    assert 2 + 4 == bb.Details().sum_union  # all but "hiccup"
    assert 4 == bb.Details().max_nomark  # sea(t(s))
    assert 4 == t.recompute_score()
    t.prune()
    assert 4 == t.recompute_score()
    assert 4 == t.bound


def test_eval_tree_force():
    t = PyTrie()
    t.AddWord("tar")
    t.AddWord("tie")
    t.AddWord("tier")
    t.AddWord("tea")
    t.AddWord("the")

    #  t i .
    # ae . .
    #  r . .
    bb = EvalTreeBoggler(t, (3, 3))
    assert bb.ParseBoard("tc i z ae z z r z z")

    # With no force, we match the behavior of scalar ibuckets
    t = bb.BuildTree()
    assert 3 == bb.Details().sum_union
    assert 3 == bb.Details().max_nomark
    assert 4 == bb.NumReps()
    assert 3 == t.bound
    assert 3 == t.recompute_score()
    t.check_consistency()
    # print(t.to_string(bb))

    # A force on an irrelevant cell has no effect
    t0 = t.force_cell(0, num_lets=1)
    # assert len(t0) == 1
    # assert t0[0].bound == 3
    # t0[0].check_consistency()
    assert isinstance(t0, list)
    assert t0[0].bound == 3
    t0[0].check_consistency()

    t0 = t.lift_choice(0, num_lets=1)
    assert t0.bound == 3
    t0.check_consistency()
    # print("lift 0")
    # print(t0.to_string(bb))
    assert t0.letter == CHOICE_NODE
    assert t0.cell == 0

    # A force on the choice cell reduces the bound.
    t3 = t.force_cell(3, 2)
    # print("lift 3")
    # print(t3.to_string(bb))
    assert len(t3) == 2
    assert t3[0].bound == 1
    assert t3[1].bound == 2
    t3[0].check_consistency()
    t3[1].check_consistency()

    t3 = t.lift_choice(3, 2)
    # print(t3.to_string(bb))
    assert t3.bound == 2
    assert t3.letter == CHOICE_NODE
    assert t3.cell == 3
    assert len(t3.children) == 2
    assert t3.children[0].cell == 3
    assert t3.children[0].letter == 0
    assert t3.children[0].bound == 1
    assert t3.children[1].cell == 3
    assert t3.children[1].letter == 1
    assert t3.children[1].bound == 2


MINI_DICT = [
    "aeon",
    "ail",
    "air",
    "ais",
    "ear",
    "eau",
    "eel",
    "eon",
    "ion",
    "lea",
    "lee",
    "lei",
    "lie",
    "lieu",
    "loo",
    "luau",
    "nee",
    "oar",
    "oil",
    "our",
    "rei",
    "ria",
    "rue",
    "sau",
    "sea",
    "see",
    "sou",
    "sue",
    "yea",
    "you",
]


def test_equivalence():
    t = PyTrie()
    for w in MINI_DICT:
        t.AddWord(w)
    board = ". . . . lnrsy aeiou aeiou aeiou . . . ."
    bb = PyBucketBoggler(t, (3, 4))
    bb.ParseBoard(board)
    bb.collect_words = True
    score = bb.UpperBound(500_000)
    assert 5 == score
    assert score == bb.Details().max_nomark

    # print("Root (PyBucketBoggler):")
    # print("\n".join(bb.words))

    t.ResetMarks()
    etb = EvalTreeBoggler(t, (3, 4))
    etb.ParseBoard(board)
    root = etb.BuildTree()
    assert root.bound == 5
    root.check_consistency()
    assert root.choice_cells() == {4, 5, 6, 7}

    # dot = root.to_dot(etb)
    # print(dot)
    # assert False

    fives = root.force_cell(5, len("aeiou"))
    assert len(fives) == 5

    # print(fives[1].bound)
    table = make_lookup_table(t)
    root_words = root.all_words(table)
    assert [*sorted(root_words)] == [*sorted(bb.words)]
    # print("Root:")
    # print("\n".join(root_words))
    # print("---")
    # print("5=e words:")
    # print("\n".join(fives[1].all_words(table)))
    # print("---")

    # print(fives[1].recompute_score())
    # fives[1].compress()
    # print(fives[1].to_dot(etb))
    # PrintEvalTreeCounts()
    # assert False
    # print(fives[1].bound)
    # print(fives[1].recompute_score())

    t.ResetMarks()
    for i, vowel in enumerate("aeiou"):
        subboard = f". . . . lnrsy {vowel} aeiou aeiou . . . ."
        bb.ParseBoard(subboard)
        bb.UpperBound(500_000)
        if not fives[i]:
            assert bb.Details().max_nomark == 0
            continue
        # print("5=e words (PyBucketBoggler):")
        # print("\n".join(bb.words))
        # Some combinations may have been ruled out by subtree merging.
        # The word lists will be the same, however.
        assert fives[i].bound <= bb.Details().max_nomark
        assert bb.Details().max_nomark == root.score_with_forces_dict({5: i}, 9)
        fives[i].check_consistency()
        # Some choices may have been pruned out
        assert fives[i].choice_cells().issubset({4, 6, 7})
        # The words should be identical, even if some combinations have been ruled out.
        force_words = [*sorted(fives[i].all_words(table))]
        assert force_words == [*sorted(bb.words)]


def choice_node(cell: int, children):
    n = EvalNode()
    n.letter = CHOICE_NODE
    n.cell = cell
    n.children = children
    n.points = 0
    n.bound = 0
    return n


def letter_node(cell: int, letter: int, points=0, children=None):
    n = EvalNode()
    n.letter = letter
    n.cell = cell
    n.children = children or []
    n.points = points
    n.bound = 0
    return n


def test_merge_eval_trees():
    t = PyTrie()
    # for w in MINI_DICT:
    #     t.AddWord(w)
    board = ". . . . lnrsy aeiou aeiou aeiou . . . ."
    etb = EvalTreeBoggler(t, (3, 4))
    etb.ParseBoard(board)

    t0 = choice_node(
        cell=6,
        children=[
            letter_node(
                cell=6,
                letter=0,
                children=[
                    choice_node(
                        cell=7,
                        children=[letter_node(cell=7, letter=4, points=1)],  # eau
                    )
                ],
            )
        ],
    )

    t1 = choice_node(
        cell=6,
        children=[
            letter_node(
                cell=6,
                letter=1,
                children=[
                    choice_node(
                        cell=4,
                        children=[letter_node(cell=4, letter=0, points=1)],  # eel
                    )
                ],
            )
        ],
    )

    # print("t0:")
    # print(t0.to_dot(etb))

    # print("t1:")
    # print(t1.to_dot(etb))

    # m = merge_trees(t0, t1)

    # this one has more overlap with t0
    t2 = choice_node(
        cell=6,
        children=[
            letter_node(
                cell=6,
                letter=0,
                children=[
                    choice_node(
                        cell=4,
                        children=[letter_node(cell=7, letter=4, points=1)],  # eeu
                    ),
                    choice_node(
                        cell=7,
                        children=[
                            letter_node(cell=7, letter=0, points=1),  # eaa
                            letter_node(cell=7, letter=4, points=1),  # eau
                        ],
                    ),
                ],
            ),
            letter_node(
                cell=6,
                letter=1,
                children=[
                    choice_node(
                        cell=4,
                        children=[letter_node(cell=4, letter=0, points=1)],  # eel
                    )
                ],
            ),
        ],
    )

    # print("t2")
    # print(t2.to_dot(etb))

    # print("t0+t2")
    m = merge_trees(t0, t2)
    # print(m.to_dot(etb))

    # print("t1+t2")
    m = merge_trees(t1, t2)
    # print(m.to_dot(etb))

    # TODO: assert something!
    # assert False


PARAMS = [
    (PyTrie, EvalTreeBoggler, create_eval_node_arena_py),
    (Trie, TreeBuilder33, create_eval_node_arena),
]


@pytest.mark.parametrize("TrieT, TreeBuilderT, create_arena", PARAMS)
def test_cpp_equivalence(TrieT, TreeBuilderT, create_arena):
    t = TrieT()
    t.AddWord("sea")
    t.AddWord("seat")
    t.AddWord("seats")
    t.AddWord("tea")
    t.AddWord("teas")

    bb = TreeBuilderT(t)

    arena = create_arena()
    assert bb.ParseBoard("a b c d e f g h i")
    tree = bb.BuildTree(arena)
    assert 0 == bb.Details().sum_union
    assert 0 == bb.Details().max_nomark
    assert 0 == tree.recompute_score()
    assert 1 == tree.node_count()

    # s e h
    # e a t
    # p u c
    print("sepeauhtc")
    assert bb.ParseBoard("s e p e a u h t c")
    tree = bb.BuildTree(arena)
    assert 4 == bb.Details().sum_union  # sea(t), tea(s)
    assert 6 == bb.Details().max_nomark  # seat*2, sea*2, tea
    assert 6 == tree.recompute_score()
    assert 6 == tree.bound
    assert 23 == tree.node_count()

    # print(t.to_string(bb))

    # a board where both [st]ea can be found, but not simultaneously
    # st z z
    #  e a s
    assert bb.ParseBoard("st z z e a s z z z")
    tree = bb.BuildTree(arena)
    assert 3 == bb.Details().sum_union  # tea(s) + sea
    assert 2 == bb.Details().max_nomark  # tea(s)
    assert 2 == tree.recompute_score()
    assert 2 == tree.bound
    assert 14 == tree.node_count()

    # Add in a "seat", test its (sum union's) shortcomings. Can't have 'seats'
    # and 'teas' on the board simultaneously, but it still counts both.
    # st z z
    #  e a st
    #  z z s
    bb.SetCell(5, "st")
    bb.SetCell(8, "s")

    tree = bb.BuildTree(arena)
    assert 2 + 4 == bb.Details().sum_union  # all but "hiccup"
    assert 4 == bb.Details().max_nomark  # sea(t(s))
    assert 4 == tree.recompute_score()
    assert 4 == tree.recompute_score()
    assert 4 == tree.bound
    assert 20 == tree.node_count()


@pytest.mark.parametrize("TrieT, TreeBuilderT, create_arena", PARAMS)
def test_cpp_force_equivalence(TrieT, TreeBuilderT, create_arena):
    t = TrieT()
    t.AddWord("tar")
    t.AddWord("tie")
    t.AddWord("tier")
    t.AddWord("tea")
    t.AddWord("the")

    arena = create_arena()
    bb = TreeBuilderT(t)

    #  t i .
    # ae . .
    #  r . .
    assert bb.ParseBoard("t i z ae z z r z z")

    # With no force, we match the behavior of scalar ibuckets
    t = bb.BuildTree(arena)
    assert 3 == bb.Details().sum_union
    assert 3 == bb.Details().max_nomark
    assert 2 == bb.NumReps()
    assert 3 == t.bound
    assert 3 == t.recompute_score()
    # t.check_consistency()
    # print(t.to_string(bb))

    # A force on an irrelevant cell has no effect
    t0 = t.force_cell(0, 1, arena)
    # assert len(t0) == 1
    # assert t0[0].bound == 3
    # t0[0].check_consistency()
    assert isinstance(t0, (EvalNode, CppEvalNode))
    assert t0.bound == 3
    # t0.check_consistency()

    # A force on the choice cell reduces the bound.
    t3 = t.force_cell(3, 2, arena)
    assert len(t3) == 2
    assert t3[0].bound == 1
    assert t3[1].bound == 2
    # t3[0].check_consistency()
    # t3[1].check_consistency()

    print("checked all bounds")

    forces = [-1 for _ in range(9)]
    assert t.score_with_forces(forces) == 3  # no force
    forces[3] = 0
    assert t.score_with_forces(forces) == 1
    forces[3] = 1
    assert t.score_with_forces(forces) == 2


# Invariants:
# - Each lift should produce a choice tree that matches max-nomark for directly evaluating the tree.
# - This should remain true for all combinations of compress + dedupe


@pytest.mark.parametrize(
    "dedupe, compress", [(False, False), (False, True), (True, False), (True, True)]
)
def test_lift_invariants(dedupe, compress):
    trie = make_py_trie("boggle-words-4.txt")
    board = "lnrsy aeiou chkmpt bdfgjvwxz"
    cells = board.split(" ")
    dedupe = False
    compress = False

    arena = create_eval_node_arena_py()
    etb = EvalTreeBoggler(trie, (2, 2))
    ibb = PyBucketBoggler(trie, (2, 2))
    assert etb.ParseBoard(board)
    t = etb.BuildTree(arena, dedupe=dedupe)
    assert t.bound == 29
    assert ibb.ParseBoard(board)
    assert 29 == ibb.UpperBound(bailout_score=123)
    max_trees = [*t.max_subtrees()]
    assert len(max_trees) == 1
    assert max_trees == [[t]]

    # Lifting a choice reduces the bound.
    # The bounds on the child cells should match what you get from ibuckets.
    tc0 = t.lift_choice(0, len(cells[0]), arena, dedupe=dedupe, compress=compress)
    assert tc0.letter == CHOICE_NODE
    assert tc0.cell == 0
    assert len(tc0.children) == len(cells[0])
    assert tc0.bound == 23
    for i, letter in enumerate(cells[0]):
        bd = " ".join(cell if j != 0 else letter for j, cell in enumerate(cells))
        assert ibb.ParseBoard(bd)
        assert ibb.UpperBound(123) == tc0.children[i].bound
    max_trees = [*tc0.max_subtrees()]
    assert len(max_trees) == len(cells[0])
    assert max_trees == [[(0, i), child] for i, child in enumerate(tc0.children)]

    # Lifting a second time reduces the bound again.
    tc1 = tc0.lift_choice(1, len(cells[1]), arena, dedupe=dedupe, compress=compress)
    assert tc1.letter == CHOICE_NODE
    assert tc1.cell == 1
    assert len(tc1.children) == len(cells[1])
    assert tc1.bound == 17
    max_trees = [*tc1.max_subtrees()]
    assert len(max_trees) == len(cells[0]) * len(cells[1])
    assert max_trees == [
        [(1, i), (0, j), child0]
        for i, child1 in enumerate(tc1.children)
        for j, child0 in enumerate(child1.children)
    ]
    for i, letter0 in enumerate(cells[0]):
        for j, letter1 in enumerate(cells[1]):
            my_cells = [*cells]
            my_cells[0] = letter0
            my_cells[1] = letter1
            bd = " ".join(my_cells)
            assert ibb.ParseBoard(bd)
            assert ibb.UpperBound(123) == tc1.children[j].children[i].bound

    tc2 = tc1.lift_choice(2, len(cells[2]), arena, dedupe=dedupe, compress=compress)
    assert tc2.letter == CHOICE_NODE
    assert tc2.cell == 2
    assert len(tc2.children) == len(cells[2])
    assert tc2.bound == 14

    tc3 = tc2.lift_choice(3, len(cells[3]), arena, dedupe=dedupe, compress=compress)
    assert tc3.letter == CHOICE_NODE
    assert tc3.cell == 3
    assert len(tc3.children) == len(cells[3])
    assert tc3.bound == 13
    n = 0
    n_non_null = 0
    for tc2 in tc3.children:
        assert tc2.letter == CHOICE_NODE
        assert len(tc2.children) == len(cells[2])
        for tc1 in tc2.children:
            assert tc1.letter == CHOICE_NODE
            assert len(tc1.children) == len(cells[1])
            for tc0 in tc1.children:
                assert tc0.letter == CHOICE_NODE
                assert len(tc0.children) == len(cells[0])
                n += len(tc0.children)
                for t in tc0.children:
                    assert not t or t.letter != CHOICE_NODE
                    if t:
                        n_non_null += 1

    assert n == math.prod(len(cell) for cell in cells)
    max_trees = [*tc3.max_subtrees()]
    assert n_non_null == len(max_trees)

    for idx in itertools.product(*(range(len(cell)) for cell in cells)):
        i0, i1, i2, i3 = idx
        bd = " ".join(cells[i][letter] for i, letter in enumerate(idx))
        assert ibb.ParseBoard(bd)
        ibb.UpperBound(123)
        score = ibb.Details().max_nomark
        print(idx, bd, score)
        t = tc3.children[i3].children[i2].children[i1].children[i0]
        assert score == (t.bound if t else 0)
        # print(t.to_string(etb))


def test_lift_invariants_22():
    trie = make_py_trie("boggle-words-4.txt")
    board = "ny ae ch ."
    cells = board.split(" ")
    etb = EvalTreeBoggler(trie, dims=(2, 2))
    etb.ParseBoard(board)
    t = etb.BuildTree(dedupe=True)
    t.assert_invariants(etb)

    scores = t.eval_all(cells)

    # Try lifting each cell; this should not affect any scores.
    for i, cell in enumerate(cells):
        if len(cell) <= 1:
            continue
        tl = t.lift_choice(i, len(cell), compress=True, dedupe=True)
        print(tl.to_string(etb))
        print("---")
        lift_scores = tl.eval_all(cells)
        assert lift_scores == scores
        tl.assert_invariants(etb)


def test_lift_invariants_33():
    trie = make_py_trie("boggle-words-9.txt")
    board = ". . . . lnrsy e aeiou aeiou ."
    # board = ". . . . rs e io au ."
    cells = board.split(" ")
    etb = EvalTreeBoggler(trie, dims=(3, 3))
    etb.ParseBoard(board)
    t = etb.BuildTree(dedupe=True)
    t.assert_invariants(etb)

    scores = t.eval_all(cells)

    bb = PyBucketBoggler(trie, dims=(3, 3))
    for choices, score in scores.items():
        this_board = " ".join([cells[i][choice] for i, choice in enumerate(choices)])
        bb.ParseBoard(this_board)
        bb.UpperBound(500_000)
        assert score == bb.Details().max_nomark

    # Try lifting each cell; this should not affect any scores.
    for i, cell in enumerate(cells):
        if len(cell) <= 1:
            continue
        tl = t.lift_choice(i, len(cell))
        lift_scores = tl.eval_all(cells)
        assert lift_scores == scores
        tl.assert_invariants(etb)

    # Do a second lift and check again.
    t2 = tl.lift_choice(0, len(cell[0]))
    lift_scores = t2.eval_all(cells)
    assert lift_scores == scores
    t2.assert_invariants(etb)
