import itertools
import math
import time

import pytest
from cpp_boggle import Trie
from inline_snapshot import external, outsource, snapshot

from boggle.dimensional_bogglers import cpp_orderly_tree_builder
from boggle.eval_tree import (
    CHOICE_NODE,
    ROOT_NODE,
    EvalNode,
    eval_all,
    eval_node_to_string,
    merge_orderly_tree,
    split_orderly_tree,
)
from boggle.ibuckets import PyBucketBoggler
from boggle.orderly_tree_builder import OrderlyTreeBuilder
from boggle.split_order import SPLIT_ORDER
from boggle.trie import PyTrie, make_py_trie


@pytest.mark.parametrize(
    "TrieT, TreeBuilderT",
    [(PyTrie, OrderlyTreeBuilder), (Trie, cpp_orderly_tree_builder)],
)
def test_build_orderly_tree(TrieT, TreeBuilderT):
    t = TrieT()
    t.AddWord("sea")
    t.AddWord("seat")
    t.AddWord("seats")
    t.AddWord("tea")
    t.AddWord("teas")

    bb = TreeBuilderT(t, (3, 3))
    arena = bb.create_arena()

    # s e h
    # e a t
    # p u c
    board = "s e p e a u h t c"
    cells = board.split(" ")
    assert bb.ParseBoard(board)
    t = bb.BuildTree(arena)
    if isinstance(t, EvalNode):
        t.assert_invariants(bb)
    assert outsource(eval_node_to_string(t, cells)) == snapshot(
        external("d7687d76c39b*.txt")
    )


OTB_PARAMS = [
    (make_py_trie, OrderlyTreeBuilder),
    (Trie.CreateFromFile, cpp_orderly_tree_builder),
]


def get_trie_otb(dict_file: str, dims: tuple[int, int], is_python: bool):
    if is_python:
        trie = make_py_trie(dict_file)
        otb = OrderlyTreeBuilder(trie, dims=dims)
    else:
        trie = Trie.CreateFromFile(dict_file)
        otb = cpp_orderly_tree_builder(trie, dims=dims)
    return trie, otb


@pytest.mark.parametrize("make_trie, get_tree_builder", OTB_PARAMS)
def test_lift_invariants_33(make_trie, get_tree_builder):
    trie = make_trie("testdata/boggle-words-9.txt")
    board = ". . . . lnrsy e aeiou aeiou ."
    # board = ". . . . nr e ai au ."
    cells = board.split(" ")
    otb = get_tree_builder(trie, dims=(3, 3))
    otb.ParseBoard(board)
    arena = otb.create_arena()
    t = otb.BuildTree(arena)
    if isinstance(t, EvalNode):
        t.assert_invariants(otb)

    assert outsource(eval_node_to_string(t, cells)) == snapshot(
        external("1bc9f74c0682*.txt")
    )


@pytest.mark.parametrize("is_python", [True, False])
def test_orderly_bound22(is_python):
    _, otb = get_trie_otb("testdata/boggle-words-4.txt", (2, 2), is_python)
    board = "ab cd ef gh"
    cells = board.split(" ")
    # num_letters = [len(cell) for cell in cells]
    otb.ParseBoard(board)
    arena = otb.create_arena()
    t = otb.BuildTree(arena)
    if isinstance(t, EvalNode):
        t.assert_invariants(otb)
    assert t.bound == 8

    failures, _, _ = t.orderly_bound(6, cells, SPLIT_ORDER[(2, 2)], [])
    assert failures == [(8, "adeg"), (7, "adeh")]


@pytest.mark.parametrize("make_trie, get_tree_builder", OTB_PARAMS)
def test_orderly_bound22_best(make_trie, get_tree_builder):
    trie = make_trie("testdata/boggle-words-4.txt")
    board = "st ea ea tr"
    cells = board.split(" ")
    # num_letters = [len(cell) for cell in cells]
    otb = get_tree_builder(trie, dims=(2, 2))
    otb.ParseBoard(board)
    arena = otb.create_arena()
    t = otb.BuildTree(arena)
    if isinstance(t, EvalNode):
        t.assert_invariants(otb)
    assert t.bound == 22

    failures, _, _ = t.orderly_bound(15, cells, SPLIT_ORDER[(2, 2)], [])
    assert failures == snapshot(
        [
            (18, "seer"),
            (18, "seat"),
            (17, "sear"),
            (18, "saet"),
            (17, "saer"),
            (20, "teat"),
            (20, "taet"),
        ]
    )

    # TODO: confirm these via ibuckets


# TODO: test C++ equivalence
def test_orderly_merge():
    is_python = True
    _, otb = get_trie_otb("testdata/boggle-words-4.txt", (2, 2), is_python)
    board = "st ea ea tr"
    cells = board.split(" ")
    num_letters = [len(cell) for cell in cells]
    otb.ParseBoard(board)
    arena = otb.create_arena()
    t = otb.BuildTree(arena)
    split_order = SPLIT_ORDER[(2, 2)]
    if isinstance(t, EvalNode):
        t.assert_invariants(otb)
        t.assert_orderly(split_order)
    assert t.bound == 22

    assert t.letter == ROOT_NODE
    assert len(t.children) == 2
    t0 = t.children[0]
    t1 = t.children[1]
    assert t0.letter == CHOICE_NODE
    assert t0.cell == 0
    assert t0.bound == 17
    assert len(t0.children) == 2
    assert t1.letter == CHOICE_NODE
    assert t1.cell == 1
    assert t1.bound == 5

    choice0, tree1 = split_orderly_tree(t, arena)
    assert choice0 == t0
    assert tree1.bound == 5
    tree1.assert_orderly(split_order)
    for child in choice0.children:
        child.assert_orderly(split_order)

    m0 = merge_orderly_tree(choice0.children[0], tree1, arena)
    assert m0.bound == 21

    m1 = merge_orderly_tree(choice0.children[1], tree1, arena)
    assert m1.bound == 22

    force = t.orderly_force_cell(0, num_letters[0], arena)
    assert len(force) == 2
    for c in force:
        c.assert_orderly(split_order)
    assert force[0].cell == 0
    assert force[0].letter == 0
    assert force[0].bound == 21
    assert force[1].cell == 0
    assert force[1].letter == 1
    assert force[1].bound == 22


@pytest.mark.parametrize("is_python", [True, False])
def test_orderly_force22(is_python):
    _, otb = get_trie_otb("testdata/boggle-words-4.txt", (2, 2), is_python)
    board = "st ea ea tr"
    cells = board.split(" ")
    num_letters = [len(cell) for cell in cells]
    otb.ParseBoard(board)
    arena = otb.create_arena()
    t = otb.BuildTree(arena)
    force = t.orderly_force_cell(0, num_letters[0], arena)

    txt = "\n\n".join(
        f"{i}: " + eval_node_to_string(t, cells) for i, t in enumerate(force)
    )

    assert outsource(txt) == snapshot(external("3f6cd59206d5*.txt"))


@pytest.mark.parametrize("make_trie, get_tree_builder", OTB_PARAMS)
def test_orderly_bound33(make_trie, get_tree_builder):
    trie = make_trie("testdata/boggle-words-9.txt")
    board = "lnrsy chkmpt lnrsy aeiou lnrsy aeiou bdfgjvwxz lnrsy chkmpt"
    # board = "lnrsy chkmpt lnrsy aeiou aeiou aeiou bdfgjvwxz lnrsy chkmpt"
    cells = board.split(" ")
    # num_letters = [len(cell) for cell in cells]
    otb = get_tree_builder(trie, dims=(3, 3))
    otb.ParseBoard(board)
    arena = otb.create_arena()
    t = otb.BuildTree(arena)
    if isinstance(t, EvalNode):
        t.assert_invariants(otb)
        print(otb.cell_counts)
        t.assert_orderly(SPLIT_ORDER[(3, 3)])
    assert t.bound > 500

    # node_counts = t.node_counts()
    start_s = time.time()
    failures, _, _ = t.orderly_bound(500, cells, SPLIT_ORDER[(3, 3)], [])
    print(time.time() - start_s)
    # break_all reports 889 points for this board, but ibucket_solver reports 512
    assert failures == snapshot([(512, "stsaseblt")])
    # assert False


# Invariants:
# - eval_all on a tree should yield the same score before and after any amount of forcing.
# - this score should match what you get from ibuckets
# - this score should be independent of how you construct the tree
def test_force_invariants22():
    is_python = True
    dims = (2, 2)
    trie, otb = get_trie_otb("testdata/boggle-words-4.txt", dims, is_python)
    board = "lnrsy aeiou chkmpt bdfgjvwxz"
    cells = board.split(" ")
    num_letters = [len(cell) for cell in cells]
    otb.ParseBoard(board)
    arena = otb.create_arena()
    root = otb.BuildTree(arena)
    # print(t.to_dot(cells))

    scores = eval_all(root, cells)

    # This forces every possible sequence and evaluates all remaining possibilities.
    choices_to_trees = [{(): root}]
    all_scores = [scores]
    for i in range(4):
        next_level = {}
        next_scores = {}
        for prev_choices, tree in choices_to_trees[-1].items():
            prev_cells = [cell for cell, _letter in prev_choices]
            assert i not in prev_cells
            if tree:
                force = tree.orderly_force_cell(i, num_letters[i], arena)
            else:
                force = [None] * num_letters[i]
            assert len(force) == num_letters[i]
            # use a stand-in value for previously-forced cells
            remaining_cells = (["."] * (i + 1)) + cells[(i + 1) :]
            for letter, t in enumerate(force):
                seq = prev_choices + ((i, letter),)
                assert len(seq) == i + 1
                next_level[seq] = t
                if t is None:
                    indices = [range(len(c)) for c in remaining_cells]
                    letter_scores = {
                        choice: 0 for choice in itertools.product(*indices)
                    }
                else:
                    letter_scores = eval_all(t, remaining_cells)
                letter_seq = tuple(let for cell, let in seq)
                for score_seq, score in letter_scores.items():
                    next_scores[letter_seq + score_seq[(i + 1) :]] = score
        choices_to_trees.append(next_level)
        assert len(next_scores) == math.prod(num_letters)
        all_scores.append(next_scores)

    assert len(choices_to_trees[-1]) == math.prod(num_letters)

    ibb = PyBucketBoggler(trie, dims)
    for idx in itertools.product(*(range(len(cell)) for cell in cells)):
        i0, i1, i2, i3 = idx
        bd = " ".join(cells[i][letter] for i, letter in enumerate(idx))
        assert ibb.ParseBoard(bd)
        ibb.UpperBound(123)
        score = ibb.Details().max_nomark
        # print(idx, bd, score)
        assert score == all_scores[0][idx]
        assert score == all_scores[1][idx]
        assert score == all_scores[2][idx]
        assert score == all_scores[3][idx]

        t = choices_to_trees[4][(0, i0), (1, i1), (2, i2), (3, i3)]
        assert score == (t.bound if t else 0)
        # print(t.to_string(etb))
