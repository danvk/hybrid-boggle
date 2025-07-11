import argparse
from typing import Sequence


def from_board_id(cell_classes: list[list[str]], idx: int) -> str:
    board: list[str] = []
    left = idx
    # print("from_board_id")
    for classes in cell_classes:
        # print(left % num_classes)
        board.append(classes[left % len(classes)])
        left //= len(classes)
    assert left == 0
    return " ".join(board)


def board_id(bd: list[list[int]], num_classes: list[int]) -> int:
    h = len(bd)
    w = len(bd[0])
    id = 0
    for i in range(w * h - 1, -1, -1):
        id *= num_classes[i]
        id += bd[i % h][i // h]
    return id


def to_2d[T](bd1d: Sequence[T], dims: tuple[int, int]) -> list[list[T]]:
    w, h = dims
    bd = [[0 for _x in range(0, w)] for _y in range(0, h)]
    assert len(bd1d) == w * h
    for i, v in enumerate(bd1d):
        bd[i % h][i // h] = v
    return bd


def to_1d[T](bd2d: Sequence[Sequence[T]]) -> list[T]:
    out = []
    w = len(bd2d[0])
    h = len(bd2d)
    for i in range(w * h):
        out.append(bd2d[i % h][i // h])
    return out


def swap(ary, a, b):
    ax, ay = a
    bx, by = b
    ary[ay][ax], ary[by][bx] = ary[by][bx], ary[ay][ax]


# TODO: can probably express this all more concisely in Python
def canonicalize_id(num_classes: list[int], dims: tuple[int, int], idx: int):
    """Return an index for a more canonical version of this board.

    Returns the original board ID if there is no such index.
    This might not return the _most_ canonical version. Call repeatedly for that.
    """
    w, h = dims
    assert idx >= 0
    bd = [[0 for _x in range(0, w)] for _y in range(0, h)]
    left = idx

    # dims=(3, 4): bd is 4x3; len(bd) == 4, len(bd[0]) == 3
    for i in range(0, w * h):
        bd[i % h][i // h] = left % num_classes[i]
        left //= num_classes[i]
    assert left == 0

    rots = (0, 1) if w == h else (0,)

    for rot in rots:
        # ABC    CBA
        # DEF -> FED
        # GHI    IHG
        for j in range(0, w // 2):
            for i in range(0, h):
                swap(bd, (j, i), (w - 1 - j, i))
        other = board_id(bd, num_classes)
        if other < idx:
            return other

        # CBA    IHG
        # FED -> FED
        # IHG    CBA
        for j in range(0, h // 2):
            for i in range(0, w):
                swap(bd, (i, j), (i, h - 1 - j))
        other = board_id(bd, num_classes)
        if other < idx:
            return other

        # IHG    GHI
        # FED -> DEF
        # CBA    ABC
        for j in range(0, w // 2):
            for i in range(0, h):
                swap(bd, (j, i), (w - 1 - j, i))
        other = board_id(bd, num_classes)
        if other < idx:
            return other

        if rot == rots[-1]:
            break

        # GHI    ABC    ADG
        # DEF -> DEF -> BEH
        # ABC    GHI    CFI
        for j in range(0, h // 2):
            for i in range(0, w):
                swap(bd, (i, j), (i, h - 1 - j))
        for i in range(0, w):
            for j in range(0, i):
                swap(bd, (i, j), (j, i))

        other = board_id(bd, num_classes)
        if other < idx:
            return other

    return idx


def get_canonical_board_id(num_classes: list[int], dims: tuple[int, int], idx: int):
    other = canonicalize_id(num_classes, dims, idx)
    if other == idx:
        return idx
    return get_canonical_board_id(num_classes, dims, other)


def is_canonical_board_id(num_classes: list[int], dims: tuple[int, int], idx: int):
    r = canonicalize_id(num_classes, dims, idx)
    return r == idx


CELL_TYPES = {"center", "edge", "corner"}


def cell_type_for_index(idx: int, dims: tuple[int, int]):
    w, h = dims
    y = idx % h
    x = idx // h
    ex = x == 0 or x == w - 1
    ey = y == 0 or y == h - 1
    if ex and ey:
        return "corner"
    elif ex or ey:
        return "edge"
    return "center"


def parse_classes(classes: str, dims: tuple[int, int]):
    w, h = dims
    clauses = [clause.strip() for clause in classes.split(",")]
    cell_types = {}
    for clause in clauses:
        if ":" in clause:
            where, what = (c.strip() for c in clause.split(":"))
            assert where in CELL_TYPES
            cell_types[where] = what.split(" ")
        else:
            for type in CELL_TYPES:
                cell_types[type] = clause.split(" ")

    return [cell_types[cell_type_for_index(i, dims)] for i in range(w * h)]


def main():
    parser = argparse.ArgumentParser(
        description="Go between board IDs and board classes",
    )
    parser.add_argument(
        "classes", type=str, help="Space-separated list of letter classes"
    )
    parser.add_argument(
        "--size",
        type=int,
        choices=(33, 34, 44, 45, 55),
        default=33,
        help="Size of the boggle board.",
    )
    parser.add_argument("boards", nargs="+", help="Board classes (space-delimited)")

    args = parser.parse_args()
    w, h = dims = args.size // 10, args.size % 10
    assert 3 <= w <= 5
    assert 3 <= h <= 5
    classes = parse_classes(args.classes, dims)
    assert len(classes) == w * h
    num_classes = [len(c) for c in classes]

    boards: set[str] = set(args.boards)
    numeric_boards = {board for board in boards if board.isdigit()}
    boards -= numeric_boards

    if numeric_boards:
        for i in numeric_boards:
            board = from_board_id(classes, int(i))
            print(f"{i}: {board}")

    if not boards:
        return

    # expand individual boards to their classes
    expanded_boards = set()
    for board in boards:
        if " " in board:
            expanded_boards.add(board)
            continue
        board_class = " ".join(
            next(c for c in classes[i] if b in c) for i, b in enumerate(board)
        )
        print(f"Expanding {board} -> {board_class}")
        expanded_boards.add(board_class)
    boards = expanded_boards

    for board in boards:
        bd_1d = board.split(" ")
        nums = [classes[i].index(c) for i, c in enumerate(bd_1d)]
        bd = to_2d(nums, dims)
        bd_id = board_id(bd, num_classes)
        canon = (
            "canonical"
            if is_canonical_board_id(num_classes, dims, bd_id)
            else f"canonical -> {get_canonical_board_id(num_classes, dims, bd_id)}"
        )

        print(f"{bd_id}\t{board}\t{canon}")


if __name__ == "__main__":
    main()
