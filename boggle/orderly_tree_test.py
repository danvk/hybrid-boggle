import pytest
from cpp_boggle import Trie
from inline_snapshot import external, outsource, snapshot

from boggle.dimensional_bogglers import cpp_orderly_tree_builder
from boggle.eval_tree import EvalNode, eval_node_to_string
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
        external("2589552d7664*.txt")
    )


@pytest.mark.parametrize(
    "make_trie, get_tree_builder",
    [
        (make_py_trie, OrderlyTreeBuilder),
        (Trie.CreateFromFile, cpp_orderly_tree_builder),
    ],
)
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
        external("31d49f6a9eab*.txt")
    )


def test_orderly_bound22():
    trie = make_py_trie("testdata/boggle-words-4.txt")
    board = "ab cd ef gh"
    cells = board.split(" ")
    # num_letters = [len(cell) for cell in cells]
    otb = OrderlyTreeBuilder(trie, dims=(2, 2))
    otb.ParseBoard(board)
    arena = otb.create_arena()
    t = otb.BuildTree(arena)
    t.assert_invariants(otb)
    assert t.bound == 8

    failures = t.orderly_bound(6, cells, SPLIT_ORDER[(2, 2)])
    assert failures == ["adeg", "adeh"]


def test_orderly_bound33():
    trie = make_py_trie("testdata/boggle-words-9.txt")
    board = "lnrsy chkmpt lnrsy aeiou aeiou aeiou bdfgjvwxz lnrsy chkmpt"
    cells = board.split(" ")
    # num_letters = [len(cell) for cell in cells]
    otb = OrderlyTreeBuilder(trie, dims=(3, 3))
    otb.ParseBoard(board)
    arena = otb.create_arena()
    t = otb.BuildTree(arena)
    t.assert_invariants(otb)
    assert t.bound > 500

    failures = t.orderly_bound(500, cells, SPLIT_ORDER[(3, 3)])
    assert failures == ["streaedlp"]
