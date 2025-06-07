def init_neighbors(w: int, h: int):
    def idx(x: int, y: int):
        return h * x + y

    def pos(idx: int):
        return (idx // h, idx % h)

    ns: list[list[int]] = []
    for i in range(0, w * h):
        x, y = pos(i)
        n = []
        for dx in range(-1, 2):
            nx = x + dx
            if nx < 0 or nx >= w:
                continue
            for dy in range(-1, 2):
                ny = y + dy
                if ny < 0 or ny >= h:
                    continue
                if dx == 0 and dy == 0:
                    continue
                n.append(idx(nx, ny))
        n.sort()
        ns.append(n)
    return ns


NEIGHBORS22 = init_neighbors(2, 2)
NEIGHBORS23 = init_neighbors(2, 3)
NEIGHBORS33 = init_neighbors(3, 3)
NEIGHBORS34 = init_neighbors(3, 4)
NEIGHBORS44 = init_neighbors(4, 4)
NEIGHBORS45 = init_neighbors(4, 5)
NEIGHBORS55 = init_neighbors(5, 5)

NEIGHBORS = {
    (2, 2): NEIGHBORS22,
    (2, 3): NEIGHBORS23,
    (3, 3): NEIGHBORS33,
    (3, 4): NEIGHBORS34,
    (4, 4): NEIGHBORS44,
    (4, 5): NEIGHBORS45,
    (5, 5): NEIGHBORS55,
}
