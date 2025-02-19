from cpp_boggle import BucketBoggler34, Trie

from boggle.ibucket_breaker import even_split


def test_even_split():
    assert even_split([1, 2, 3], 4) == [[1], [2], [3]]
    assert even_split([1, 2, 3, 4], 4) == [[1], [2], [3], [4]]
    assert even_split([1, 2, 3, 4, 5], 4) == [[1, 2], [3], [4], [5]]
    assert even_split([1, 2, 3, 4, 5, 6, 7], 3) == [[1, 2, 3], [4, 5], [6, 7]]


def test_bucket_boggle34():
    t = Trie.CreateFromFile("wordlists/enable2k.txt")
    bb = BucketBoggler34(t)
    # s l p i a e n t r d e s
    assert bb.ParseBoard(
        "lnrsy lnrsy chkmpt aeiou aeiou aeiou lnrsy chkmpt lnrsy bdfgjvwxz aeiou lnrsy"
    )
    assert bb.UpperBound(1_000_000) > 1600
    d = bb.Details()
    print(d.max_nomark, d.sum_union)
    assert d.max_nomark == 57_158
    assert d.sum_union == 353_018

    # assert bb.ParseBoard('s l p i a e n t r d e s')
    assert bb.ParseBoard("s i n d l a t e p e r s")
    assert bb.UpperBound(1_000_000) > 1600
    d = bb.Details()
    print(d.max_nomark, d.sum_union)
    assert d.max_nomark == 1847
    assert d.sum_union == 1651
