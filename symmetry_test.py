from symmetry import rot90

def test_rot90():
    mat = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    expected = [
        [7, 4, 1],
        [8, 5, 2],
        [9, 6, 3],
    ]
    assert rot90(mat) == expected

def test_rot90_asym():
    mat = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
        [10, 11, 12],
    ]
    expected = [
        [10, 7, 4, 1],
        [11, 8, 5, 2],
        [12, 9, 6, 3],
    ]
    assert rot90(mat) == expected
