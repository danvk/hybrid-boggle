"""A tree representing the evaluation of a class of Boggle boards.

See https://www.danvk.org/2025/02/13/boggle2025.html#the-evaluation-tree

There are two types of nodes: sum and choice:

- Sum nodes sum points across their children. This models how you can move in any direction
  to extend a word, or start words from any cell on the board.
- Choice nodes reflect a choice that must be made, namely which letter to choose for
  a cell in the board class. To get a bound, we can take the max across any
  choice, but this is imprecise because the same choice can appear in many subtrees and
  our choices won't be synchronized across those subtrees.

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

from cpp_boggle import ChoiceNode, SumNode

from boggle.arena import PyArena
from boggle.board_class_boggler import BoardClassBoggler
from boggle.trie import make_lookup_table

ROOT_NODE = -2
CHOICE_NODE = -1


cache_count = 1


class EvalNode:
    letter: int
    """For a sum node: which choice of letter on the cell does this represent? (0-based)
    This can also be set to CHOICE_NODE or ROOT_NODE
    """

    cell: int
    """Which cell does this represent on the Boggle board?"""

    bound: int
    """Upper bound on the number of points available in this subtree."""

    points: int
    """Points provided by _this_ node, not children. Only relevant for sum nodes."""

    children: list[Self | None]
    """For sum nodes: the children to sum, sorted by child.cell.
    For choice nodes: the choices, ordered by child.letter.

    null children are rare but they can occur.
    """

    def __init__(self):
        self.children = []
        self.points = 0

    def add_word(
        self,
        choices: Sequence[tuple[int, int]],
        points: int,
        arena,
        cell_counts: list[int] = None,
    ):
        """Add a word at the end of a sequence of choices to the tree."""
        assert self.letter != CHOICE_NODE
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
            choice_child = EvalNode()
            choice_child.letter = CHOICE_NODE
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
            letter_child = EvalNode()
            letter_child.cell = cell
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

    # TODO: move this to the "debug & test" block
    def score_with_forces(self, forces: list[int]) -> int:
        """Evaluate a tree with some choices forced. Use -1 to not force a choice."""
        if self.letter == CHOICE_NODE:
            force = forces[self.cell]
            if force >= 0:
                for child in self.children:
                    if child and child.letter == force:
                        return child.score_with_forces(forces)
                return 0

        # Otherwise, this is the same as regular scoring
        if self.letter == CHOICE_NODE:
            v = (
                max(
                    child.score_with_forces(forces) if child else 0
                    for child in self.children
                )
                if self.children
                else 0
            )
        else:
            v = self.points + sum(
                child.score_with_forces(forces) if child else 0
                for child in self.children
            )
        return v

    def orderly_force_cell(
        self, cell: int, num_lets: int, arena: PyArena
    ) -> list[Self] | Self:
        assert self.letter != CHOICE_NODE
        if not self.children:
            return self
        top_choice = None
        top_choice_idx = None
        for i, child in enumerate(self.children):
            if child.cell == cell:
                top_choice_idx = i
                top_choice = child
                break

        if top_choice is None:
            return self

        assert top_choice.letter == CHOICE_NODE

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
                        point_node = EvalNode()
                        point_node.points = non_cell_points
                        point_node.cell = cell
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
        num_letters = [len(cell) for cell in cells]
        stacks = [[] for _ in num_letters]
        choices = []  # for tracking unbreakable boards
        failures: list[str] = []
        # max_lens: list[int] = [0] * len(stacks)
        n_preset = len(preset_cells)
        elim_at_level = [0] * (1 + len(cells) - n_preset)
        visit_at_level = [0] * (1 + len(cells) - n_preset)

        num_visits = Counter[EvalNode]()

        def advance(node: Self, sums: list[int]):
            num_visits[node] += 1
            assert node.letter != CHOICE_NODE
            for child in node.children:
                assert child.letter == CHOICE_NODE
                stacks[child.cell].append(child)
                sums[child.cell] += child.bound
                # max_lens[child.cell] = max(max_lens[child.cell], len(stacks[child.cell]))
            return node.points

        def record_failure(bound: int):
            bd = [None] * len(num_letters)
            for cell, letter in preset_cells:
                bd[cell] = cells[cell][letter]
            for cell, letter in choices:
                bd[cell] = cells[cell][letter]
            board = "".join(bd)
            # indent = "  " * len(num_letters)
            # print(f"{indent}unbreakable board! {bound} {board} {choices=}")
            nonlocal failures
            failures.append((bound, board))

        def rec(base_points: int, num_splits: int, stack_sums: list[int]):
            bound = base_points + sum(
                stack_sums[cell] for cell in split_order[num_splits:]
            )
            # indent = "  " * num_splits
            # print(f"{indent}{num_splits=} {base_points=} {bound=}")
            if bound <= cutoff:
                elim_at_level[num_splits] += 1
                return  # done!
            if num_splits == len(split_order):
                record_failure(bound)
                return

            # need to advance; try each possibility in turn.
            next_to_split = split_order[num_splits]
            stack_top = [len(stack) for stack in stacks]
            # print(f"{indent}{stack_top=}")
            base_sums = [*stack_sums]
            for letter in range(0, num_letters[next_to_split]):
                # print(f"{indent}{next_to_split}={letter}")
                if letter > 0:
                    for i, v in enumerate(base_sums):
                        stack_sums[i] = v
                    # TODO: track a "top" of each stack and leave the rest as garbage
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
        # print(f"{max_lens=}")
        self.cache_value = num_visits
        return failures, visit_at_level, elim_at_level

    # --- Methods below here are only for testing / debugging and may not have C++ equivalents. ---

    def get_children(self):
        return self.children

    def set_computed_fields(self, num_letters: Sequence[int]):
        for c in self.children:
            if c:
                c.set_computed_fields(num_letters)

        if self.letter == CHOICE_NODE:
            self.bound = (
                max(c.bound for c in self.children if c) if self.children else 0
            )
        else:
            self.bound = self.points + sum(c.bound for c in self.children if c)

    def assert_orderly(self, split_order: Sequence[int], max_index=None):
        # If a choice for cell i is a descendant of a choice for cell j, then
        # it must be that index(split_order, i) > index(split_order, j).

        if self.letter == CHOICE_NODE:
            idx = split_order.index(self.cell)
            if max_index is not None:
                assert idx > max_index
            max_index = idx
        else:
            # every child of a sum node must be a choice node
            for child in self.children:
                assert child.letter == CHOICE_NODE
            # sum node children must be sorted by cell (not split_order)
            for a, b in zip(self.children, self.children[1:]):
                assert a.cell < b.cell

        for child in self.children:
            if child:
                child.assert_orderly(split_order, max_index)

    def assert_invariants(self, solver):
        """Ensure the tree is well-formed. Some desirable properties:

        - Choice nodes do not have points.
        - node.bound is correct (checked shallowly)
        - choice node children are mutually-exclusive
        - choice node children are sorted
        - no duplicate choice children for sum nodes
        """
        if self.letter == CHOICE_NODE:
            # choice nodes _may_ have non-null children, but the rest must be sorted.
            nnc = [c for c in self.children if c]
            for a, b in zip(nnc, nnc[1:]):
                assert a.letter < b.letter
            if len(self.children) == len(solver.bd_[self.cell]) and all(
                c for c in self.children
            ):
                for i, c in enumerate(self.children):
                    if c.letter != CHOICE_NODE:
                        assert c.letter == i
            bound = 0
            for child in self.children:
                if child:
                    bound = max(bound, child.bound)
        else:
            bound = self.points
            seen_choices = set[int]()
            for child in self.children:
                assert child
                bound += child.bound
                if child.letter == CHOICE_NODE:
                    assert child.cell not in seen_choices
                    seen_choices.add(child.cell)
        # if bound != self.bound:
        #     print(f"Warning {bound} != {self.bound}")
        #     self.flag = True
        assert bound == self.bound

        for child in self.children:
            if child:
                child.assert_invariants(solver)

    def to_string(self, cells: list[str]):
        return eval_node_to_string(self, cells)

    def to_dot(self, cells: list[str], max_depth=100, trie=None, node_data=None) -> str:
        lookup_table = make_lookup_table(trie) if trie else None
        _root_id, dot = self.to_dot_help(
            cells,
            "",
            {},
            self.letter == CHOICE_NODE,
            max_depth,
            lookup_table,
            node_data,
        )
        return f"""graph {{
    rankdir=LR;
    nodesep=0.1;
    node [shape="rect" penwidth="0" style="rounded" fontname="Comic Sans MS"];
    {dot}
}}
"""

    def to_dot_help(
        self,
        cells: list[str],
        prefix,
        cache,
        is_top_max,
        remaining_depth,
        lookup_table,
        node_data,
    ) -> tuple[str, str]:
        """Returns ID of this node plus DOT for its subtree."""
        is_dupe = False  # self in cache  # hasattr(self, "flag")
        me = prefix

        # if self.letter != CHOICE_NODE:
        #     is_dupe = any_choice_collisions(self.children)

        if node_data:
            label = str(node_data.get(self, "-"))
        else:
            label = f"{self.bound}"
        attrs = ""
        if is_dupe:
            attrs = 'color="red"'
        if self.letter == ROOT_NODE:
            me += "r"
            attrs += ' penwidth="1"'
        elif self.letter == CHOICE_NODE:
            me += f"_{self.cell}c"
            color = DOT_FILL_COLORS[self.cell]
            attrs += f' style="rounded, filled" fillcolor="{color}"'
        else:
            letter = cells[self.cell][self.letter]
            me += f"_{self.cell}{letter}"
            attrs += ' penwidth="1"'
            # label = f"{self.cell}={letter}"
            if self.points and self.bound != self.points:
                attrs += ' peripheries="2"'
            #     label += f" ({self.points})"
            #     if self.trie_node and lookup_table:
            #         word = lookup_table[self.trie_node]
            #         label += f"\\nword={word}"
        # label += f"\\nbound={self.bound}"
        cache[self] = me
        dot = [f'{me} [label="{label}"{attrs}];']

        if remaining_depth == 0:
            return me, dot[0]

        children = [
            child.to_dot_help(
                cells,
                f"{me}{i}",
                cache,
                is_top_max and child.letter == CHOICE_NODE,
                remaining_depth - 1,
                lookup_table,
                node_data,
            )
            for i, child in enumerate(self.children)
            if child
        ]
        # all_choices = len(children) == len(self.children) and all(
        #     c.letter == CHOICE_NODE for c in self.children
        # )

        # if self.letter != CHOICE_NODE and len(children) == 1 and not self.points:
        #     # A sum node with no points and only one child is just a placeholder.
        #     # Remove it from the graph to simplify the visualization.
        #     return children[0]

        # print(f"{is_top_max=}, {all_choices=}")
        for i, (child_id, _) in enumerate(children):
            attrs = ""
            if self.letter == CHOICE_NODE and len(children) < len(cells[self.cell]):
                # incomplete set of choices; label them for clarity.
                attrs = f' [label="{self.children[i].letter}"]'
            # if is_top_max and all_choices:
            #     letter = cells[self.cell][i]
            #     attrs = f' [label="{self.cell}={letter}"]'
            dot.append(f"{me} -- {child_id}{attrs};")
        for _, child_dot in children:
            dot.append(child_dot)
        return me, "\n".join(dot)

    def to_json(self, solver: BoardClassBoggler | None, max_depth=100, lookup=None):
        if not lookup and solver:
            lookup = make_lookup_table(solver.trie_)
        char = solver.bd_[self.cell][self.letter] if solver else "?"
        out = {
            "type": (
                "ROOT"
                if self.letter == ROOT_NODE
                else "CHOICE"
                if self.letter == CHOICE_NODE
                else f"{self.cell}={char} ({self.letter})"
            ),
            "cell": self.cell,
            "bound": self.bound,
        }
        if self.points:
            out["points"] = self.points
        if self.trie_node and lookup:
            out["word"] = lookup[self.trie_node]
        if self.children:
            # child_range = [child.bound for child in self.children]
            # child_range.sort()
            # out["child_bound_range"] = child_range
            # out["num_reps"] = num_possibilities(self.choice_letters())
            if max_depth == 0:
                out["children"] = self.node_count()
            else:
                out["children"] = [
                    child.to_json(solver, max_depth - 1, lookup) if child else None
                    for child in self.children
                ]
        return out


DOT_FILL_COLORS = [
    "LightSkyBlue",
    "PaleGreen",
    "LightSalmon",
    "Khaki",
    "Plum",
    "Thistle",
    "PeachPuff",
    "Lavender",
    "HoneyDew",
    "MintCream",
    "AliceBlue",
    "LemonChiffon",
    "MistyRose",
    "PapayaWhip",
    "BlanchedAlmond",
    "LightCyan",
]


def _into_list(node: EvalNode, cells: list[str], lines: list[str], indent=""):
    line = ""
    if node.letter == ROOT_NODE:
        line = f"{indent}ROOT ({node.bound})"
    elif node.letter == CHOICE_NODE:
        line = f"{indent}CHOICE ({node.cell} <{node.bound}) points={node.points}"
    else:
        cell = cells[node.cell][node.letter]
        line = f"{indent}{cell} ({node.cell}={node.letter} {node.points}/{node.bound})"
    lines.append(line)
    for child in node.get_children():
        if child:
            _into_list(child, cells, lines, " " + indent)
        else:
            print("null!")
        # There are some slight discrepancies between C++ and Python trees that
        # are functionally irrelevant but surfaced if you uncomment this:
        # else:
        #     lines.append(f"{indent} null")


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


def eval_node_to_string(node: EvalNode, cells: list[str], top_cell=None):
    lines = []
    if isinstance(node, (ChoiceNode, SumNode)):
        _sum_to_list(node, cells, lines, indent="", prev_cell=top_cell)
    else:
        _into_list(node, cells, lines, indent="")
    return "\n".join(lines)


def size_stats(
    node: EvalNode, level=0, num_children=None, num_nodes=None, num_singles=None
):
    if num_children is None:
        num_children = Counter[int]()
        num_nodes = Counter[int]()
        num_singles = Counter[int]()
    children = node.get_children()
    num_children[level] += len(children)
    num_nodes[level] += 1
    if len(children) == 1:
        num_singles[level] += 1
    for child in children:
        size_stats(child, level + 1, num_children, num_nodes, num_singles)
    return num_children, num_nodes, num_singles


def eval_all(node: EvalNode, cells: list[str]):
    """Evaluate all possible boards.

    This is defined externally to EvalNode so that it can be used with C++ EvalNode, too.
    """
    num_letters = [len(cell) for cell in cells]
    indices = [range(n) for n in num_letters]
    return {
        choices: node.score_with_forces(choices)
        for choices in itertools.product(*indices)
    }


def split_orderly_tree(tree: EvalNode, arena: PyArena):
    """Split an orderly(N) into the choice for N and an orderly(N-1) tree.

    Points on the input tree are put on the output tree.
    """
    assert tree.letter != CHOICE_NODE
    top_choice = tree.children[0]
    assert top_choice.letter == CHOICE_NODE

    children = tree.children[1:]
    n = EvalNode()
    arena.add_node(n)
    n.letter = tree.letter
    n.cell = tree.cell
    n.children = children
    n.points = tree.points
    n.bound = n.points + sum(child.bound for child in children if child)
    return top_choice, n


def merge_orderly_tree(a: EvalNode, b: EvalNode, arena: PyArena):
    """Merge two orderly(N) trees."""
    assert a.letter != CHOICE_NODE
    assert b.letter != CHOICE_NODE
    return merge_orderly_tree_children(a, b.children, b.points, arena)


def merge_orderly_tree_children(
    a: EvalNode, bc: Sequence[EvalNode], b_points: int, arena: PyArena
):
    # TODO: it may be safe to merge bc in-place into a and avoid an allocation.
    #       might need to be careful with the out.append(b) case, though.
    assert a.letter != CHOICE_NODE
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

    n = EvalNode()
    n.letter = in_a.letter
    n.cell = in_a.cell
    n.children = out
    n.points = in_a.points + b_points
    n.bound = n.points + sum(child.bound for child in n.children)
    arena.add_node(n)
    return n


def merge_orderly_choice_children(a: EvalNode, b: EvalNode, arena: PyArena):
    """Merge two orderly choice nodes for the same cell."""
    in_a = a
    assert a.letter == CHOICE_NODE
    assert b.letter == CHOICE_NODE
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

    n = EvalNode()
    n.letter = in_a.letter
    n.cell = in_a.cell
    n.children = out
    n.points = 0
    n.bound = max(child.bound for child in n.children)
    arena.add_node(n)
    return n
