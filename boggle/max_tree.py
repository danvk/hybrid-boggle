import itertools
from dataclasses import dataclass


@dataclass
class MaxTree:
    cell: int
    choices: dict[str, int]


type TreeOrScalar = int | MaxTree


def add_max_trees(a: TreeOrScalar, b: TreeOrScalar) -> TreeOrScalar:
    if type(a) is int:
        if type(b) is int:
            return a + b
        return MaxTree(
            cell=b.cell,
            choices={k: a + v for k, v in b.choices.items()},
        )
    else:
        if type(b) is int:
            return add_max_trees(b, a)
        assert a.cell == b.cell
        ac = a.choices
        bc = b.choices
        return MaxTree(
            cell=a.cell,
            choices={k: av + bc[k] for k, av in ac.items()},
        )


def max_of_max_trees(a: TreeOrScalar, b: TreeOrScalar) -> TreeOrScalar:
    if type(a) is int:
        if type(b) is int:
            return max(a, b)
        if a >= max_tree_max(b):
            return a
        mt = MaxTree(
            cell=b.cell,
            choices={k: max(a, v) for k, v in b.choices.items()},
        )
        assert mt.choices
        return mt
    else:
        if type(b) is int:
            return max_of_max_trees(b, a)
        assert a.cell == b.cell
        ac = a.choices
        bc = b.choices
        # This can't fully collapse.
        return MaxTree(
            cell=a.cell,
            choices={k: max(av, bc[k]) for k, av in ac.items()},
        )


def max_tree_max(t: TreeOrScalar) -> int:
    if type(t) is int:
        return t
    return max(t.choices.values())
