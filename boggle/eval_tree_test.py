from boggle.eval_tree import EvalNode, EvalTreeBoggler
from boggle.ibuckets import PyBucketBoggler
from boggle.trie import PyTrie

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


def test_equivalence():
    words = [
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
    t = PyTrie()
    for w in words:
        t.AddWord(w)
    board = ". . . . lnrsy aeiou aeiou aeiou . . . ."
    bb = PyBucketBoggler(t, (3, 4))
    bb.ParseBoard(board)
    score = bb.UpperBound(500_000)
    assert 5 == score
    assert score == bb.Details().max_nomark

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
    # print(fives[1].recompute_score())
    # fives[1].compress()
    # print(fives[1].to_dot(etb))
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
        assert bb.Details().max_nomark == fives[i].bound
        assert bb.Details().max_nomark == root.score_with_forces({5: i})
        fives[i].check_consistency()
        # Some choices may have been pruned out
        assert fives[i].choice_cells().issubset({4, 6, 7})
