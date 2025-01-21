from cpp_boggle import (
    Boggler33,
    Boggler34,
    Boggler44,
    BucketBoggler33,
    BucketBoggler34,
    BucketBoggler44,
    TreeBuilder33,
    TreeBuilder34,
    TreeBuilder44,
)

from boggle.ibuckets import PyBucketBoggler22

Bogglers = {(3, 3): Boggler33, (3, 4): Boggler34, (4, 4): Boggler44}

BucketBogglers = {
    (2, 2): PyBucketBoggler22,
    (3, 3): BucketBoggler33,
    (3, 4): BucketBoggler34,
    (4, 4): BucketBoggler44,
}

TreeBuilders = {
    (3, 3): TreeBuilder33,
    (3, 4): TreeBuilder34,
    (4, 4): TreeBuilder44,
}


# Matches PyBoggler constructor
def cpp_boggler(t, dims):
    return Bogglers[dims](t)
