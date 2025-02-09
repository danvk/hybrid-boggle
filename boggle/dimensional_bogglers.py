from cpp_boggle import (
    Boggler33,
    Boggler34,
    Boggler44,
    Boggler55,
    BucketBoggler33,
    BucketBoggler34,
    BucketBoggler44,
    TreeBuilder33,
    TreeBuilder34,
    TreeBuilder44,
)

from boggle.ibuckets import PyBucketBoggler22, PyBucketBoggler23

Bogglers = {(3, 3): Boggler33, (3, 4): Boggler34, (4, 4): Boggler44, (5, 5): Boggler55}

BucketBogglers = {
    (2, 2): PyBucketBoggler22,
    (2, 3): PyBucketBoggler23,
    (3, 3): BucketBoggler33,
    (3, 4): BucketBoggler34,
    (4, 4): BucketBoggler44,
}

TreeBuilders = {
    # (2, 2): TreeBuilder22,
    (3, 3): TreeBuilder33,
    (3, 4): TreeBuilder34,
    (4, 4): TreeBuilder44,
}


# Matches PyBoggler constructor
def cpp_boggler(t, dims):
    return Bogglers[dims](t)


# Matches EvalTreeBoggler
def cpp_tree_builder(t, dims):
    return TreeBuilders[dims](t)
