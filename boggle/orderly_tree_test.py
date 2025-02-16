import pytest
from cpp_boggle import Trie

from boggle.dimensional_bogglers import cpp_orderly_tree_builder
from boggle.eval_tree import EvalNode, eval_node_to_string
from boggle.orderly_tree_builder import OrderlyTreeBuilder
from boggle.trie import PyTrie, make_py_trie

WRITE_SNAPSHOTS = False


def snapshot(value: str, filename: str, is_readonly=False):
    if WRITE_SNAPSHOTS and not is_readonly:
        with open(filename, "w") as out:
            out.write(value)
    expected = open(filename).read()
    assert value == expected


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
    is_python = isinstance(t, EvalNode)
    is_readonly = not is_python
    snapshot(
        eval_node_to_string(t, cells),
        "testdata/sepeathtc-tree.txt",
        is_readonly=is_readonly,
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

    is_python = isinstance(t, EvalNode)
    is_readonly = not is_python
    snapshot(
        eval_node_to_string(t, cells),
        "testdata/orderly-3x3.txt",
        is_readonly=is_readonly,
    )
