from boggle.max_tree import (
    MaxTree,
    add_max_trees,
    get_value,
    max_of_max_trees,
    max_tree_max,
    pivot,
)


def test_max_tree_ops_no_default():
    scalar = 2
    scalar3 = 3
    tree = MaxTree(cell=0, choices={"a": 1, "b": 2, "c": 0})
    low_tree = MaxTree(cell=0, choices={"a": 1, "b": 1, "c": 0})
    abc_tree = MaxTree(cell=0, choices={"a": 1, "b": 7, "c": 3})

    assert add_max_trees(scalar, tree) == MaxTree(
        cell=0,
        choices={"a": 3, "b": 4, "c": 2},
    )
    assert add_max_trees(low_tree, tree) == MaxTree(
        cell=0, choices={"a": 2, "b": 3, "c": 0}
    )
    assert add_max_trees(low_tree, scalar) == MaxTree(
        cell=0,
        choices={"a": 3, "b": 3, "c": 2},
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
        choices={"a": 2, "b": 7, "c": 3},
    )
    assert max_of_max_trees(low_tree, tree) == tree
    assert max_of_max_trees(tree, abc_tree) == MaxTree(
        cell=0, choices={"a": 1, "b": 7, "c": 3}
    )
    assert max_of_max_trees(scalar3, scalar) == 3


def test_depth_two_tree():
    scalar = 2
    tree_cell1 = MaxTree(cell=1, choices={"c": 4, "d": 5})
    tree_cell0 = MaxTree(cell=0, choices={"a": 3, "b": 4, "c": tree_cell1})

    assert max_tree_max(tree_cell0) == 5

    assert get_value(tree_cell0, {0: "a"}) == 3
    assert get_value(tree_cell0, {0: "b"}) == 4
    assert get_value(tree_cell0, {0: "c"}) == 5  # max of tree_cell1
    assert get_value(tree_cell0, {0: "c", 1: "c"}) == 4
    assert get_value(tree_cell0, {0: "c", 1: "d"}) == 5

    pivoted = pivot(tree_cell0)
    assert get_value(pivoted, {0: "a"}) == 3
    assert get_value(pivoted, {0: "b"}) == 4
    assert get_value(pivoted, {0: "c"}) == 5  # max of tree_cell1
    assert get_value(pivoted, {0: "c", 1: "c"}) == 4
    assert get_value(pivoted, {0: "c", 1: "d"}) == 5

    back = pivot(pivoted)
    # print(back)
    assert back == tree_cell0

    sum_tree = add_max_trees(tree_cell0, pivoted)
    assert get_value(sum_tree, {0: "a"}) == 2 * 3
    assert get_value(sum_tree, {0: "b"}) == 2 * 4
    assert get_value(sum_tree, {0: "c"}) == 2 * 5  # max of tree_cell1
    assert get_value(sum_tree, {0: "c", 1: "c"}) == 2 * 4
    assert get_value(sum_tree, {0: "c", 1: "d"}) == 2 * 5

    mistree = add_max_trees(tree_cell0, tree_cell1)
    assert get_value(mistree, {0: "a"}) == 8
