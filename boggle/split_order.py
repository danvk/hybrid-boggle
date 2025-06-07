"""Order in which to split cells. Middle then edges then corners."""

from typing import Sequence

SPLIT_ORDER_33 = (4, 5, 3, 1, 7, 0, 2, 6, 8)


def to_idx(x, y):
    return x * 4 + y


SPLIT_ORDER_34 = tuple(
    to_idx(x, y)
    for x, y in (
        (1, 1),
        (1, 2),  # middle
        (0, 1),
        (2, 1),
        (0, 2),
        (2, 2),  # middle sides
        (1, 0),
        (1, 3),  # top/bottom middle
        (0, 0),
        (2, 0),
        (0, 3),
        (2, 3),  # corners
    )
)
assert len(SPLIT_ORDER_34) == 12

SPLIT_ORDER_44 = tuple(
    to_idx(x, y)
    for x, y in (
        (1, 1),
        (1, 2),
        (2, 1),
        (2, 2),  # middle
        (0, 1),
        (3, 1),
        (0, 2),
        (3, 2),  # middle sides
        (1, 0),
        (1, 3),
        (2, 0),
        (2, 3),  # top/bottom middle
        (0, 0),
        (3, 0),
        (0, 3),
        (3, 3),  # corners
    )
)
assert len(SPLIT_ORDER_44) == 16
assert len(set(SPLIT_ORDER_44)) == 16


def to_idx5(x, y):
    return x * 5 + y


# c E E c
# E O O E
# X C C X
# E O O E
# c E E c

SPLIT_ORDER_45 = tuple(
    to_idx5(x, y)
    for x, y in (
        (1, 2),  # center (C)
        (2, 2),
        (1, 1),  # off-center (O)
        (2, 1),
        (1, 3),
        (2, 3),
        (0, 2),  # side-center (X)
        (3, 2),
        (1, 0),  # edges (E)
        (2, 0),
        (0, 1),
        (0, 3),
        (3, 1),
        (3, 3),
        (1, 4),
        (2, 4),
        (0, 0),  # corners (c)
        (3, 0),
        (0, 4),
        (3, 4),
    )
)
assert len(SPLIT_ORDER_45) == 20
assert len(set(SPLIT_ORDER_45)) == 20

SPLIT_ORDER_55 = tuple(
    to_idx5(x, y)
    for x, y in (
        (2, 2),  # super-center
        (1, 2),
        (2, 1),
        (3, 2),
        (2, 3),  # up/down from center
        (1, 1),
        (1, 3),
        (3, 1),
        (3, 3),  # diagonal from center
        (0, 2),
        (2, 0),
        (4, 2),
        (2, 4),  # center sides
        (1, 0),
        (3, 0),
        (0, 1),
        (0, 3),
        (1, 4),
        (3, 4),
        (4, 1),
        (4, 3),  # off-center sides
        (0, 0),
        (4, 0),
        (0, 4),
        (4, 4),  # corners
    )
)
assert len(SPLIT_ORDER_55) == 25
assert len(set(SPLIT_ORDER_55)) == 25


SPLIT_ORDER: dict[tuple[int, int], Sequence[int]] = {
    (2, 2): (0, 1, 2, 3),
    (2, 3): (0, 1, 2, 3, 4, 5),
    (3, 3): SPLIT_ORDER_33,
    (3, 4): SPLIT_ORDER_34,
    (4, 4): SPLIT_ORDER_44,
    (4, 5): SPLIT_ORDER_45,
    (5, 5): SPLIT_ORDER_55,
}
