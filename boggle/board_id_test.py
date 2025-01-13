from boggle.board_id import (
    board_id,
    from_board_id,
    get_canonical_board_id,
    is_canonical_board_id,
    to_1d,
    to_2d,
)


def test_board_id_round_trip33():
    classes = ["a", "b", "c", "d"]
    board = from_board_id(classes, (3, 3), 0)
    assert board == "a a a a a a a a a"
    assert board_id([[0, 0, 0], [0, 0, 0], [0, 0, 0]], (3, 3), 4) == 0

    board = from_board_id(classes, (3, 3), 100068)
    assert board == "a b c d c b a c b"
    assert board_id(to_2d([0, 1, 2, 3, 2, 1, 0, 2, 1], (3, 3)), (3, 3), 4) == 100068

    board = from_board_id(classes, (3, 3), 4309)
    assert board == "b b b d a a b a a"
    assert board_id(to_2d([1, 1, 1, 3, 0, 0, 1, 0, 0], (3, 3)), (3, 3), 4) == 4309


def test_is_canonical_board_id33():
    assert is_canonical_board_id(4, (3, 3), 0)
    assert not is_canonical_board_id(4, (3, 3), 100068)
    assert not is_canonical_board_id(4, (3, 3), 4309)


def test_best_34():
    best = "s i n d l a t e p e r s".split(" ")
    classes = ["bdfgjvwxz", "aeiou", "lnrsy", "chkmpt"]
    best_class = " ".join([next(c for c in classes if x in c) for x in best])
    assert (
        best_class
        == "lnrsy aeiou lnrsy bdfgjvwxz lnrsy aeiou chkmpt aeiou chkmpt aeiou lnrsy lnrsy"
    )
    best_idxs = [next(i for i, c in enumerate(classes) if x in c) for x in best]
    assert best_idxs == [2, 1, 2, 0, 2, 1, 3, 1, 3, 1, 2, 2]
    best_idxs2d = to_2d(best_idxs, (3, 4))
    assert best_idxs2d == [
        [2, 2, 3],  # SLP
        [1, 1, 1],  # IAE
        [2, 3, 2],  # NTR
        [0, 1, 2],  # DES
    ]
    assert board_id(best_idxs2d, (3, 4), 4) == 10974758
    assert from_board_id(classes, (3, 4), 10974758) == best_class
    assert get_canonical_board_id(4, (3, 4), 10974758) == 2520743

    canonical_best_class = from_board_id(classes, (3, 4), 2520743)
    best_2d = to_2d(canonical_best_class.split(" "), (3, 4))
    assert best_2d == [
        ["chkmpt", "lnrsy", "lnrsy"],  # P L S
        ["aeiou", "aeiou", "aeiou"],  # E A I
        ["lnrsy", "chkmpt", "lnrsy"],  # R T N
        ["lnrsy", "aeiou", "bdfgjvwxz"],  # S E D
    ]


def test_2d_1d_round_trip():
    board = "sindlatepers"
    bd2d = to_2d(board, (3, 4))
    assert bd2d == [
        ["s", "l", "p"],  #
        ["i", "a", "e"],
        ["n", "t", "r"],
        ["d", "e", "s"],
    ]
    assert to_1d(bd2d) == [*board]
