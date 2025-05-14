import itertools
import math
import time

import pytest
from cpp_boggle import Trie
from inline_snapshot import external, outsource, snapshot

from boggle.boggler import PyBoggler
from boggle.dimensional_bogglers import (
    cpp_boggler,
    cpp_bucket_boggler,
    cpp_orderly_tree_builder,
)
from boggle.eval_node import (
    ROOT_NODE,
    ChoiceNode,
    SumNode,
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
    if isinstance(t, SumNode):
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
    if isinstance(t, SumNode):
        t.assert_invariants(otb)

    assert outsource(eval_node_to_string(t, cells)) == snapshot(
        external("1f0fc29ed9ce*.txt")
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
    if isinstance(t, SumNode):
        t.assert_invariants(otb)
    assert t.bound == 8

    failures = t.orderly_bound(6, cells, SPLIT_ORDER[(2, 2)], [])
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
    if isinstance(t, SumNode):
        t.assert_invariants(otb)
    assert t.bound == snapshot(21)

    failures = t.orderly_bound(15, cells, SPLIT_ORDER[(2, 2)], [])
    assert failures == snapshot(
        [
            (18, "seat"),
            (17, "sear"),
            (18, "saet"),
            (17, "saer"),
            (15, "teat"),
            (15, "tear"),
            (15, "taet"),
            (15, "taer"),
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
    if isinstance(t, SumNode):
        t.assert_invariants(otb)
        t.assert_orderly(split_order)
    assert t.bound == snapshot(21)

    assert isinstance(t, SumNode)
    assert t.letter == ROOT_NODE
    assert len(t.children) == 2
    t0 = t.children[0]
    t1 = t.children[1]
    assert isinstance(t0, ChoiceNode)
    assert t0.cell == 0
    assert t0.bound == snapshot(16)
    assert len(t0.children) == 2
    assert isinstance(t1, ChoiceNode)
    assert t1.cell == 1
    assert t1.bound == 5

    choice0, tree1 = split_orderly_tree(t, arena)
    assert choice0 == t0
    assert tree1.bound == 5
    tree1.assert_orderly(split_order)
    for child in choice0.children:
        child.assert_orderly(split_order)

    m0 = merge_orderly_tree(choice0.children[0], tree1, arena)
    assert m0.bound == snapshot(21)

    m1 = merge_orderly_tree(choice0.children[1], tree1, arena)
    assert m1.bound == snapshot(18)

    force = t.orderly_force_cell(0, num_letters[0], arena)
    assert len(force) == 2
    for c in force:
        c.assert_orderly(split_order)
    assert force[0].letter == 0
    assert force[0].bound == m0.bound
    assert force[1].letter == 1
    assert force[1].bound == m1.bound


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
        f"{i}: " + eval_node_to_string(t, cells, top_cell=0)
        for i, t in enumerate(force)
    )

    assert outsource(txt) == snapshot(external("7e73f64f3fe0*.txt"))


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
    if isinstance(t, SumNode):
        t.assert_invariants(otb)
        print(otb.cell_counts)
        t.assert_orderly(SPLIT_ORDER[(3, 3)])
    assert t.bound > 500

    # node_counts = t.node_counts()
    start_s = time.time()
    failures = t.orderly_bound(500, cells, SPLIT_ORDER[(3, 3)], [])
    print(time.time() - start_s)
    # XXX lower the cutoff to get a board out
    # break_all reports 889 points for this board, but ibucket_solver reports 512
    assert failures == snapshot([])
    # assert False


# Invariants:
# - eval_all on a tree should yield the same score before and after any amount of forcing.
# - this score should match what you get from ibuckets
@pytest.mark.parametrize("is_python", [True, False])
def test_force_invariants22(is_python):
    dims = (2, 2)
    trie, otb = get_trie_otb("testdata/boggle-words-4.txt", dims, is_python)
    # This has no dupes, so bounds converge to the true Boggle score
    board = "lnrsy aeiou chkmpt bdfgjvwxz"
    cells = board.split(" ")
    num_letters = [len(cell) for cell in cells]
    otb.ParseBoard(board)
    arena = otb.create_arena()
    root = otb.BuildTree(arena)
    # print(t.to_dot(cells))

    scores = eval_all(root, cells)
    # This keeps the Python & C++ implementations in sync with each other.
    assert outsource(str(scores)) == snapshot(external("cdc47ced1c1f*.txt"))

    # This forces every possible sequence and evaluates all remaining possibilities.
    # If we ever get a null value out of a force, it and its desendants become zeroes.
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
    assert len(choices_to_trees) == 5

    boggler = (PyBoggler if is_python else cpp_boggler)(trie, dims)
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
        assert score == all_scores[4][idx]

        t = choices_to_trees[4][(0, i0), (1, i1), (2, i2), (3, i3)]
        assert score == (t.bound if t else 0)
        assert score == PyBoggler.multiboggle_score(boggler, bd.replace(" ", ""))
        # print(t.to_string(etb))


def test_build_invariants44():
    is_python = False  # Python is pretty slow for this one.
    dims = (4, 4)
    trie, otb = get_trie_otb("wordlists/enable2k.txt", dims, is_python)
    board = "bdfgjqvwxz e s bdfgjqvwxz r r n e e e e h bdfgjqvwxz t e bdfgjqvwxz"
    cells = board.split(" ")

    arena = otb.create_arena()
    assert otb.ParseBoard(board)
    root = otb.BuildTree(arena)
    assert root.bound == snapshot(3858)

    # XXX this is no longer true
    # this is a better bound than orderly, for which this is a worst-case scenario
    ibb = cpp_bucket_boggler(trie, dims)
    assert ibb.ParseBoard(board)
    ibb.UpperBound(123_456)
    ibuckets_score = ibb.Details().max_nomark
    assert ibuckets_score == snapshot(4348)

    scores = eval_all(root, cells)

    # the scores converge once you force all the cells
    best_score = 0
    boggler = cpp_boggler(trie, (4, 4))
    for idx in itertools.product(*(range(len(cell)) for cell in cells)):
        bd = "".join(cells[i][letter] for i, letter in enumerate(idx))
        # assert ibb.ParseBoard(bd)
        # ibb.UpperBound(123_456)
        # score = ibb.Details().max_nomark
        score = PyBoggler.multiboggle_score(boggler, bd)
        assert score == scores[idx], f"{idx} {bd}"
        best_score = max(score, best_score)

    assert best_score == snapshot(2994)


def test_force_invariants44():
    is_python = False  # Python is pretty slow for this one.
    dims = (4, 4)
    trie, otb = get_trie_otb("wordlists/enable2k.txt", dims, is_python)
    base_board = "bdfgjqvwxz ae hklnrsty bdfgjqvwxz hklnrsty hklnrsty hklnrsty ai ao au ae hklnrsty bdfgjqvwxz hklnrsty ae bdfgjqvwxz"

    base_cells = base_board.split(" ")
    base_num_letters = [len(cell) for cell in base_cells]

    arena = otb.create_arena()
    assert otb.ParseBoard(base_board)
    root = otb.BuildTree(arena)
    assert root.bound == snapshot(15051)

    forces = [
        (5, 0),
        (6, 1),
        (9, 1),
        (10, 1),
        (1, 1),
        (13, 6),
        (2, 5),
        (14, 1),
        (4, 4),
        (7, 1),
        (8, 1),
        (11, 0),
    ]

    t = root
    cells = [*base_cells]
    unforced_cells = {*range(16)}
    for cell, letter in forces:
        forces = t.orderly_force_cell(cell, base_num_letters[cell], arena)
        t = forces[letter]
        cells[cell] = cells[cell][letter]
        unforced_cells.remove(cell)

    assert t.bound == snapshot(320)
    forced_scores = eval_all(t, cells)

    board = " ".join(cells)
    cells = board.split(" ")
    assert otb.ParseBoard(board)
    direct_root = otb.BuildTree(arena)

    # The direct tree's bound is much higher because the cells with single letters
    # interfere with the other choices and desynchronize them. Despite this, it _is_
    # the same tree, which eval_all demonstrates.
    assert direct_root.bound == snapshot(557)
    direct_scores = eval_all(direct_root, cells)

    assert forced_scores == direct_scores

    # These scores should all match max_nomark from ibuckets.
    # indices = [base_cells[i].index(c) for i, c in enumerate(cells)]
    # ibb = cpp_bucket_boggler(trie, dims)
    # for seq, root_score in forced_scores.items():
    #     for cell in unforced_cells:
    #         indices[cell] = seq[cell]
    #         cells[cell] = base_cells[cell][seq[cell]]
    #     bd = " ".join(cells)
    #     assert ibb.ParseBoard(bd)
    #     ibb.UpperBound(123_456)
    #     ibuckets_score = ibb.Details().max_nomark
    #     forced_score = t.score_with_forces(indices)
    #     assert forced_score == root_score
    #     assert ibuckets_score == root_score


def test_missing_top_choice():
    is_python = False  # Python is pretty slow for this one.
    dims = (4, 4)
    # TODO: cache the trie across tests
    trie, otb = get_trie_otb("wordlists/enable2k.txt", dims, is_python)
    base_cells = [
        "bcdfghjklmnpqrtvwxz",
        "bcdfgmpqvwxz",
        "aeijou",
        "bcdfghjklmnpqrtvwxz",
        "hklnrsty",
        "ej",  # 5
        "vw",  # 6
        "bcdfgmpqvwxz",
        "bcdfgmpqvwxz",
        "ej",  # 9
        "hklnrsty",
        "hklnrsty",
        "bcdfghjklmnpqrtvwxz",
        "aeijou",
        "hklnrsty",
        "aeiosuy",
    ]
    base_num_letters = [len(cell) for cell in base_cells]
    arena = otb.create_arena()
    assert otb.ParseBoard(" ".join(base_cells))
    root = otb.BuildTree(arena)
    assert root.bound == snapshot(21049)

    forces = [
        (5, 0),
        (6, 0),
        (9, 0),
        (10, 4),
        (1, 0),
        (13, 1),
        (2, 3),
        (14, 5),
        (4, 4),
        (7, 6),
        (8, 8),
        (11, 4),
        (0, 13),
        (12, 13),
        (3, 3),  # this force triggers the "!top_choice" path in OrderlyForceCell
        (15, 0),
    ]

    t = root
    cells = [*base_cells]
    unforced_cells = {*range(16)}
    for cell, letter in forces:
        forces = t.orderly_force_cell(cell, base_num_letters[cell], arena)
        t = forces[letter]
        cells[cell] = cells[cell][letter]
        unforced_cells.remove(cell)

    # https://www.danvk.org/boggle/?board=rbjfrevpverrresa&multiboggle=1
    assert t.bound == snapshot(1029)
