from cpp_boggle import (
    Boggler23,
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

from boggle.boggler import PyBoggler
from boggle.ibuckets import PyBucketBoggler22, PyBucketBoggler23

Bogglers = {(2, 3): Boggler23, (3, 3): Boggler33, (3, 4): Boggler34, (4, 4): Boggler44}

BucketBogglers = {
    (2, 2): PyBucketBoggler22,
    (2, 3): PyBucketBoggler23,
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
    if dims == (2, 2):
        return PyBoggler(t, dims)
    return Bogglers[dims](t)
