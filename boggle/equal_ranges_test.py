from boggle.equal_ranges import equal_ranges

#     0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
XS = [1, 1, 1, 1, 2, 2, 2, 3, 5, 7, 7, 8]


def test_partial():
    assert equal_ranges(XS, 0, 0) == []
    assert equal_ranges(XS, 0, 1) == [(1, 0, 1)]
    assert equal_ranges(XS, 0, 2) == [(1, 0, 2)]
    assert equal_ranges(XS, 3, 5) == [(1, 3, 4), (2, 4, 5)]
    assert equal_ranges(XS, 0, 3) == [(1, 0, 3)]
    assert equal_ranges(XS, 0, 4) == [(1, 0, 4)]
    assert equal_ranges(XS, 0, 5) == [(1, 0, 4), (2, 4, 5)]
    assert equal_ranges(XS, 0, 6) == [(1, 0, 4), (2, 4, 6)]


def test_equal_ranges():
    ranges = equal_ranges(XS, 0, len(XS))
    assert ranges == [
        (1, 0, 4),
        (2, 4, 7),
        (3, 7, 8),
        (5, 8, 9),
        (7, 9, 11),
        (8, 11, 12),
    ]
