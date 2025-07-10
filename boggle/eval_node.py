"""A tree representing the evaluation of a class of Boggle boards.

See https://www.danvk.org/2025/02/13/boggle2025.html#the-evaluation-tree

There are two types of nodes: sum and choice:

- Sum nodes sum points across their children. This models how you can move in any
  direction to extend a word, or start words from any cell on the board.
- Choice nodes reflect a choice that must be made, namely which letter to choose for
  a cell in the board class. To get a bound, we can take the max across any
  choice, but this is imprecise because the same choice can appear in many subtrees
  and our choices won't be synchronized across those subtrees.

The children of sum nodes are choice nodes, and vice versa.
The root of the tree is always a sum node.

You can use node.bound to get the current upper bound for any subtree.

To reduce the bound, you can "force" a choice on a cell to get a subtree
for each possibility for that cell. This has the effect of merging other
choices and reducing the bound.
"""

import itertools
from collections import Counter
from typing import Self, Sequence

from boggle.arena import PyArena


class SumNode:
    points: int
    """Points provided by _this_ node, not children."""

    bound: int
    """Upper bound on the number of points available in this subtree."""

    children: list["ChoiceNode"]
    """The children to sum, sorted by child.cell."""

    def __init__(self):
        self.children = []
        self.points = 0
        self.bound = 0

    def add_word(
        self,
        choices: Sequence[int],
        used_ordered: int,
        split_order: Sequence[int],
        arena: PyArena,
    ):
        """Add a word to this tree. choices is a list of (cell, letter index) tuples.

        Returns the SumNode corresponding to these choices (either new or existing).
        """
        if used_ordered == 0:
            return self

        # some choices values may uninitialized here, but we only access the ones that are
        # initialized based on the bitmap
        order_index = countr_zero(used_ordered)
        cell = split_order[order_index]
        letter = choices[order_index]

        # remove the cell from used_ordered
        used_ordered &= used_ordered - 1

        choice_child = None
        for c in self.children:
            if c.cell == cell:
                choice_child = c
                break
        if not choice_child:
            choice_child = ChoiceNode()
            choice_child.cell = cell
            self.children.append(choice_child)
            if arena:
                arena.add_node(choice_child)
            self.children.sort(key=lambda c: c.cell)

        letter_child = choice_child.get_child_for_letter(letter)
        if not letter_child:
            letter_child = SumNode()
            letter_child.bound = 0
            # Update the bitmask and insert child at correct position
            choice_child.child_letters |= 1 << letter
            # Find insertion index using popcount
            mask = (1 << letter) - 1
            insert_index = (choice_child.child_letters & mask).bit_count()
            choice_child.children.insert(insert_index, letter_child)
            if arena:
                arena.add_node(letter_child)

        return letter_child.add_word(choices, used_ordered, split_order, arena)

    def decode_points_and_bound(self, wordlists=None):
        """Decode bound and points as set by OrderlyTreeBuilder."""
        if isinstance(self.bound, set):
            count = len(self.bound)
            word_score = self.points
            self.points = count * word_score

        bound = self.points
        for child in self.children:
            child.decode_points_and_bound(wordlists)
            bound += child.bound
        self.bound = bound

    def orderly_force_cell(
        self, cell: int, num_lets: int, arena: PyArena
    ) -> list[Self]:
        """Return trees for each possible choice for cell."""
        # See https://www.danvk.org/2025/04/10/following-insight.html#lift--orderly-force--merge
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
            return [self] * num_lets  # See comment in C++

        non_cell_children = [*self.children]
        non_cell_children.pop(top_choice_idx)
        non_cell_points = self.points

        out = [None] * num_lets
        # Iterate only over set bits in the bitmask
        remaining_bits = top_choice.child_letters
        while remaining_bits:
            letter = countr_zero(remaining_bits)
            if letter < num_lets:
                child = top_choice.get_child_for_letter(letter)
                if child:
                    out[letter] = merge_orderly_tree_children(
                        child, non_cell_children, non_cell_points, arena
                    )
            remaining_bits &= remaining_bits - 1  # Clear the lowest set bit

        if top_choice.child_letters.bit_count() < num_lets:
            # TODO: if there's >1 of these, this could result in a lot of duplicate work.
            other_bound = sum(c.bound for c in non_cell_children)
            if other_bound > 0 or non_cell_points > 0:
                for i, child in enumerate(out):
                    if not child:
                        point_node = SumNode()
                        point_node.points = non_cell_points
                        point_node.bound = point_node.points + other_bound
                        point_node.children = non_cell_children
                        arena.add_node(point_node)
                        out[i] = point_node
        return out

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
            if bound < cutoff:
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
                    letter_node = node.get_child_for_letter(letter)
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
        # return failures, visit_at_level, elim_at_level
        return failures

    # --- Methods below here are only for testing / debugging and may not have C++ equivalents. ---

    def get_children(self):
        return self.children

    def node_count(self):
        return 1 + sum(child.node_count() for child in self.children if child)

    def word_count(self):
        return (1 if self.points else 0) + sum(
            child.word_count() for child in self.children
        )

    def score_with_forces(self, forces: list[int]) -> int:
        """Evaluate a tree with some choices forced. Use -1 to not force a choice."""
        return self.points + sum(
            child.score_with_forces(forces) if child else 0 for child in self.children
        )

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

    def to_json(self, max_depth=100):
        out = {
            "type": "SUM",
            "bound": self.bound,
        }
        if self.points:
            out["points"] = self.points
        if self.children:
            out["children"] = [c.to_json(max_depth - 1) for c in self.children if c]
        return out

    def add_word_with_points_for_testing(
        self,
        choices: Sequence[int],
        used_ordered: int,
        split_order: Sequence[int],
        points: int,
        arena: PyArena,
    ):
        word_node = self.add_word(choices, used_ordered, split_order, arena)
        word_node.points += points


class ChoiceNode:
    cell: int
    """Which cell does this represent on the Boggle board?"""

    bound: int
    """Upper bound on the number of points available in this subtree."""

    child_letters: int
    """Bitmask of which letters this node's children represent."""

    children: list[SumNode]
    """For choice nodes: the choices, ordered by letter index."""

    def __init__(self):
        self.children = []
        self.bound = 0
        self.child_letters = 0

    def num_children(self) -> int:
        """Return the number of children, calculated from the bitmask."""
        return self.child_letters.bit_count()

    def get_child_for_letter(self, letter: int) -> SumNode | None:
        """Find child SumNode for given letter using popcount on child_letters bitmask."""
        if not (self.child_letters & (1 << letter)):
            return None  # This letter is not present
        # Count number of set bits before this letter to find index
        mask = (1 << letter) - 1
        index = (self.child_letters & mask).bit_count()
        return self.children[index] if index < len(self.children) else None

    # --- Methods below here are only for testing / debugging and may not have C++ equivalents. ---

    def get_children(self):
        return self.children

    def node_count(self):
        return 1 + sum(child.node_count() for child in self.children if child)

    def word_count(self):
        return sum(child.word_count() for child in self.children)

    def score_with_forces(self, forces: list[int]) -> int:
        """Evaluate a tree with some choices forced. Use -1 to not force a choice."""
        force = forces[self.cell]
        if force >= 0:
            child = self.get_child_for_letter(force)
            if child:
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

    def decode_points_and_bound(self, wordlists=None):
        # See corresponding method on SumNode.
        bound = 0
        for child in self.children:
            child.decode_points_and_bound(wordlists)
            bound = max(bound, child.bound)
        self.bound = bound

    def assert_orderly(self, split_order: Sequence[int], max_index=None):
        idx = split_order.index(self.cell)
        if max_index is not None:
            assert idx > max_index
        max_index = idx
        for child in self.children:
            if child:
                child.assert_orderly(split_order, max_index)

    def assert_invariants(self, solver):
        # choice nodes _may_ have non-null children, but children are ordered by bitmask
        nnc = [c for c in self.children if c]
        # Verify bitmask consistency
        expected_count = self.child_letters.bit_count()
        assert len(nnc) == expected_count
        # Verify children are in order according to the bitmask
        child_index = 0
        for letter in range(32):
            if self.child_letters & (1 << letter):
                # This letter should have a corresponding child
                assert child_index < len(self.children)
                child_index += 1
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

    def to_json(self, max_depth=100):
        out = {
            "type": "CHOICE",
            "cell": self.cell,
            "bound": self.bound,
            "child_letters": self.child_letters,
        }
        if self.children:
            out["children"] = [c.to_json(max_depth - 1) for c in self.children if c]
        return out


def countr_zero(n: int):
    assert n != 0
    return (n & -n).bit_length() - 1


def _sum_to_list(
    node: SumNode,
    cells: list[str],
    lines: list[str],
    indent="",
    prev_cell=None,
    prev_letter=None,
):
    line = ""
    if prev_cell is None or prev_letter is None:
        line = f"{indent}ROOT ({node.bound})"
    else:
        cell = cells[prev_cell][prev_letter]
        line = f"{indent}{cell} ({prev_cell}={prev_letter} {node.points}/{node.bound})"
    lines.append(line)
    for child in node.get_children():
        if child:
            _choice_to_list(child, cells, lines, " " + indent)
        else:
            print("null!")


def _choice_to_list(node: ChoiceNode, cells: list[str], lines: list[str], indent=""):
    line = f"{indent}CHOICE ({node.cell} <{node.bound}) points=0"
    lines.append(line)
    # Iterate through children using the bitmask
    child_index = 0
    children = node.get_children()
    for letter in range(32):
        if node.child_letters & (1 << letter):
            if child_index < len(children):
                child = children[child_index]
                if child:
                    _sum_to_list(
                        child,
                        cells,
                        lines,
                        " " + indent,
                        prev_cell=node.cell,
                        prev_letter=letter,
                    )
                else:
                    print("null!")
                child_index += 1


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
    n.children = out
    n.points = in_a.points + b_points
    n.bound = n.points + sum(child.bound for child in n.children)
    arena.add_node(n)
    return n


def merge_orderly_choice_children(
    a: ChoiceNode, b: ChoiceNode, arena: PyArena
) -> ChoiceNode:
    """Merge two orderly choice nodes for the same cell."""
    assert a.cell == b.cell

    # Compute the union of child letters from both nodes
    merged_letters = a.child_letters | b.child_letters

    n = ChoiceNode()
    n.cell = a.cell
    n.child_letters = merged_letters
    n.bound = 0

    # Iterate only over set bits in the merged bitmask
    out = []
    remaining_bits = merged_letters
    while remaining_bits:
        letter = countr_zero(remaining_bits)
        a_child = a.get_child_for_letter(letter)
        b_child = b.get_child_for_letter(letter)

        result_child = None
        if a_child and b_child:
            result_child = merge_orderly_tree(a_child, b_child, arena)
        elif a_child:
            result_child = a_child
        elif b_child:
            result_child = b_child

        out.append(result_child)
        if result_child:
            n.bound = max(n.bound, result_child.bound)

        remaining_bits &= remaining_bits - 1  # Clear the lowest set bit

    n.children = out
    arena.add_node(n)
    return n
