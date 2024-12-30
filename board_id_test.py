from board_id import board_id, from_board_id, is_canonical_board_id


def test_board_id_round_trip33():
    classes = ['a', 'b', 'c', 'd']
    board = from_board_id(classes, (3, 3), 0)
    assert board == 'a a a a a a a a a'
    assert board_id([[0, 0, 0], [0, 0, 0], [0, 0, 0]], (3, 3), 4) == 0

    board = from_board_id(classes, (3, 3), 100068)
    assert board == 'a b c d c b a c b'
    assert board_id([[0, 1, 2], [3, 2, 1], [0, 2, 1]], (3, 3), 4) == 100068

    board = from_board_id(classes, (3, 3), 4309)
    assert board == 'b b b d a a b a a'
    assert board_id([[1, 1, 1], [3, 0, 0], [1, 0, 0]], (3, 3), 4) == 4309


def test_is_canonical_board_id33():
    assert is_canonical_board_id(4, (3, 3), 0)
    assert not is_canonical_board_id(4, (3, 3), 100068)
    assert not is_canonical_board_id(4, (3, 3), 4309)


def test_best_34():
    best = "s i n d l a t e p e r s".split(" ")
    classes = ['bdfgjvwxz', 'aeiou', 'lnrsy', 'chkmpt']
    best_class = ' '.join([next(c for c in classes if x in c) for x in best])
    assert best_class == 'lnrsy aeiou lnrsy bdfgjvwxz lnrsy aeiou chkmpt aeiou chkmpt aeiou lnrsy lnrsy'
    best_idxs = [next(i for i, c in enumerate(classes) if x in c) for x in best]
    assert best_idxs == [2, 1, 2, 0, 2, 1, 3, 1, 3, 1, 2, 2]
    best_idxs2d = [[2, 1, 2], [0, 2, 1], [3, 1, 3], [1, 2, 2]]
    assert board_id(best_idxs2d, (3, 4), 4) == 10974758
    assert from_board_id(classes, (3, 4), 10974758) == best_class
    # assert is_canonical_board_id(4, (3, 4), 9627002)
