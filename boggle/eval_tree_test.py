import pytest
from cpp_boggle import EvalNode as CppEvalNode
from cpp_boggle import TreeBuilder33, Trie

from boggle.eval_tree import (
    CHOICE_NODE,
    EvalNode,
    EvalTreeBoggler,
    merge_trees,
)
from boggle.ibuckets import PyBucketBoggler
from boggle.trie import PyTrie, make_lookup_table

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
    assert bb.ParseBoard("t i z ae z z r z z")

    # With no force, we match the behavior of scalar ibuckets
    t = bb.BuildTree()
    assert 3 == bb.Details().sum_union
    assert 3 == bb.Details().max_nomark
    assert 2 == bb.NumReps()
    assert 3 == t.bound
    assert 3 == t.recompute_score()
    t.check_consistency()
    print(t.to_string(bb))

    # A force on an irrelevant cell has no effect
    t0 = t.force_cell(0, 1)
    # assert len(t0) == 1
    # assert t0[0].bound == 3
    # t0[0].check_consistency()
    assert isinstance(t0, EvalNode)
    assert t0.bound == 3
    t0.check_consistency()

    # A force on the choice cell reduces the bound.
    t3 = t.force_cell(3, 2)
    # print(t3.to_string(bb))
    assert len(t3) == 2
    assert t3[0].bound == 1
    assert t3[1].bound == 2
    t3[0].check_consistency()
    t3[1].check_consistency()


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


PARAMS = [(PyTrie, EvalTreeBoggler), (Trie, TreeBuilder33)]


@pytest.mark.parametrize("TrieT, TreeBuilderT", PARAMS)
def test_cpp_equivalence(TrieT, TreeBuilderT):
    t = TrieT()
    t.AddWord("sea")
    t.AddWord("seat")
    t.AddWord("seats")
    t.AddWord("tea")
    t.AddWord("teas")

    bb = TreeBuilderT(t)

    assert bb.ParseBoard("a b c d e f g h i")
    tree = bb.BuildTree()
    assert 0 == bb.Details().sum_union
    assert 0 == bb.Details().max_nomark
    assert 0 == tree.recompute_score()
    assert 1 == tree.node_count()

    # s e h
    # e a t
    # p u c
    print("sepeauhtc")
    assert bb.ParseBoard("s e p e a u h t c")
    tree = bb.BuildTree()
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
    tree = bb.BuildTree()
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

    tree = bb.BuildTree()
    assert 2 + 4 == bb.Details().sum_union  # all but "hiccup"
    assert 4 == bb.Details().max_nomark  # sea(t(s))
    assert 4 == tree.recompute_score()
    assert 4 == tree.recompute_score()
    assert 4 == tree.bound
    assert 20 == tree.node_count()


@pytest.mark.parametrize("TrieT, TreeBuilderT", PARAMS)
def test_cpp_force_equivalence(TrieT, TreeBuilderT):
    t = TrieT()
    t.AddWord("tar")
    t.AddWord("tie")
    t.AddWord("tier")
    t.AddWord("tea")
    t.AddWord("the")

    bb = TreeBuilderT(t)

    #  t i .
    # ae . .
    #  r . .
    assert bb.ParseBoard("t i z ae z z r z z")

    # With no force, we match the behavior of scalar ibuckets
    t = bb.BuildTree()
    assert 3 == bb.Details().sum_union
    assert 3 == bb.Details().max_nomark
    assert 2 == bb.NumReps()
    assert 3 == t.bound
    assert 3 == t.recompute_score()
    # t.check_consistency()
    # print(t.to_string(bb))

    # A force on an irrelevant cell has no effect
    t0 = t.force_cell(0, 1)
    # assert len(t0) == 1
    # assert t0[0].bound == 3
    # t0[0].check_consistency()
    assert isinstance(t0, (EvalNode, CppEvalNode))
    assert t0.bound == 3
    # t0.check_consistency()

    # A force on the choice cell reduces the bound.
    t3 = t.force_cell(3, 2)
    # print(t3.to_string(bb))
    assert len(t3) == 2
    assert t3[0].bound == 1
    assert t3[1].bound == 2
    # t3[0].check_consistency()
    # t3[1].check_consistency()

    # (C++ segfaults, I think because of a double-free.)

    forces = [-1 for _ in range(9)]
    assert t.score_with_forces(forces) == 3  # no force
    forces[3] = 0
    assert t.score_with_forces(forces) == 1
    forces[3] = 1
    assert t.score_with_forces(forces) == 2
