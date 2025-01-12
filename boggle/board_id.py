import argparse

from tqdm import tqdm


def from_board_id(classes: list[str], dims: tuple[int, int], idx: int) -> str:
    w, h = dims
    num_classes = len(classes)
    board: list[str] = []
    left = idx
    for i in range(0, w * h):
        board.append(classes[left % num_classes])
        left //= num_classes
    assert left == 0
    return " ".join(board)


# TODO: maybe should be i // h to match C++
def board_id(bd: list[list[int]], dims: tuple[int, int], num_classes: int) -> int:
    w, h = dims
    id = 0
    for i in range(w * h - 1, -1, -1):
        id *= num_classes
        id += bd[i // w][i % w]
    return id


def swap(ary, a, b):
    ax, ay = a
    bx, by = b
    ary[ay][ax], ary[by][bx] = ary[by][bx], ary[ay][ax]


# TODO: can probably express this all more concisely in Python
def is_canonical_board_id(num_classes: int, dims: tuple[int, int], idx: int):
    w, h = dims
    if idx < 0:
        return False
    bd = [[0 for _x in range(0, w)] for _y in range(0, h)]
    left = idx
    for i in range(0, w * h):
        bd[i // w][i % w] = left % num_classes
        left //= num_classes
    assert left == 0

    rots = (0, 1) if w == h else (0,)

    for rot in rots:
        # ABC    CBA
        # DEF -> FED
        # GHI    IHG
        for i in range(0, h):
            swap(bd, (0, i), (w - 1, i))
        if board_id(bd, dims, num_classes) < idx:
            return False

        # CBA    IHG
        # FED -> FED
        # IHG    CBA
        for i in range(0, w):
            swap(bd, (i, 0), (i, h - 1))
        if board_id(bd, dims, num_classes) < idx:
            return False

        # IHG    GHI
        # FED -> DEF
        # CBA    ABC
        for i in range(0, h):
            swap(bd, (0, i), (w - 1, i))
        if board_id(bd, dims, num_classes) < idx:
            return False

        if rot == rots[-1]:
            break

        # GHI    ABC    ADG
        # DEF -> DEF -> BEH
        # ABC    GHI    CFI
        for i in range(0, w):
            swap(bd, (i, 0), (i, h - 1))
        for i in range(0, w):
            for j in range(0, i):
                swap(bd, (i, j), (j, i))

        if board_id(bd, dims, num_classes) < idx:
            return False

    return True


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
        choices=(33, 34, 44),
        default=33,
        help="Size of the boggle board.",
    )
    parser.add_argument("boards", nargs="+", help="Board classes (space-delimited)")

    args = parser.parse_args()
    classes = args.classes.split(" ")
    num_classes = len(classes)
    w, h = dims = args.size // 10, args.size % 10
    assert 3 <= w <= 4
    assert 3 <= h <= 4
    max_index = num_classes ** (w * h)

    boards: set[str] = set(args.boards)
    numeric_boards = {board for board in boards if board.isdigit()}
    boards -= numeric_boards

    if numeric_boards:
        for i in numeric_boards:
            board = from_board_id(classes, dims, int(i))
            print(f"{i}: {board}")

    if not boards:
        return

    print(f"Searching for {boards}")

    # This is horribly inefficient -- it should be possible to derive the ID directly
    # from the letter classes. But maybe this is fine if we don't need to do this often.
    for i in tqdm(range(max_index)):
        # TODO: add flag to allow searching non-canonical boards (slower)
        if not is_canonical_board_id(num_classes, dims, i):
            continue
        board = from_board_id(classes, dims, i)
        if board not in boards:
            continue

        print(f"{i}: {board}")


if __name__ == "__main__":
    main()
