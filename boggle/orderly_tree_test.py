import time

import pytest
from cpp_boggle import Trie
from inline_snapshot import external, outsource, snapshot

from boggle.dimensional_bogglers import cpp_orderly_tree_builder
from boggle.eval_tree import (
    CHOICE_NODE,
    ROOT_NODE,
    EvalNode,
    eval_node_to_string,
    merge_orderly_trees,
)
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
        external("e1e08ef3841e*.txt")
    )


OTB_PARAMS = [
    (make_py_trie, OrderlyTreeBuilder),
    (Trie.CreateFromFile, cpp_orderly_tree_builder),
]


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
        external("7f5b9b263a25*.txt")
    )


@pytest.mark.parametrize("make_trie, get_tree_builder", OTB_PARAMS)
def test_orderly_bound22(make_trie, get_tree_builder):
    trie = make_trie("testdata/boggle-words-4.txt")
    board = "ab cd ef gh"
    cells = board.split(" ")
    # num_letters = [len(cell) for cell in cells]
    otb = get_tree_builder(trie, dims=(2, 2))
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


def get_trie_otb(dict_file: str, dims: tuple[int, int], is_python: bool):
    if is_python:
        trie = make_py_trie(dict_file)
        otb = OrderlyTreeBuilder(trie, dims=dims)
    else:
        trie = Trie.CreateFromFile(dict_file)
        otb = cpp_orderly_tree_builder(trie, dims=dims)
    return trie, otb


def test_orderly_merge():
    is_python = True
    _, otb = get_trie_otb("testdata/boggle-words-4.txt", (2, 2), is_python)
    board = "st ea ea tr"
    # cells = board.split(" ")
    # num_letters = [len(cell) for cell in cells]
    otb.ParseBoard(board)
    arena = otb.create_arena()
    t = otb.BuildTree(arena)
    if isinstance(t, EvalNode):
        t.assert_invariants(otb)
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

    # these match what you'd get from lifting cell 0
    sum_wrap_t1 = EvalNode()
    sum_wrap_t1.cell = 0
    sum_wrap_t1.letter = t0.children[0].letter
    sum_wrap_t1.children = [t1]
    sum_wrap_t1.bound = t1.bound
    sum_wrap_t1.choice_mask = t1.choice_mask
    m00 = merge_orderly_trees([t0.children[0], sum_wrap_t1], arena)
    assert m00.bound == 21
    sum_wrap_t1.letter = t0.children[1].letter
    m01 = merge_orderly_trees([t0.children[1], sum_wrap_t1], arena)
    assert m01.bound == 22


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
    assert t.bound > 500

    # node_counts = t.node_counts()
    start_s = time.time()
    failures, _, _ = t.orderly_bound(500, cells, SPLIT_ORDER[(3, 3)], [])
    print(time.time() - start_s)
    # break_all reports 889 points for this board, but ibucket_solver reports 512
    assert failures == snapshot([(512, "stsaseblt")])
    # assert False


@pytest.mark.parametrize("make_trie, get_tree_builder", OTB_PARAMS)
def test_lift_and_bound(make_trie, get_tree_builder):
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
    assert t.bound == 889

    order = [*SPLIT_ORDER[(3, 3)]]
    cell0 = order.pop(0)

    mark = 1
    t = t.lift_choice(
        cell0, len(cells[cell0]), arena, mark, dedupe=False, compress=True
    )

    assert t.bound == 838
    assert t.letter == CHOICE_NODE
    assert t.cell == cell0
    assert len(t.children) == len(cells[cell0])

    mts = t.max_subtrees()
    assert len(mts) == len(cells[cell0])

    failures = []
    for tree, seq in t.max_subtrees():
        # start_s = time.time()
        this_failures, _, _ = tree.orderly_bound(500, cells, order, seq)
        # print(time.time() - start_s, seq, tree.bound, this_failures)
        failures += this_failures

    cell1 = order.pop(0)
    mark += 1
    t = t.lift_choice(
        cell1, len(cells[cell1]), arena, mark, dedupe=False, compress=True
    )
    assert t.bound == 714
    assert t.letter == CHOICE_NODE
    assert t.cell == cell1
    assert len(t.children) == len(cells[cell1])

    failures = []
    for tree, seq in t.max_subtrees():
        start_s = time.time()
        this_failures, _, _ = tree.orderly_bound(500, cells, order, seq)
        print(time.time() - start_s, seq, tree.bound, this_failures)
        failures += this_failures

    # (same as test_orderly_bound33)
    assert failures == snapshot([(512, "stsaseblt")])
    # assert False
