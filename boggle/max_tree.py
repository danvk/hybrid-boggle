from collections import Counter
from dataclasses import dataclass

import numpy as np


@dataclass
class MaxTree:
    cells: list[int]
    data: np.array  # could be scalar!


# TODO: try using 9-, 12- or 16-D numpy arrays with lots of empty dimensions.
#       this would eliminate any need to rearrange axes.


def pair_str(a: int, b: int):
    if a < b:
        return f"{a}-{b}"
    return f"{b}-{a}"


class MaxTreeUniverse:
    choices: list[str]  # cell index -> possible letters at that cell
    counts: Counter[str]

    def __init__(self, choices: list[str], max_depth: int):
        self.choices = choices
        self.max_depth = max_depth
        self.zero = self.scalar(0)
        self.counts = Counter()

    def reset_counts(self):
        self.counts = Counter()

    def from_ints(self, cell: int, scores: dict[str, int]) -> MaxTree:
        self.counts["from_ints"] += 1
        letters = self.choices[cell]
        m = MaxTree(cells=[cell], data=np.ndarray(len(letters), dtype=np.int32))
        for letter, score in scores.items():
            m.data[letters.index(letter)] = score
        return m

    def from_choices(self, cell: int, choices: dict[str, MaxTree]) -> MaxTree:
        self.counts["from_choices"] += 1
        # If we have room, add the cell as another dimension.
        subtrees = [*choices.values()]
        all_children = {
            c for child in subtrees for c in ([] if type(child) is int else child.cells)
        }
        assert cell not in all_children
        if len(all_children) < self.max_depth:
            self.counts["from_choices: safe"] += 1
            # add the new choice as the first dimension to a new array
            # TODO: this could be done in a loop with many fewer intermediates
            cells = [*all_children]
            zero = MaxTree(
                cells=cells,
                data=np.zeros(
                    tuple(len(self.choices[i]) for i in cells), dtype=np.int32
                ),
            )
            letters = self.choices[cell]
            all_cells = [cell] + cells
            data = np.zeros(
                tuple(len(self.choices[i]) for i in all_cells), dtype=np.int32
            )
            for c, subtree in choices.items():
                idx = letters.index(c)
                # this gets the subtree in the canonical order and adds missing columns
                idx_slice = self.add(zero, subtree)
                data[idx] = idx_slice.data
            return MaxTree(cells=all_cells, data=data)

        # Have to forget something! Choose the least-common.
        # TODO: choose the lowest-information instead? This will be arbitrary with one choice.
        freqs = Counter(
            c for child in subtrees for c in ([] if type(child) is int else child.cells)
        )
        _freq, forget_cell = min((v, k) for k, v in freqs.items())
        self.counts["from_choices: forget"] += 1
        return self.from_choices(
            cell,
            {
                c: self.forget(subtree, forget_cell)
                if type(subtree) is not int and forget_cell in subtree.cells
                else subtree
                for c, subtree in choices.items()
            },
        )

    def scalar(self, value: int) -> MaxTree:
        # return MaxTree(cells=[], data=np.array(value, dtype=np.int32))
        return value

    def add_scalar(self, m: MaxTree | int, val: int) -> MaxTree | int:
        if type(m) is int:
            return m + val
        return MaxTree(cells=m.cells, data=m.data + val)

    def max_scalar(self, m: MaxTree | int, val: int) -> MaxTree | int:
        if type(m) is int:
            return max(m, val)
        return MaxTree(cells=m.cells, data=np.maximum(m.data, val))

    def add(self, a: MaxTree, b: MaxTree) -> MaxTree | int:
        if type(b) is int:
            self.counts["add: scalar"] += 1
            return self.add_scalar(a, b)
        elif type(a) is int:
            self.counts["add: scalar"] += 1
            return self.add_scalar(b, a)
        self.counts["add: tree"] += 1
        self.counts["add: " + pair_str(self.depth(a), self.depth(b))] += 1
        out = self.aligned_op(a, b, np.add)
        assert isinstance(out, (MaxTree, int))
        return out

    def max(self, a: MaxTree | int, b: MaxTree | int) -> MaxTree | int:
        if type(b) is int:
            self.counts["max: scalar"] += 1
            return self.max_scalar(a, b)
        elif type(a) is int:
            self.counts["max: scalar"] += 1
            return self.max_scalar(b, a)
        self.counts["max: tree"] += 1
        self.counts["max: " + pair_str(self.depth(a), self.depth(b))] += 1
        out = self.aligned_op(a, b, np.maximum)
        assert isinstance(out, (MaxTree, int))
        return out

    def aligned_op(self, a: MaxTree, b: MaxTree, op) -> MaxTree:
        # Scalars
        if a.cells and not b.cells:
            # b is a scalar; let numpy broadcast it
            return MaxTree(cells=a.cells, data=op(a.data, b.data))
        elif b.cells and not a.cells:
            return self.aligned_op(b, a, op)

        # Same cells in the same order
        if a.cells == b.cells:
            self.counts["aligned_op: match"] += 1
            return MaxTree(cells=a.cells, data=op(a.data, b.data))

        # There's some sort of misalignment
        acells = set(a.cells)
        bcells = set(b.cells)

        # If the arrays are small enough, we can broadcast.
        # Otherwise we need to forget something.
        all_cells = acells | bcells
        if len(all_cells) <= self.max_depth:
            self.counts["aligned_op: safe"] += 1
            new_a_cells = [cell for cell in b.cells if cell not in acells]
            new_b_cells = [cell for cell in a.cells if cell not in bcells]
            expanded_a_cells = a.cells + new_a_cells
            expanded_b_cells = b.cells + new_b_cells
            new_a_shape = tuple(list(a.data.shape) + [1 for _ in new_a_cells])
            new_b_shape = tuple(list(b.data.shape) + [1 for _ in new_b_cells])
            expanded_a_data = a.data.reshape(new_a_shape)
            expanded_b_data = b.data.reshape(new_b_shape)
            aligned_b_data = expanded_b_data.transpose(
                [expanded_b_cells.index(i) for i in expanded_a_cells]
            )
            return MaxTree(
                cells=expanded_a_cells, data=op(expanded_a_data, aligned_b_data)
            )

        # Must forget something!
        if len(a.cells) < len(b.cells):
            a, b = b, a
            acells, bcells = bcells, acells
        # a is bigger -- forget one of its cells outside the overlap and try again
        # TODO: the choice here is probably very important!
        a_not_b = [cell for cell in a.cells if cell not in bcells]
        forget_cell = a_not_b[-1]
        self.counts["aligned_op: forget"] += 1
        return self.aligned_op(self.forget(a, forget_cell), b, op)

    def value(self, a: MaxTree, choices: dict[int, str]) -> int:
        if type(a) is int:
            return a
        idxs = []
        for cell in a.cells:
            c = choices.get(cell)
            if c is None:
                idxs.append(slice(None))
            else:
                idxs.append(self.choices[cell].index(c))
        view = a.data[tuple(idxs)]
        return int(view.max())

    def max_value(self, a: MaxTree) -> int:
        return self.value(a, {})

    def forget(self, a: MaxTree, cell: int) -> MaxTree | int:
        if type(a) is int:
            return a
        # TODO: special-case forgetting the only dimension -> scalar?
        idx = a.cells.index(cell)
        return MaxTree(cells=[v for v in a.cells if v != cell], data=a.data.max(idx))

    def depth(self, m: MaxTree | int) -> int:
        if type(m) is int:
            return 0
        return m.data.ndim

    def to_dict(self, m: MaxTree):
        if type(m) is int:
            return {frozenset({}): m}
        letters = [self.choices[i] for i in m.cells]
        it = np.nditer(m.data, flags=["multi_index"])
        out = {}
        for score in it:
            out[
                frozenset(
                    (m.cells[i], letters[i][j]) for i, j in enumerate(it.multi_index)
                )
            ] = int(score)
        return out

    def print(self, m: MaxTree):
        for choices, score in self.to_dict(m).items():
            print(
                ", ".join(f"{cell}={score}" for (cell, score) in choices),
                score,
            )
