from break_all import even_split, from_board_id, board_id, is_canonical_id


classes = ['a', 'b', 'c', 'd']


def test_board_round_trip():
    board = from_board_id(classes, 0)
    assert board == 'a a a a a a a a a'
    assert board_id([[0, 0, 0], [0, 0, 0], [0, 0, 0]], 4) == 0

    assert is_canonical_id(4, 0)


def test_is_canonical():
    assert board_id([[0, 1, 2], [3, 2, 1], [0, 1, 2]], 4) == 149220
    assert not is_canonical_id(4, 149220)
    assert from_board_id(classes, 149220) == 'a b c d c b a b c'
    assert board_id([[2, 1, 0], [1, 2, 3], [2, 1, 0]], 4) == 28230
    assert is_canonical_id(4, 28230)


def test_even_split():
    assert even_split([1, 2, 3], 4) == [[1], [2], [3]]
    assert even_split([1, 2, 3, 4], 4) == [[1], [2], [3], [4]]
    assert even_split([1, 2, 3, 4, 5], 4) == [[1, 2], [3], [4], [5]]
    assert even_split([1, 2, 3, 4, 5, 6, 7], 3) == [[1, 2, 3], [4, 5], [6, 7]]
