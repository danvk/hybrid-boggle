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
            choices={k: add_max_trees(a, v) for k, v in b.choices.items()},
        )
    else:
        if type(b) is int:
            return add_max_trees(b, a)
        if a.cell == b.cell:
            ac = a.choices
            bc = b.choices
            # assert set(ac.keys()) == set(bc.keys())
            # It's unlikely that these all reduce to the same value
            return MaxTree(
                cell=a.cell,
                choices={k: add_max_trees(av, bc[k]) for k, av in ac.items()},
            )
        else:
            if a.cell > b.cell:
                a, b = b, a
            # TODO: prune. Could be faster, too!
            # TODO: cache a.choices[ac] lookup
            # TODO: collapse useless nodes
            return MaxTree(
                cell=a.cell,
                choices={
                    ac: MaxTree(
                        cell=b.cell,
                        choices={
                            bc: get_value(a, {a.cell: ac, b.cell: bc})
                            + get_value(b, {a.cell: ac, b.cell: bc})
                            for bc in b.choices.keys()
                        },
                    )
                    for ac in a.choices.keys()
                },
            )


def max_of_max_trees(a: TreeOrScalar, b: TreeOrScalar) -> TreeOrScalar:
    if type(a) is int:
        if type(b) is int:
            return max(a, b)
        if a >= max_tree_max(b):
            return a
        mt = MaxTree(
            cell=b.cell,
            choices={k: max_of_max_trees(a, v) for k, v in b.choices.items()},
        )
        return mt
    else:
        if type(b) is int:
            return max_of_max_trees(b, a)
        if a.cell == b.cell:
            ac = a.choices
            bc = b.choices
            # assert set(ac.keys()) == set(bc.keys())
            # It's unlikely that these all reduce to the same value
            return MaxTree(
                cell=a.cell,
                choices={k: max_of_max_trees(av, bc[k]) for k, av in ac.items()},
            )
        else:
            if a.cell > b.cell:
                a, b = b, a
            # TODO: prune. Could be faster, too!
            # TODO: cache a.choices[ac] lookup
            # TODO: collapse useless nodes
            return MaxTree(
                cell=a.cell,
                choices={
                    ac: MaxTree(
                        cell=b.cell,
                        choices={
                            bc: max(
                                get_value(a, {a.cell: ac, b.cell: bc}),
                                get_value(b, {a.cell: ac, b.cell: bc}),
                            )
                            for bc in b.choices.keys()
                        },
                    )
                    for ac in a.choices.keys()
                },
            )


def max_tree_max(t: TreeOrScalar) -> int:
    if type(t) is int:
        return t
    return max(max_tree_max(child) for child in t.choices.values())


def get_value(t: TreeOrScalar, choices: dict[int, str]) -> int:
    if type(t) is int:
        return t
    cell_choice = choices.get(t.cell)
    if cell_choice is not None:
        subtree = t.choices[cell_choice]
        return get_value(subtree, choices)
    # if we're unconstrained, take the max of all choices
    return max(get_value(t, choices) for t in t.choices.values())


def pivot(t: MaxTree) -> MaxTree:
    """Flip the order of a depth-two MaxTree."""
    cell1s = [
        *set(child.cell for child in t.choices.values() if isinstance(child, MaxTree))
    ]
    assert len(cell1s) == 1
    choice1s = set(
        cell1
        for child in t.choices.values()
        if isinstance(child, MaxTree)
        for cell1 in child.choices.keys()
    )

    # TODO: this could be more efficient
    cell1 = cell1s[0]
    tree = MaxTree(
        cell=cell1,
        choices={
            c1: MaxTree(
                cell=t.cell,
                choices={
                    c0: get_value(t, {t.cell: c0, cell1: c1}) for c0 in t.choices.keys()
                },
            )
            for c1 in choice1s
        },
    )

    # Collapse useless nodes. Unclear whether this is helpful in practice,
    # but it does give an invariant that pivot(pivot(X)) == X.
    for c1, child in tree.choices.items():
        vs = child.choices.values()
        minv = min(vs)
        if minv == max(vs):
            tree.choices[c1] = minv

    return tree


def print_tabular(t: MaxTree, prefix=""):
    if type(t) is int:
        print(f"{prefix}: {t}")
        return

    for choice in sorted(t.choices.keys()):
        child = t.choices[choice]
        add = f"{t.cell}={choice}"
        print_tabular(child, f"{prefix}, {add}" if prefix else add)
