from typing import Callable, Sequence


def group_by[T, R](seq: Sequence[T], fn: Callable[[T], R]) -> dict[R, list[T]]:
    out = dict[R, list[T]]()
    for v in seq:
        k = fn(v)
        out.setdefault(k, [])
        out[k].append(v)
    return out


def partition[T](seq: Sequence[T], fn: Callable[[T], bool]) -> tuple[list[T], list[T]]:
    trues = []
    falses = []
    for x in seq:
        if fn(x):
            trues.append(x)
        else:
            falses.append(x)
    return falses, trues
