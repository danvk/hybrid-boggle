from break_all import even_split
from example import BucketBoggler34, Trie


def test_even_split():
    assert even_split([1, 2, 3], 4) == [[1], [2], [3]]
    assert even_split([1, 2, 3, 4], 4) == [[1], [2], [3], [4]]
    assert even_split([1, 2, 3, 4, 5], 4) == [[1, 2], [3], [4], [5]]
    assert even_split([1, 2, 3, 4, 5, 6, 7], 3) == [[1, 2, 3], [4, 5], [6, 7]]


def test_bucket_boggle34():
    t = Trie.CreateFromFile('boggle-words.txt')
    bb = BucketBoggler34(t)
    # s l p i a e n t r d e s
    assert bb.ParseBoard('lnrsy lnrsy chkmpt aeiou aeiou aeiou lnrsy chkmpt lnrsy bdfgjvwxz aeiou lnrsy')
    assert bb.UpperBound(1600000) > 1600
    d = bb.Details()
    print(d.max_nomark, d.sum_union)

    # assert bb.ParseBoard('s l p i a e n t r d e s')
    assert bb.ParseBoard('s i n d l a t e p e r s')
    assert bb.UpperBound(1600000) > 1600
    d = bb.Details()
    print(d.max_nomark, d.sum_union)
