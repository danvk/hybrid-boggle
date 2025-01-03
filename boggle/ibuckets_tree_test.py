from boggle.boggle import PyTrie
from boggle.ibuckets_tree import (
    MaxTree,
    TreeBucketBoggler,
    add_max_trees,
    max_of_max_trees,
    max_tree_max,
)


def test_max_tree_ops_no_default():
    scalar = 2
    scalar3 = 3
    tree = MaxTree(cell=0, choices={"a": 1, "b": 2})
    low_tree = MaxTree(cell=0, choices={"a": 1, "b": 1})
    abc_tree = MaxTree(cell=0, choices={"a": 0, "b": 7, "c": 3})

    assert add_max_trees(scalar, tree) == MaxTree(
        cell=0, choices={"a": 3, "b": 4}, default=2
    )
    assert add_max_trees(low_tree, tree) == MaxTree(cell=0, choices={"a": 2, "b": 3})
    assert add_max_trees(low_tree, scalar) == MaxTree(
        cell=0, choices={"a": 3, "b": 3}, default=2
    )
    assert add_max_trees(scalar3, scalar) == 5

    assert max_tree_max(scalar) == 2
    assert max_tree_max(scalar3) == 3
    assert max_tree_max(tree) == 2
    assert max_tree_max(low_tree) == 1

    assert max_of_max_trees(scalar, tree) == 2
    assert max_of_max_trees(tree, scalar3) == 3
    assert max_of_max_trees(scalar, abc_tree) == MaxTree(
        cell=0, choices={"b": 7, "c": 3}, default=2
    )
    assert max_of_max_trees(low_tree, tree) == tree
    assert max_of_max_trees(tree, abc_tree) == MaxTree(
        cell=0, choices={"a": 1, "b": 7, "c": 3}
    )
    assert max_of_max_trees(scalar3, scalar) == 3


def test_max_tree_with_default():
    scalar = 2
    tree_with_default = MaxTree(cell=0, choices={"a": 3, "b": 4}, default=2)
    tree_ac = MaxTree(cell=0, choices={"a": 4, "c": 3})

    assert add_max_trees(scalar, tree_ac) == MaxTree(
        cell=0, choices={"a": 6, "c": 5}, default=2
    )
    assert add_max_trees(scalar, tree_with_default) == MaxTree(
        cell=0, choices={"a": 5, "b": 6}, default=4
    )
    assert add_max_trees(tree_ac, tree_with_default) == MaxTree(
        cell=0, choices={"a": 7, "b": 4, "c": 5}, default=2
    )


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
    assert 3 == bb.UpperBound(BIGINT, -1)
    assert 3 == bb.Details().sum_union
    assert 3 == bb.Details().max_nomark
    assert 2 == bb.NumReps()

    # A force on an irrelevant cell has no effect
    assert 3 == bb.UpperBound(BIGINT, 0)

    # A force on the choice cell reduces the bound.
    assert 2 == bb.UpperBound(BIGINT, 3)
