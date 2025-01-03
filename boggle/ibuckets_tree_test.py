from boggle.boggle import PyTrie
from boggle.ibuckets_tree import TreeBucketBoggler

BIGINT = 1_000_000


def test_tar_tier():
    # This is the motivating example for choice trees, see
    # https://www.danvk.org/wp/2009-08-11/a-few-more-boggle-examples/

    t = PyTrie()
    t.AddWord("tar")
    t.AddWord("tie")
    t.AddWord("tier")
    t.AddWord("tea")
    t.AddWord("the")

    #  t i .
    # ae . .
    #  r . .
    bb = TreeBucketBoggler(t)
    assert bb.ParseBoard("t i z ae z z r z z")

    # With no force, we match the behavior of scalar ibuckets
    assert 3 == bb.UpperBound(BIGINT, set())
    assert 3 == bb.Details().sum_union
    assert 3 == bb.Details().max_nomark
    assert 2 == bb.NumReps()

    # A force on an irrelevant cell has no effect
    assert 3 == bb.UpperBound(BIGINT, {0})

    # A force on the choice cell reduces the bound.
    assert 2 == bb.UpperBound(BIGINT, {3})
