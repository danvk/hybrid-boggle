from break_all import from_board_id, board_id, is_canonical


classes = ['a', 'b', 'c', 'd']


def test_board_round_trip():
    board = from_board_id(classes, 0)
    assert board == 'a a a a a a a a a'
    assert board_id([[0, 0, 0], [0, 0, 0], [0, 0, 0]], 4) == 0

    assert is_canonical(4, 0)
