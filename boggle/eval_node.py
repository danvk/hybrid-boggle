import itertools
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
    ) -> list[Self]:
        if not self.children:
            return [self]
        top_choice = None
        top_choice_idx = None
        for i, child in enumerate(self.children):
            if child.cell == cell:
                top_choice_idx = i
                top_choice = child
                break

        if top_choice is None:
            return [self]

        non_cell_children = [*self.children]
        non_cell_children.pop(top_choice_idx)
        non_cell_points = self.points

        out = [None] * num_lets
        for child in top_choice.children:
            out[child.letter] = merge_orderly_tree_children(
                child, non_cell_children, non_cell_points, arena
            )

        if len(top_choice.children) < num_lets:
            # TODO: if there's >1 of these, this could result in a lot of duplicate work.
            other_bound = sum(c.bound for c in non_cell_children)
            if other_bound > 0 or non_cell_points > 0:
                for i, child in enumerate(out):
                    if not child:
                        point_node = SumNode()
                        point_node.points = non_cell_points
                        point_node.letter = i
                        point_node.bound = point_node.points + other_bound
                        point_node.children = non_cell_children
                        arena.add_node(point_node)
                        out[i] = point_node
        return out

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
        # Call this on SumNode instead.
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


def eval_all(node: SumNode, cells: list[str]):
    """Evaluate all possible boards.

    This is defined externally to SumNode so that it can be used with C++ nodes, too.
    """
    num_letters = [len(cell) for cell in cells]
    indices = [range(n) for n in num_letters]
    return {
        choices: node.score_with_forces(choices)
        for choices in itertools.product(*indices)
    }


# TODO: delete this function, it's only used in one test
def split_orderly_tree(tree: SumNode, arena: PyArena):
    """Split an orderly(N) into the choice for N and an orderly(N-1) tree.

    Points on the input tree are put on the output tree.
    """
    top_choice = tree.children[0]

    children = tree.children[1:]
    n = SumNode()
    arena.add_node(n)
    n.letter = tree.letter
    n.children = children
    n.points = tree.points
    n.bound = n.points + sum(child.bound for child in children if child)
    return top_choice, n


def merge_orderly_tree(a: SumNode, b: SumNode, arena: PyArena) -> SumNode:
    """Merge two orderly(N) trees."""
    return merge_orderly_tree_children(a, b.children, b.points, arena)


def merge_orderly_tree_children(
    a: SumNode, bc: Sequence[ChoiceNode], b_points: int, arena: PyArena
) -> SumNode:
    # TODO: it may be safe to merge bc in-place into a and avoid an allocation.
    #       might need to be careful with the out.append(b) case, though.
    in_a = a

    i_a = 0
    i_b = 0
    ac = a.children
    a_n = len(ac)
    b_n = len(bc)
    out = []
    while i_a < a_n and i_b < b_n:
        a = ac[i_a]
        if not a:
            i_a += 1
            continue
        b = bc[i_b]
        if not b:
            i_b += 1
            continue
        if a.cell < b.cell:
            out.append(a)
            i_a += 1
        elif b.cell < a.cell:
            out.append(b)
            i_b += 1
        else:
            out.append(merge_orderly_choice_children(a, b, arena))
            i_a += 1
            i_b += 1

    while i_a < a_n:
        a = ac[i_a]
        if a:
            out.append(a)
        i_a += 1

    while i_b < b_n:
        b = bc[i_b]
        if b:
            out.append(b)
        i_b += 1

    n = SumNode()
    n.letter = in_a.letter
    n.children = out
    n.points = in_a.points + b_points
    n.bound = n.points + sum(child.bound for child in n.children)
    arena.add_node(n)
    return n


def merge_orderly_choice_children(
    a: ChoiceNode, b: ChoiceNode, arena: PyArena
) -> ChoiceNode:
    """Merge two orderly choice nodes for the same cell."""
    in_a = a
    assert a.cell == b.cell
    i_a = 0
    i_b = 0
    ac = a.children
    bc = b.children
    a_n = len(ac)
    b_n = len(bc)

    out = []
    while i_a < a_n and i_b < b_n:
        a = ac[i_a]
        if not a:
            i_a += 1
            continue
        b = bc[i_b]
        if not b:
            i_b += 1
            continue
        if a.letter < b.letter:
            out.append(a)
            i_a += 1
        elif b.letter < a.letter:
            out.append(b)
            i_b += 1
        else:
            out.append(merge_orderly_tree(a, b, arena))
            i_a += 1
            i_b += 1

    while i_a < a_n:
        a = ac[i_a]
        if a:
            out.append(a)
        i_a += 1

    while i_b < b_n:
        b = bc[i_b]
        if b:
            out.append(b)
        i_b += 1

    n = ChoiceNode()
    n.cell = in_a.cell
    n.children = out
    n.points = 0
    n.bound = max(child.bound for child in n.children)
    arena.add_node(n)
    return n
