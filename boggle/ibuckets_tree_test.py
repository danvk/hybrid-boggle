from boggle.ibuckets_tree import MaxTree, add_max_trees


def test_max_tree_ops():
    scalar = 2
    scalar3 = 3
    tree = MaxTree(cell=0, choices={"a": 1, "b": 2})
    low_tree = MaxTree(cell=0, choices={"a": 1, "b": 1})

    assert add_max_trees(scalar, tree) == MaxTree(cell=0, choices={"a": 3, "b": 4})
    assert add_max_trees(low_tree, tree) == MaxTree(cell=0, choices={"a": 2, "b": 3})
    assert add_max_trees(low_tree, scalar) == MaxTree(cell=0, choices={"a": 3, "b": 3})
    assert add_max_trees(scalar3, scalar) == 5
