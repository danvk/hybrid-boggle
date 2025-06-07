from cpp_boggle import (
    Boggler22,
    Boggler23,
    Boggler33,
    Boggler34,
    Boggler44,
    Boggler45,
    Boggler55,
    BucketBoggler22,
    BucketBoggler23,
    BucketBoggler33,
    BucketBoggler34,
    BucketBoggler44,
    BucketBoggler45,
    BucketBoggler55,
    OrderlyTreeBuilder22,
    OrderlyTreeBuilder23,
    OrderlyTreeBuilder33,
    OrderlyTreeBuilder34,
    OrderlyTreeBuilder44,
    OrderlyTreeBuilder45,
    OrderlyTreeBuilder55,
)

Bogglers = {
    (2, 2): Boggler22,
    (2, 3): Boggler23,
    (3, 3): Boggler33,
    (3, 4): Boggler34,
    (4, 4): Boggler44,
    (4, 5): Boggler45,
    (5, 5): Boggler55,
}

BucketBogglers = {
    (2, 2): BucketBoggler22,
    (2, 3): BucketBoggler23,
    (3, 3): BucketBoggler33,
    (3, 4): BucketBoggler34,
    (4, 4): BucketBoggler44,
    (4, 5): BucketBoggler45,
    (5, 5): BucketBoggler55,
}

OrderlyTreeBuilders = {
    (2, 2): OrderlyTreeBuilder22,
    (2, 3): OrderlyTreeBuilder23,
    (3, 3): OrderlyTreeBuilder33,
    (3, 4): OrderlyTreeBuilder34,
    (4, 4): OrderlyTreeBuilder44,
    (4, 5): OrderlyTreeBuilder45,
    (5, 5): OrderlyTreeBuilder55,
}


# Matches PyBoggler constructor
def cpp_boggler(t, dims):
    return Bogglers[dims](t)


def cpp_bucket_boggler(t, dims):
    return BucketBogglers[dims](t)


def cpp_orderly_tree_builder(t, dims):
    return OrderlyTreeBuilders[dims](t)


LEN_TO_DIMS = {
    4: (2, 2),
    6: (2, 3),
    9: (3, 3),
    12: (3, 4),
    16: (4, 4),
    20: (4, 5),
    25: (5, 5),
}
