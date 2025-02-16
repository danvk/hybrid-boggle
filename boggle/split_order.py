"""Order in which to split cells. Middle then edges then corners."""

import json

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

SPLIT_ORDER = {
    (2, 2): (0, 1, 2, 3),
    (3, 3): SPLIT_ORDER_33,
    (3, 4): SPLIT_ORDER_34,
    (4, 4): SPLIT_ORDER_44,
}


def main():
    for (w, h), split_order in SPLIT_ORDER.items():
        print(
            f"""template<>
const int BucketBoggler<{w}, {h}>::SPLIT_ORDER[{w}*{h}] = {{%s}};
"""
            % ", ".join(str(x) for x in split_order)
        )


if __name__ == "__main__":
    main()
