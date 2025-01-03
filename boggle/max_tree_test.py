from boggle.max_tree import (
    MaxTree,
    add_max_trees,
    max_of_max_trees,
    max_tree_max,
)


def test_max_tree_ops_no_default():
    scalar = 2
    scalar3 = 3
    tree = MaxTree(cell=0, choices={"a": 1, "b": 2})
    low_tree = MaxTree(cell=0, choices={"a": 1, "b": 1})
    abc_tree = MaxTree(cell=0, choices={"a": 1, "b": 7, "c": 3})

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
        cell=0,
        choices={"b": 7, "c": 3},
        default=2,  # absorbs "a"
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

    assert max_tree_max(tree_with_default) == 4
    assert max_tree_max(tree_ac) == 4

    assert max_of_max_trees(scalar, tree_with_default) == tree_with_default
    assert max_of_max_trees(scalar, tree_ac) == MaxTree(
        cell=0, choices={"a": 4, "c": 3}, default=2
    )
    assert max_of_max_trees(tree_with_default, tree_ac) == MaxTree(
        cell=0, choices={"a": 4, "b": 4, "c": 3}, default=2
    )

    tree_with_high_default = MaxTree(cell=0, choices={"d": 11}, default=10)
    assert max_of_max_trees(scalar, tree_with_high_default) == tree_with_high_default
    assert (
        max_of_max_trees(tree_with_default, tree_with_high_default)
        == tree_with_high_default
    )
    assert max_of_max_trees(tree_ac, tree_with_high_default) == tree_with_high_default
