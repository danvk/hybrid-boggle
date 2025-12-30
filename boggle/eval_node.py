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

    word_ids: set[int]
    """Set of word IDs that end at this node."""

    bound: int
    """Upper bound on the number of points available in this subtree."""

    children: dict[int, "ChoiceNode"]
    """The children to sum, sorted by child.cell."""

    def __init__(self):
        self.children = {}
        self.points = 0
        self.word_ids = set()
        self.bound = 0

    def orderly_force_cell(
        self, cell: int, num_lets: int, arena: PyArena
    ) -> list[Self]:
        """Return trees for each possible choice for cell."""
        # See https://www.danvk.org/2025/04/10/following-insight.html#lift--orderly-force--merge
        if not self.children:
            return [self] * num_lets
        top_choice = self.children.get(cell)

        if top_choice is None:
            return [self] * num_lets  # See comment in C++

        non_cell_children = {k: v for k, v in self.children.items() if k != cell}
        non_cell_points = self.points
        non_cell_word_ids = self.word_ids

        out = [None] * num_lets
        # Iterate only over set bits in the bitmask
        remaining_bits = top_choice.child_letters
        while remaining_bits:
            letter = countr_zero(remaining_bits)
            if letter < num_lets:
                child = top_choice.get_child_for_letter(letter)
                if child:
                    # Subtract the forced path (child) from the unforced paths (non_cell_children)
                    # to prevent double-counting words.
                    purified_children = {
                        k: subtract_sum_from_choice(v, child, arena)
                        for k, v in non_cell_children.items()
                    }
                    out[letter] = merge_orderly_tree_children(
                        child,
                        purified_children,
                        non_cell_points,
                        non_cell_word_ids,
                        arena,
                    )
            remaining_bits &= remaining_bits - 1  # Clear the lowest set bit

        if top_choice.child_letters.bit_count() < num_lets:
            # TODO: if there's >1 of these, this could result in a lot of duplicate work.
            other_bound = sum(c.bound for c in non_cell_children.values())
            if other_bound > 0 or non_cell_points > 0:
                for i, child in enumerate(out):
                    if not child:
                        point_node = SumNode()
                        point_node.points = non_cell_points
                        point_node.word_ids = non_cell_word_ids.copy()
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
            for cell, child in node.children.items():
                stacks[cell].append(child)
                sums[cell] += child.bound
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
        return self.children.values()

    def node_count(self):
        return 1 + sum(child.node_count() for child in self.children.values() if child)

    def word_count(self):
        return (1 if self.points else 0) + sum(
            child.word_count() for child in self.children.values()
        )

    def score_with_forces(self, forces: list[int]) -> int:
        """Evaluate a tree with some choices forced. Use -1 to not force a choice."""
        return self.points + sum(
            child.score_with_forces(cell, forces) if child else 0
            for cell, child in self.children.items()
        )

    def assert_orderly(self, split_order: Sequence[int], max_index=None):
        """Ensure that the tree is "orderly" in the following sense:

        If a choice for cell i is a descendant of a choice for cell j, then
        it must be that index(split_order, i) > index(split_order, j).
        """
        # sum node children must be sorted by cell (not split_order)
        children = sorted(self.children.items())
        for (cell_a, _), (cell_b, _) in zip(children, children[1:]):
            assert cell_a < cell_b, f"{cell_a} not < {cell_b}"
        for cell, child in self.children.items():
            assert child is not None
            child.assert_orderly(cell, split_order, max_index)

    def assert_invariants(self, solver):
        """Ensure the tree is well-formed. Some desirable properties:

        - node.bound is correct (checked shallowly)
        - choice node children are mutually-exclusive
        - choice node children are sorted
        - no duplicate choice children for sum nodes
        """
        bound = self.points
        for child in self.children.values():
            assert child is not None
            bound += child.bound
        assert bound == self.bound, f"{bound} != {self.bound}"

        for cell, child in self.children.items():
            assert child is not None
            child.assert_invariants(cell, solver)

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
            out["children"] = [
                c.to_json(cell, max_depth - 1)
                for cell, c in sorted(self.children.items())
                if c
            ]
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

    def set_bounds_for_testing(self):
        for c in self.children.values():
            c.set_bounds_for_testing()
        self.bound = self.points + sum(c.bound for c in self.children.values())


class ChoiceNode:
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

    def get_labeled_children(self):
        remaining_bits = self.child_letters
        while remaining_bits:
            letter = countr_zero(remaining_bits)
            child = self.get_child_for_letter(letter)
            yield (letter, child)

    def set_bounds_for_testing(self):
        for c in self.children:
            c.set_bounds_for_testing()
        if self.children:
            self.bound = max(c.bound for c in self.children)
        else:
            self.bound = 0

    def score_with_forces(self, cell: int, forces: list[int]) -> int:
        """Evaluate a tree with some choices forced. Use -1 to not force a choice."""
        force = forces[cell]
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

    def assert_orderly(self, cell: int, split_order: Sequence[int], max_index=None):
        idx = split_order.index(cell)
        if max_index is not None:
            assert idx > max_index
        max_index = idx
        for child in self.children:
            if child:
                child.assert_orderly(split_order, max_index)

    def assert_invariants(self, cell: int, solver):
        # Verify bitmask consistency
        expected_count = self.child_letters.bit_count()
        assert len(self.children) == expected_count
        bound = 0
        for child in self.children:
            assert child is not None
            bound = max(bound, child.bound)
        assert bound == self.bound

        for child in self.children:
            assert child is not None
            child.assert_invariants(solver)

    def to_string(self, cells: list[str]):
        # Call this on SumNode instead.
        raise NotImplementedError()

    def to_json(self, cell: int, max_depth=100):
        out = {
            "type": "CHOICE",
            "cell": cell,
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
        cell_char = cells[prev_cell][prev_letter]
        line = f"{indent}{cell_char} ({prev_cell}={prev_letter} {node.points}/{node.bound})"
    lines.append(line)
    for cell, child in sorted(node.children.items()):
        if child:
            _choice_to_list(child, cell, cells, lines, " " + indent)
        else:
            print("null!")


def _choice_to_list(
    node: ChoiceNode, cell: int, cells: list[str], lines: list[str], indent=""
):
    if node.bound == 0:
        return
    line = f"{indent}CHOICE ({cell} <{node.bound})"
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
                        prev_cell=cell,
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
    children = sorted(tree.children.items())
    top_cell, top_choice = children[0]

    n = SumNode()
    arena.add_node(n)
    n.children = dict(children[1:])
    n.points = tree.points
    n.bound = n.points + sum(child.bound for child in n.children.values() if child)
    return top_choice, n


def merge_orderly_tree(a: SumNode, b: SumNode, arena: PyArena) -> SumNode:
    """Merge two orderly(N) trees."""
    return merge_orderly_tree_children(a, b.children, b.points, b.word_ids, arena)


def merge_orderly_tree_children(
    a: SumNode,
    bc: dict[int, ChoiceNode],
    b_points: int,
    b_word_ids: set[int],
    arena: PyArena,
) -> SumNode:
    in_a = a
    ac = a.children

    out = {}
    all_keys = sorted(list(ac.keys() | bc.keys()))

    for cell in all_keys:
        in_a_cell = cell in ac
        in_b_cell = cell in bc
        if in_a_cell and in_b_cell:
            out[cell] = merge_orderly_choice_children(ac[cell], bc[cell], cell, arena)
        elif in_a_cell:
            out[cell] = ac[cell]
        elif in_b_cell:
            out[cell] = bc[cell]

    n = SumNode()
    n.children = out
    n.points = in_a.points + b_points
    n.word_ids = in_a.word_ids | b_word_ids
    n.bound = n.points + sum(child.bound for child in n.children.values())
    arena.add_node(n)
    return n


def merge_orderly_choice_children(
    a: ChoiceNode, b: ChoiceNode, cell: int, arena: PyArena
) -> ChoiceNode:
    """Merge two orderly choice nodes for the same cell."""
    # Compute the union of child letters from both nodes
    merged_letters = a.child_letters | b.child_letters

    n = ChoiceNode()
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


def subtract_tree(a: SumNode, b: SumNode, arena: PyArena) -> SumNode:
    """Subtract tree b from tree a (a - b).

    Removes any word IDs present in b from a.
    If a node becomes empty (no points, no children), it might remain as a ghost
    (bound 0) which is fine.
    """
    new_word_ids = a.word_ids - b.word_ids
    new_points = a.points
    # We can't easily recalculate points from word_ids without the dictionary,
    # but in our specific case, if we remove all word_ids, points should be 0.
    # If we remove some, points should decrease.
    # However, since we don't have a map from ID to points here, we assume
    # that if word_ids match, the points match.
    # If a.word_ids is not empty and b.word_ids contains all of them, points -> 0.
    # For partial overlap, it's tricky. But in "deduping", we expect full overlap
    # for specific words.
    # Simplified logic: if we remove IDs, we should ideally adjust points.
    # BUT, SumNode.points is just an integer.
    # Constraint: we only support this if we assume each ID contributes points?
    # Or simply: if we remove an ID, we remove its points.
    # Problem: we don't know how many points an ID is worth without the word length or lookups.
    # Workaround:
    # If a.word_ids is subset of b.word_ids, points = 0.
    # If disjoint, points = a.points.
    # If partial... we might be stuck.
    # BUT for the deduping case, we usually see full word matches.
    if not new_word_ids:
        new_points = 0
    elif new_word_ids == a.word_ids:
        new_points = a.points
    else:
        # Partial overlap.
        # If b's IDs were fully present in a, we can safely subtract b's points.
        if b.word_ids.issubset(a.word_ids):
            new_points = max(0, a.points - b.points)
        else:
            # If b has IDs not in a, but we removed some shared IDs...
            # This implies a structure mismatch or different word IDs ending at same node.
            # We'll conservatively keep a's points to avoid undercounting,
            # unless we can be smarter.
            # In orderly trees, if paths match, word sets should be consistent.
            new_points = a.points

    # If nothing changes in points or IDs, and children don't change, return a.
    # But checking deep equality is slow. So we always create a new node if there's overlap.

    # Check intersection of children
    common_cells = set(a.children.keys()) & set(b.children.keys())

    new_children = {}
    children_changed = False

    for cell, child_a in a.children.items():
        if cell in common_cells:
            child_b = b.children[cell]
            new_child = subtract_choice(child_a, child_b, arena)
            new_children[cell] = new_child
            if new_child is not child_a:
                children_changed = True
        else:
            new_children[cell] = child_a

    if not children_changed and new_word_ids == a.word_ids:
        return a

    n = SumNode()
    n.points = new_points
    n.word_ids = new_word_ids
    n.children = new_children
    n.bound = n.points + sum(child.bound for child in n.children.values())
    arena.add_node(n)
    return n


def subtract_choice(a: ChoiceNode, b: ChoiceNode, arena: PyArena) -> ChoiceNode:
    # Iterate over common letters
    common_mask = a.child_letters & b.child_letters

    if common_mask == 0:
        return a

    new_children = []
    children_changed = False

    # Iterate through a's children
    a_children = a.get_children()
    # We need to map index back to letter to find b's child
    child_idx = 0

    for letter in range(32):
        if a.child_letters & (1 << letter):
            child_a = a_children[child_idx]
            if b.child_letters & (1 << letter):
                child_b = b.get_child_for_letter(letter)
                new_child = subtract_tree(child_a, child_b, arena)
                new_children.append(new_child)
                if new_child is not child_a:
                    children_changed = True
            else:
                new_children.append(child_a)
            child_idx += 1

    if not children_changed:
        return a

    n = ChoiceNode()
    n.child_letters = a.child_letters
    n.children = new_children
    n.bound = max(c.bound for c in n.children) if n.children else 0
    arena.add_node(n)
    return n


def subtract_sum_from_choice(
    choice: ChoiceNode, sub: SumNode, arena: PyArena
) -> ChoiceNode:
    """Subtract SumNode 'sub' from each branch of ChoiceNode 'choice'."""
    new_children = []
    children_changed = False

    # Iterate through choice's children
    choice_children = choice.get_children()
    child_idx = 0

    # We must construct a new ChoiceNode with the same letters, but potentially modified children.
    # The letters mask stays the same (unless a child becomes empty/null? No, we keep empty children usually)
    # Actually, if a child becomes empty/bound 0, we can keep it.

    for letter in range(32):
        if choice.child_letters & (1 << letter):
            child_sum = choice_children[child_idx]
            # Recursively subtract sub from the child SumNode.
            # Why? Because 'sub' represents the path starting *after* the forced cell.
            # 'child_sum' represents the path starting *after* the choice cell + letter.
            # If the paths align structurally, we subtract.
            # NOTE: We assume sub and child_sum start at the same 'logical' position in the word path?
            # Yes, because in Orderly Tree, the path is sorted by cell index.
            # Main (sub) starts after forced cell 0. So it contains cells > 0.
            # Others (choice) starts at cell 1. Children start after cell 1.
            # So both contain cells > 1.
            # So they line up.

            # Wait. Main contains cell 1?
            # If force 0. Main has cells {1, 2, ...}.
            # Others starts at 1. Child of 1 has cells {2, ...}.
            # So Main {1, 2} vs Child {2}.
            # They do NOT line up immediately?
            # Main has ChoiceNode for 1. Child has ChoiceNode for 2.
            # SubtractTree(Child, Main) would check:
            # Child.children keys vs Main.children keys.
            # Child has key 2. Main has key 1 (and maybe 2).
            # Common keys? Only 2?
            # If Main has 1, Child does NOT have 1 (it's past 1).
            # So SubtractTree ignores 1.
            # It compares Child(2) vs Main(2).
            # This is exactly what we want!
            # It finds the intersection.

            new_child = subtract_tree(child_sum, sub, arena)
            new_children.append(new_child)
            if new_child is not child_sum:
                children_changed = True
            child_idx += 1

    if not children_changed:
        return choice

    n = ChoiceNode()
    n.child_letters = choice.child_letters
    n.children = new_children
    n.bound = max(c.bound for c in n.children) if n.children else 0
    arena.add_node(n)
    return n
