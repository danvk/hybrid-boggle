import itertools
import math

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
    ChoiceNode,
    SumNode,
    eval_all,
    eval_node_to_string,
    merge_orderly_tree,
    split_orderly_tree,
)
from boggle.ibuckets import PyBucketBoggler
from boggle.orderly_tree_builder import (
    OrderlyTreeBuilder,
    WordPath,
    dedupe_paths_for_word,
)
from boggle.split_order import SPLIT_ORDER
from boggle.trie import PyTrie, make_py_trie

TRIE_BUILDER_PARAMS = [(PyTrie, OrderlyTreeBuilder), (Trie, cpp_orderly_tree_builder)]


@pytest.mark.parametrize("TrieT, TreeBuilderT", TRIE_BUILDER_PARAMS)
def test_build_orderly_tree(TrieT, TreeBuilderT):
    words = [
        "sea",
        "seat",
        "seats",
        "tea",
        "teas",
    ]
    t = TrieT.create_from_wordlist(words)

    bb = TreeBuilderT(t, (3, 3))
    arena = bb.create_arena()

    # s e h
    # e a t
    # p u c
    board = "s e p e a u h t c"
    cells = board.split(" ")
    assert bb.parse_board(board)
    t = bb.build_tree(arena)
    if isinstance(t, SumNode):
        t.assert_invariants(bb)
    assert outsource(eval_node_to_string(t, cells)) == snapshot(
        external("d7687d76c39b*.txt")
    )


@pytest.mark.parametrize("TrieT, TreeBuilderT", TRIE_BUILDER_PARAMS)
def test_build_force_tree_no_force(TrieT, TreeBuilderT):
    words = ["bee", "fee", "beef"]
    t = TrieT.create_from_wordlist(words)
    bb = TreeBuilderT(t, (2, 2))
    bb.dedupe_forced = False
    arena = bb.create_arena()

    # bf ae
    #  f ae
    board = "bf fg ae ae"
    assert bb.parse_board(board)
    t0 = bb.build_tree(arena)
    assert t0.bound == 3  # one bee, one beef, two fees (but can't both count)

    t1s = t0.orderly_force_cell(0, 2, arena)
    assert t1s[1].bound == 2  # two fees

    board1 = "f fg ae ae"
    assert bb.parse_board(board1)
    t1 = bb.build_tree(arena)
    assert t1.bound == 2  # still two fees when building the tree


@pytest.mark.parametrize("TrieT, TreeBuilderT", TRIE_BUILDER_PARAMS)
def test_build_force_tree_force(TrieT, TreeBuilderT):
    words = ["bee", "fee", "beef"]
    t = TrieT.create_from_wordlist(words)
    bb = TreeBuilderT(t, (2, 2))
    bb.dedupe_forced = True
    arena = bb.create_arena()

    # bf ae
    #  f ae
    board = "bf fg ae ae"
    assert bb.parse_board(board)
    t0 = bb.build_tree(arena)
    assert t0.bound == 3  # one bee, one beef, two fees (but can't both count)

    t1s = t0.orderly_force_cell(0, 2, arena)
    assert t1s[1].bound == 2  # two fees when you force

    board1 = "f fg ae ae"
    assert bb.parse_board(board1)
    t1 = bb.build_tree(arena)
    assert t1.bound == 1  # just one fee with deduplicating when building the tree


OTB_PARAMS = [
    (make_py_trie, OrderlyTreeBuilder),
    (Trie.create_from_file, cpp_orderly_tree_builder),
]


def get_trie_otb(dict_file: str, dims: tuple[int, int], is_python: bool):
    if is_python:
        trie = make_py_trie(dict_file)
        otb = OrderlyTreeBuilder(trie, dims=dims)
    else:
        trie = Trie.create_from_file(dict_file)
        otb = cpp_orderly_tree_builder(trie, dims=dims)
    return trie, otb


@pytest.mark.parametrize("make_trie, get_tree_builder", OTB_PARAMS)
def test_lift_invariants_33(make_trie, get_tree_builder):
    trie = make_trie("testdata/boggle-words-9.txt")
    board = ". . . . lnrsy e aeiou aeiou ."
    # board = ". . . . nr e ai au ."
    cells = board.split(" ")
    otb = get_tree_builder(trie, dims=(3, 3))
    otb.parse_board(board)
    arena = otb.create_arena()
    t = otb.build_tree(arena)
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
    otb.parse_board(board)
    arena = otb.create_arena()
    t = otb.build_tree(arena)
    if isinstance(t, SumNode):
        t.assert_invariants(otb)
    assert t.bound == 8

    failures = t.orderly_bound(6, cells, SPLIT_ORDER[(2, 2)], [])
    assert failures == [(8, "adeg"), (7, "adeh")]


@pytest.mark.parametrize("is_python", [True, False])
def test_orderly_no_words(is_python):
    _, otb = get_trie_otb("testdata/boggle-words-4.txt", (2, 2), is_python)
    board = "cd cd cd cd"
    cells = board.split(" ")
    # num_letters = [len(cell) for cell in cells]
    otb.parse_board(board)
    arena = otb.create_arena()
    t = otb.build_tree(arena)
    if isinstance(t, SumNode):
        t.assert_invariants(otb)
    assert t.bound == 0

    failures = t.orderly_bound(6, cells, SPLIT_ORDER[(2, 2)], [])
    assert failures == []


@pytest.mark.parametrize("make_trie, get_tree_builder", OTB_PARAMS)
def test_orderly_bound22_best(make_trie, get_tree_builder):
    trie = make_trie("testdata/boggle-words-4.txt")
    board = "st ea ea tr"
    cells = board.split(" ")
    # num_letters = [len(cell) for cell in cells]
    otb = get_tree_builder(trie, dims=(2, 2))
    otb.parse_board(board)
    arena = otb.create_arena()
    t = otb.build_tree(arena)
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
    otb.parse_board(board)
    arena = otb.create_arena()
    t = otb.build_tree(arena)
    split_order = SPLIT_ORDER[(2, 2)]
    if isinstance(t, SumNode):
        t.assert_invariants(otb)
        t.assert_orderly(split_order)
    assert t.bound == snapshot(21)

    assert isinstance(t, SumNode)
    assert len(t.children) == 2
    assert 0 in t.children
    assert 1 in t.children
    t0 = t.children[0]
    t1 = t.children[1]
    assert isinstance(t0, ChoiceNode)
    assert isinstance(t1, ChoiceNode)
    assert t0.bound == snapshot(16)
    assert len(t0.children) == 2
    assert isinstance(t1, ChoiceNode)
    assert t1.bound == 5

    choice0, tree1 = split_orderly_tree(t, arena)
    assert choice0 == t0
    assert tree1.bound == 5
    tree1.assert_orderly(split_order)
    for child in choice0.children:
        child.assert_orderly(split_order, 0)

    m0 = merge_orderly_tree(choice0.children[0], tree1, arena)
    assert m0.bound == snapshot(21)

    m1 = merge_orderly_tree(choice0.children[1], tree1, arena)
    assert m1.bound == snapshot(18)

    force = t.orderly_force_cell(0, num_letters[0], arena)
    assert len(force) == 2
    for c in force:
        c.assert_orderly(split_order)
    # force[0] corresponds to letter 0, force[1] to letter 1, etc. by construction
    assert force[0].bound == m0.bound
    assert force[1].bound == m1.bound


@pytest.mark.parametrize("is_python", [True, False])
def test_orderly_force22(is_python):
    _, otb = get_trie_otb("testdata/boggle-words-4.txt", (2, 2), is_python)
    board = "st ea ea tr"
    cells = board.split(" ")
    num_letters = [len(cell) for cell in cells]
    otb.parse_board(board)
    arena = otb.create_arena()
    t = otb.build_tree(arena)
    force = t.orderly_force_cell(0, num_letters[0], arena)

    txt = "\n\n".join(
        f"{i}: " + eval_node_to_string(t, cells, top_cell=0)
        for i, t in enumerate(force)
    )

    assert outsource(txt) == snapshot(external("7dd80d82a00c*.txt"))


@pytest.mark.parametrize("make_trie, get_tree_builder", OTB_PARAMS)
def test_orderly_bound33(make_trie, get_tree_builder):
    trie = make_trie("testdata/boggle-words-9.txt")
    board = "lnrsy chkmpt lnrsy aeiou lnrsy aeiou bdfgjvwxz lnrsy chkmpt"
    cells = board.split(" ")
    otb = get_tree_builder(trie, dims=(3, 3))
    otb.parse_board(board)
    arena = otb.create_arena()
    t = otb.build_tree(arena)
    if isinstance(t, SumNode):
        t.assert_invariants(otb)
        t.assert_orderly(SPLIT_ORDER[(3, 3)])
    assert t.bound > 500

    failures = t.orderly_bound(450, cells, SPLIT_ORDER[(3, 3)], [])
    # https://www.danvk.org/boggle/?board=stsaseblt&multiboggle=1&dims=33
    assert failures == snapshot([(470, "stsaseblt")])


# Invariants:
# - eval_all on a tree should yield the same score before and after any amount of forcing.
# - this score should match what you get from ibuckets (assuming no repeat letters)
@pytest.mark.parametrize("is_python", [True, False])
def test_force_invariants22(is_python):
    dims = (2, 2)
    trie, otb = get_trie_otb("testdata/boggle-words-4.txt", dims, is_python)
    # This has no dupes, so bounds converge to the true Boggle score
    board = "lnrsy aeiou chkmpt bdfgjvwxz"
    cells = board.split(" ")
    num_letters = [len(cell) for cell in cells]
    otb.parse_board(board)
    arena = otb.create_arena()
    root = otb.build_tree(arena)
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

    # Since the board has no repeat letters, the ibuckets bound, multiboggle score,
    # and true score are all identical to the fully-forced bound.
    boggler = (PyBoggler if is_python else cpp_boggler)(trie, dims)
    ibb = PyBucketBoggler(trie, dims)
    for idx in itertools.product(*(range(len(cell)) for cell in cells)):
        i0, i1, i2, i3 = idx
        bd = " ".join(cells[i][letter] for i, letter in enumerate(idx))
        assert ibb.parse_board(bd)
        ibb.upper_bound(123)
        score = ibb.details().max_nomark
        # print(idx, bd, score)
        assert score == all_scores[0][idx]
        assert score == all_scores[1][idx]
        assert score == all_scores[2][idx]
        assert score == all_scores[3][idx]
        assert score == all_scores[4][idx]

        t = choices_to_trees[4][(0, i0), (1, i1), (2, i2), (3, i3)]
        assert score == (t.bound if t else 0)
        assert score == PyBoggler.multiboggle_score(boggler, bd.replace(" ", ""))
        assert score == boggler.score(bd.replace(" ", ""))
        # print(t.to_string(etb))


def test_build_invariants44():
    is_python = False  # Python is pretty slow for this one.
    dims = (4, 4)
    trie, otb = get_trie_otb("wordlists/enable2k.txt", dims, is_python)
    board = "bdfgjqvwxz e s bdfgjqvwxz r r n e e e e h bdfgjqvwxz t e bdfgjqvwxz"
    cells = board.split(" ")

    arena = otb.create_arena()
    assert otb.parse_board(board)
    root = otb.build_tree(arena)
    assert root.bound == snapshot(3858)

    # the orderly bound is only a bit better for this board thanks to all the repeat "e"s.
    ibb = cpp_bucket_boggler(trie, dims)
    assert ibb.parse_board(board)
    ibb.upper_bound(123_456)
    ibuckets_score = ibb.details().max_nomark
    assert ibuckets_score == snapshot(4348)

    scores = eval_all(root, cells)

    # the scores converge on the multiboggle score once you force all the cells
    best_score = 0
    boggler = cpp_boggler(trie, (4, 4))
    for idx in itertools.product(*(range(len(cell)) for cell in cells)):
        bd = "".join(cells[i][letter] for i, letter in enumerate(idx))
        score = PyBoggler.multiboggle_score(boggler, bd)
        assert score == scores[idx]
        best_score = max(score, best_score)

    assert best_score == snapshot(1975)


def test_force_invariants44():
    is_python = False  # Python is pretty slow for this one.
    dims = (4, 4)
    trie, otb = get_trie_otb("wordlists/enable2k.txt", dims, is_python)
    base_board = "bdfgjqvwxz ae hklnrsty bdfgjqvwxz hklnrsty hklnrsty hklnrsty ai ao au ae hklnrsty bdfgjqvwxz hklnrsty ae bdfgjqvwxz"

    base_cells = base_board.split(" ")
    base_num_letters = [len(cell) for cell in base_cells]

    arena = otb.create_arena()
    assert otb.parse_board(base_board)
    root = otb.build_tree(arena)
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
    assert otb.parse_board(board)
    direct_root = otb.build_tree(arena)

    # The direct tree's bound is much higher because the cells with single letters
    # interfere with the other choices and desynchronize them. Despite this, it _is_
    # the same tree, which eval_all demonstrates.
    assert direct_root.bound == snapshot(557)
    direct_scores = eval_all(direct_root, cells)

    assert forced_scores == direct_scores

    # These scores should all match the multiboggle score
    indices = [base_cells[i].index(c) for i, c in enumerate(cells)]
    boggler = cpp_boggler(trie, dims)
    for seq, root_score in forced_scores.items():
        for cell in unforced_cells:
            indices[cell] = seq[cell]
            cells[cell] = base_cells[cell][seq[cell]]
        bd = "".join(cells)
        multiboggle_score = PyBoggler.multiboggle_score(boggler, bd)
        forced_score = t.score_with_forces(indices)
        assert forced_score == root_score
        assert multiboggle_score == root_score


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
    assert otb.parse_board(" ".join(base_cells))
    root = otb.build_tree(arena)
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


def test_dedupe_wordpaths():
    #  (3)
    # [(2, 0), (3, 0), (4, 0)] (1)
    short = WordPath(
        path=[(2, 0), (3, 0), (4, 0)], word_id=1, points=1, cell_mask=4 + 8 + 16
    )
    long = WordPath(
        path=[(1, 0), (2, 0), (3, 0), (4, 0)],
        word_id=1,
        points=1,
        cell_mask=2 + 4 + 8 + 16,
    )
    wps = [short, long]

    assert dedupe_paths_for_word(wps) == ([short], [long])

    # 55 [(2, 0), (3, 0), (4, 0)] (1) mana
    # 56 [(1, 0), (2, 0), (3, 0), (4, 0)] (1) mana


@pytest.mark.parametrize("is_python", [True, False])
def test_forced_tree_32(is_python):
    dims = (2, 3)
    trie, otb = get_trie_otb("wordlists/enable2k.txt", dims, is_python)
    board = "r nr ae mt ae n"
    otb.dedupe_forced = True
    assert otb.parse_board(board)
    arena = otb.create_arena()
    t = otb.build_tree(arena)
    assert t.bound == 32
    assert t.node_count() == 102
    cells = board.split(" ")
    assert outsource(eval_node_to_string(t, cells)) == snapshot(
        external("35fcf2479a9f*.txt")
    )


# @pytest.mark.parametrize("is_python", [True, False])
def test_subtraction_tree(is_python=True):
    dims = (2, 3)
    trie, otb = get_trie_otb("wordlists/enable2k.txt", dims, is_python)
    board = "nr lnrsy aeiou mt ae nr"
    otb.dedupe_forced = False
    assert otb.parse_board(board)
    arena = otb.create_arena()
    t = otb.build_tree(arena)
    assert t.bound == 91

    board_force2 = "r r aeiou mt ae nr"
    assert otb.parse_board(board_force2)
    tf2 = otb.build_tree(arena)
    assert tf2.bound == 45

    otb.dedupe_forced = True
    assert otb.parse_board(board_force2)
    tf2dd = otb.build_tree(arena)
    assert tf2dd.bound == 26

    t0s = t.orderly_force_cell(0, 2, arena)
    assert t0s[1].bound == 85

    t1s = t0s[1].orderly_force_cell(1, 5, arena)
    rr = t1s[2]
    assert rr.bound == 41

    # back to the original board
    otb.dedupe_forced = False
    assert otb.parse_board(board)
    t = otb.build_tree(arena)
    assert t.bound == 91

    st = otb.build_subtraction_tree([1, 2], arena)
    print(st.bound)
    print(st.node_count())
    assert False
