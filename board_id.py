
def from_board_id(classes: list[str], dims: tuple[int, int], idx: int) -> str:
    w, h = dims
    num_classes = len(classes)
    board: list[str] = []
    left = idx
    for i in range(0, w*h):
        board.append(classes[left % num_classes])
        left //= num_classes
    assert left == 0
    return ' '.join(board)


def board_id(bd: list[list[int]], dims: tuple[int, int], num_classes: int) -> int:
    w, h = dims
    id = 0
    for i in range(w*h-1, -1, -1):
        id *= num_classes
        id += bd[i//w][i%w]
    return id


def swap(ary, a, b):
    ax, ay = a
    bx, by = b
    ary[ax][ay], ary[bx][by] = ary[bx][by], ary[ax][ay]


# TODO: can probably express this all more concisely in Python
def is_canonical_board_id(num_classes: int, dims: tuple[int, int], idx: int):
    w, h = dims
    if idx < 0:
        return False
    bd = [[0 for _x in range(0, w)] for _y in range(0, h)]
    left = idx
    for i in range(0, w*h):
        bd[i//w][i%w] = left % num_classes
        left //= num_classes
    assert left == 0

    for rot in (0, 1):
        print(f'{rot=}')
        # ABC    CBA
        # DEF -> FED
        # GHI    IHG
        for i in range(0, h):
            swap(bd, (0, i), (w-1, i))
        if board_id(bd, dims, num_classes) < idx:
            print(bd)
            return False

        # CBA    IHG
        # FED -> FED
        # IHG    CBA
        for i in range(0, h):
            swap(bd, (i, 0), (i, h-1))
        if board_id(bd, dims, num_classes) < idx:
            print(bd)
            return False

        # IHG    GHI
        # FED -> DEF
        # CBA    ABC
        for i in range(0, h):
            swap(bd, (0, i), (w-1, i))
        if board_id(bd, dims, num_classes) < idx:
            print(bd)
            return False

        if rot == 1:
            break

        # GHI    ABC    ADG
        # DEF -> DEF -> BEH
        # ABC    GHI    CFI
        for i in range(0, w):
            swap(bd, (i, 0), (i, h-1))
        for i in range(0, w):
            for j in range(0, i):
                swap(bd, (i, j), (j, i))

        if board_id(bd, dims, num_classes) < idx:
            print(bd)
            return False

    return True
