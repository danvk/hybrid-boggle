import itertools
from dataclasses import dataclass


@dataclass
class MaxTree:
    cell: int
    choices: dict[str, int]
    """Invariants:
    1. len(choices) > 0
    2. all(c > default for c in choices.values())
    """
    default: int = 0
    """Value for cells that aren't explicitly listed in choices."""


type TreeOrScalar = int | MaxTree


def add_max_trees(a: TreeOrScalar, b: TreeOrScalar) -> TreeOrScalar:
    if type(a) is int:
        if type(b) is int:
            return a + b
        return MaxTree(
            cell=b.cell,
            choices={k: a + v for k, v in b.choices.items()},
            default=a + b.default,
        )
    else:
        if type(b) is int:
            return add_max_trees(b, a)
        assert a.cell == b.cell
        ac = a.choices
        ad = a.default
        bc = b.choices
        bd = b.default
        return MaxTree(
            cell=a.cell,
            choices={
                k: ac.get(k, ad) + bc.get(k, bd)
                for k in set(itertools.chain(ac.keys(), bc.keys()))
            },
            default=ad + bd,
        )


def max_of_max_trees(a: TreeOrScalar, b: TreeOrScalar) -> TreeOrScalar:
    if type(a) is int:
        if type(b) is int:
            return max(a, b)
        if a >= max_tree_max(b):
            return a
        # There's a new default, so we can filter any entries that are lower.
        # This can never be empty thanks to the max_tree_max check.
        md = max(a, b.default)
        mt = MaxTree(
            cell=b.cell,
            choices={k: m for k, v in b.choices.items() if (m := max(a, v)) > md},
            default=md,
        )
        assert mt.choices
        return mt
    else:
        if type(b) is int:
            return max_of_max_trees(b, a)
        assert a.cell == b.cell
        ac = a.choices
        ad = a.default
        bc = b.choices
        bd = b.default
        md = max(a.default, b.default)
        # This can't fully collapse.
        return MaxTree(
            cell=a.cell,
            choices={
                k: m
                for k in set(itertools.chain(ac.keys(), bc.keys()))
                if (m := max(ac.get(k, ad), bc.get(k, bd))) > md
            },
            default=md,
        )


def max_tree_max(t: TreeOrScalar) -> int:
    if type(t) is int:
        return t
    return max(t.choices.values())
