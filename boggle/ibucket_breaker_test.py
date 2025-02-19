from boggle.ibucket_breaker import even_split


def test_even_split():
    assert even_split([1, 2, 3], 4) == [[1], [2], [3]]
    assert even_split([1, 2, 3, 4], 4) == [[1], [2], [3], [4]]
    assert even_split([1, 2, 3, 4, 5], 4) == [[1, 2], [3], [4], [5]]
    assert even_split([1, 2, 3, 4, 5, 6, 7], 3) == [[1, 2, 3], [4, 5], [6, 7]]
