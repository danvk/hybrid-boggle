from collections import Counter
from typing import Self, Sequence

from boggle.arena import PyArena
from boggle.board_class_boggler import BoardClassBoggler

ROOT_NODE = -2


class SumNode:
    letter: int
    """Which choice of letter on the cell does this represent? (0-based).

    For the root node of a tree, this may be set to ROOT_NODE.
    """

    points: int
    """Points provided by _this_ node, not children."""

    bound: int
    """Upper bound on the number of points available in this subtree."""

    children: list["ChoiceNode"]
    """The children to sum, sorted by child.cell."""

    def __init__(self):
        self.children = []
        self.points = 0

    def add_word(
        self,
        choices: Sequence[tuple[int, int]],
        points: int,
        arena: PyArena,
        cell_counts: list[int] = None,
    ):
        if not choices:
            self.points += points
            self.bound += points
            return

        (cell, letter) = choices[0]
        remaining_choices = choices[1:]

        choice_child = None
        for c in self.children:
            if c.cell == cell:
                choice_child = c
                break
        old_choice_bound = 0
        if not choice_child:
            choice_child = ChoiceNode()
            choice_child.cell = cell
            choice_child.bound = 0
            self.children.append(choice_child)
            if cell_counts:
                cell_counts[cell] += 1
            if arena:
                arena.add_node(choice_child)
            self.children.sort(key=lambda c: c.cell)
        else:
            old_choice_bound = choice_child.bound

        letter_child = None
        for c in choice_child.children:
            if c.letter == letter:
                letter_child = c
                break
        if not letter_child:
            letter_child = SumNode()
            letter_child.letter = letter
            letter_child.bound = 0
            choice_child.children.append(letter_child)
            choice_child.children.sort(key=lambda c: c.letter)
            if arena:
                arena.add_node(letter_child)

        letter_child.add_word(remaining_choices, points, arena, cell_counts)
        if letter_child.bound > old_choice_bound:
            choice_child.bound = letter_child.bound
        self.bound += choice_child.bound - old_choice_bound

    def score_with_forces(self, forces: list[int]) -> int:
        """Evaluate a tree with some choices forced. Use -1 to not force a choice."""
        return self.points + sum(
            child.score_with_forces(forces) if child else 0 for child in self.children
        )

    def orderly_force_cell(
        self, cell: int, num_lets: int, arena: PyArena
    ) -> list[Self] | Self:
        raise NotImplementedError()

    def node_count(self):
        return 1 + sum(child.node_count() for child in self.children if child)

    def orderly_bound(
        self,
        cutoff: int,
        cells: list[str],
        split_order: Sequence[int],
        preset_cells: Sequence[tuple[int, int]],
    ):
        """Find individual high-scoring boards in this tree without creating new nodes.

        See https://www.danvk.org/2025/04/10/following-insight.html#orderly-bound
        """
        num_letters = [len(cell) for cell in cells]
        stacks: list[list[ChoiceNode]] = [[] for _ in num_letters]
        choices = []  # for tracking unbreakable boards
        failures: list[str] = []
        # max_lens: list[int] = [0] * len(stacks)
        n_preset = len(preset_cells)
        elim_at_level = [0] * (1 + len(cells) - n_preset)
        visit_at_level = [0] * (1 + len(cells) - n_preset)

        num_visits = Counter[Self]()

        def advance(node: Self, sums: list[int]):
            num_visits[node] += 1
            for child in node.children:
                stacks[child.cell].append(child)
                sums[child.cell] += child.bound
            return node.points

        def record_failure(bound: int):
            bd = [None] * len(num_letters)
            for cell, letter in preset_cells:
                bd[cell] = cells[cell][letter]
            for cell, letter in choices:
                bd[cell] = cells[cell][letter]
            board = "".join(bd)
            nonlocal failures
            failures.append((bound, board))

        def rec(base_points: int, num_splits: int, stack_sums: list[int]):
            bound = base_points + sum(
                stack_sums[cell] for cell in split_order[num_splits:]
            )
            if bound <= cutoff:
                elim_at_level[num_splits] += 1
                return  # done!
            if num_splits == len(split_order):
                record_failure(bound)
                return

            # need to advance; try each possibility in turn.
            next_to_split = split_order[num_splits]
            stack_top = [len(stack) for stack in stacks]
            base_sums = [*stack_sums]
            for letter in range(0, num_letters[next_to_split]):
                if letter > 0:
                    for i, v in enumerate(base_sums):
                        stack_sums[i] = v
                    for i, length in enumerate(stack_top):
                        stacks[i] = stacks[i][:length]
                choices.append((next_to_split, letter))
                points = base_points
                for node in stacks[next_to_split]:
                    letter_node = None
                    for n in node.children:
                        if n.letter == letter:
                            letter_node = n
                            break
                    if letter_node:
                        visit_at_level[1 + num_splits] += 1
                        points += advance(letter_node, stack_sums)

                rec(points, num_splits + 1, stack_sums)
                # reset the stacks
                choices.pop()

        sums = [0] * len(num_letters)
        visit_at_level[0] += 1
        base_points = advance(self, sums)
        rec(base_points, 0, sums)
        self.num_visits = num_visits  # for visualizing backtracking behavior
        return failures, visit_at_level, elim_at_level

    # --- Methods below here are only for testing / debugging and may not have C++ equivalents. ---

    def get_children(self):
        return self.children

    def set_computed_fields(self, num_letters: Sequence[int]):
        for c in self.children:
            if c:
                c.set_computed_fields(num_letters)
        self.bound = self.points + sum(c.bound for c in self.children if c)

    def assert_orderly(self, split_order: Sequence[int], max_index=None):
        """Ensure that the tree is "orderly" in the following sense:

        If a choice for cell i is a descendant of a choice for cell j, then
        it must be that index(split_order, i) > index(split_order, j).
        """
        # sum node children must be sorted by cell (not split_order)
        for a, b in zip(self.children, self.children[1:]):
            assert a.cell < b.cell
        for child in self.children:
            if child:
                child.assert_orderly(split_order, max_index)

    def assert_invariants(self, solver):
        """Ensure the tree is well-formed. Some desirable properties:

        - node.bound is correct (checked shallowly)
        - choice node children are mutually-exclusive
        - choice node children are sorted
        - no duplicate choice children for sum nodes
        """
        bound = self.points
        seen_choices = set[int]()
        for child in self.children:
            assert child
            bound += child.bound
            assert child.cell not in seen_choices
            seen_choices.add(child.cell)
        assert bound == self.bound

        for child in self.children:
            if child:
                child.assert_invariants(solver)

    def to_string(self, cells: list[str]):
        return eval_node_to_string(self, cells)

    def to_json(self, solver: BoardClassBoggler | None, max_depth=100, lookup=None):
        raise NotImplementedError()


class ChoiceNode:
    cell: int
    """Which cell does this represent on the Boggle board?"""

    bound: int
    """Upper bound on the number of points available in this subtree."""

    children: list[SumNode]
    """For choice nodes: the choices, ordered by child.letter."""

    def __init__(self):
        self.children = []

    def score_with_forces(self, forces: list[int]) -> int:
        """Evaluate a tree with some choices forced. Use -1 to not force a choice."""
        force = forces[self.cell]
        if force >= 0:
            for child in self.children:
                if child and child.letter == force:
                    return child.score_with_forces(forces)
            return 0
        return (
            max(
                child.score_with_forces(forces) if child else 0
                for child in self.children
            )
            if self.children
            else 0
        )

    def orderly_force_cell(
        self, cell: int, num_lets: int, arena: PyArena
    ) -> list[Self] | Self:
        raise NotImplementedError()

    def node_count(self):
        return 1 + sum(child.node_count() for child in self.children if child)

    # --- Methods below here are only for testing / debugging and may not have C++ equivalents. ---

    def get_children(self):
        return self.children

    def set_computed_fields(self, num_letters: Sequence[int]):
        for c in self.children:
            if c:
                c.set_computed_fields(num_letters)
        self.bound = max(c.bound for c in self.children if c) if self.children else 0

    def assert_orderly(self, split_order: Sequence[int], max_index=None):
        idx = split_order.index(self.cell)
        if max_index is not None:
            assert idx > max_index
        max_index = idx
        for child in self.children:
            if child:
                child.assert_orderly(split_order, max_index)

    def assert_invariants(self, solver):
        # choice nodes _may_ have non-null children, but the rest must be sorted.
        nnc = [c for c in self.children if c]
        for a, b in zip(nnc, nnc[1:]):
            assert a.letter < b.letter
        if len(self.children) == len(solver.bd_[self.cell]) and all(
            c for c in self.children
        ):
            for i, c in enumerate(self.children):
                assert c.letter == i
        bound = 0
        for child in self.children:
            if child:
                bound = max(bound, child.bound)
        assert bound == self.bound

        for child in self.children:
            if child:
                child.assert_invariants(solver)

    def to_string(self, cells: list[str]):
        raise NotImplementedError()

    def to_json(self, solver: BoardClassBoggler | None, max_depth=100, lookup=None):
        raise NotImplementedError()


def _sum_to_list(
    node: SumNode, cells: list[str], lines: list[str], indent="", prev_cell=None
):
    line = ""
    if node.letter == ROOT_NODE:
        line = f"{indent}ROOT ({node.bound})"
    else:
        cell = cells[prev_cell][node.letter]
        line = f"{indent}{cell} ({prev_cell}={node.letter} {node.points}/{node.bound})"
    lines.append(line)
    for child in node.get_children():
        if child:
            _choice_to_list(child, cells, lines, " " + indent)
        else:
            print("null!")


def _choice_to_list(node: ChoiceNode, cells: list[str], lines: list[str], indent=""):
    line = f"{indent}CHOICE ({node.cell} <{node.bound}) points=0"
    lines.append(line)
    for child in node.get_children():
        if child:
            _sum_to_list(child, cells, lines, " " + indent, prev_cell=node.cell)
        else:
            print("null!")


def eval_node_to_string(node: SumNode, cells: list[str], top_cell=None):
    # This is defined externally so that it works with both C++ and Python implementations.
    lines = []
    _sum_to_list(node, cells, lines, indent="", prev_cell=top_cell)
    return "\n".join(lines)
