"""A tree representing the evaluation of a class of Boggle boards.

See https://www.danvk.org/2025/02/13/boggle2025.html#the-evaluation-tree

There are two types of nodes: sum and choice:

- Sum nodes sum points across their children. This models how you can move in any direction
  to extend a word, or start words from any cell on the board.
- Choice nodes reflect a choice that must be made, namely which letter to choose for
  a cell for a board in the board class. To get a bound, we can take the max across any
  choice, but this is imprecise because the same choice can appear in many subtrees and
  our choices won't be synchronized across those subtrees.

You can use node.bound to get the current upper bound for any subtree.
To reduce the bound, you can "lift" a choice on a cell to the top of the subtree, thus
synchronizing it across all subtrees. This comes at the cost of allocating new nodes.

It's a battle to keep tree operations from blowing up the number of nodes too much.
There are two ways to shrink the tree: compression and deduplication. Compression
restructures the tree into an equivalent but more compact representation, and de-
duplication replaces structurally equivalent nodes with references to the same object.
These are both described in the blog post linked above.
"""

import itertools
from collections import Counter
from typing import Self, Sequence

from boggle.board_class_boggler import BoardClassBoggler
from boggle.trie import PyTrie, make_lookup_table

ROOT_NODE = -2
CHOICE_NODE = -1


# This produces more compact, efficient trees at the cost of compute.
# This isn't worth the effort is Python, but it definitely _is_ in C++.
MERGE_TREES = True


COUNTS = Counter[str]()


def ResetEvalTreeCount():
    COUNTS.clear()


def PrintEvalTreeCounts():
    for k in sorted(COUNTS):
        print(k, COUNTS[k])


class PyArena:
    """This class is useless, but it helps maintain the same API as C++."""

    def __init__(self):
        self.count = 0

    def free_the_children(self):
        pass

    def num_nodes(self):
        return self.count

    def new_node(self):
        n = EvalNode()
        n.letter = ROOT_NODE
        n.cell = 0
        return n

    def add_node(self, node):
        self.count += 1


def create_eval_node_arena_py():
    return PyArena()


cache_count = 1
hash_collisions = 0


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
    """Points provided by _this_ node, not children.

    Only relevant for sum nodes, unless you call set_choice_point_mask(), in which case
    it's a bit mask for which children are set that's used by bound_remaining_boards().
    """

    choice_mask: int
    """Which choice nodes appear in this subtree?

    If choice_mask & (1<<C) == 0 then there is no choice node for cell C under us.
    """

    children: list[Self | None]
    """For sum nodes: the children to sum, in no particular order.
    For choice nodes: the choices, ordered by child.letter.

    For a choice node for cell C, children will typically have child.cell = C,
    but this may not be the case at the very top of the tree, where a dense representation
    is used to represent a "choice pyramid."

    null children are rare, particularly with compress=True, but they can occur.
    """

    trie_node: PyTrie | None
    """If set, the node in the Trie that this corresponds to."""

    # TODO: could even track _which_ choice on each cell matters
    choice_mask: int
    """If a child has choice for cell i, then (1<<i) will be set."""

    def __init__(self):
        self.children = []
        self.points = 0
        self.choice_mask = 0
        self.trie_node = None
        self.cache_key = None
        self.cache_value = None

    def add_word(
        self,
        choices: Sequence[tuple[int, int]],
        points: int,
        arena,
        cell_counts: list[int] = None,
    ):
        """Add a word at the end of a sequence of choices to the tree.

        This doesn't update bounds or choice_mask.
        """
        assert self.letter != CHOICE_NODE
        if not choices:
            self.points += points
            return

        (cell, letter) = choices[0]
        remaining_choices = choices[1:]

        choice_child = None
        for c in self.children:
            if c.cell == cell:
                choice_child = c
                break
        if not choice_child:
            choice_child = EvalNode()
            choice_child.letter = CHOICE_NODE
            choice_child.cell = cell
            self.children.append(choice_child)
            if cell_counts:
                cell_counts[cell] += 1
            if arena:
                arena.add_node(choice_child)
            self.children.sort(key=lambda c: c.cell)

        letter_child = None
        for c in choice_child.children:
            if c.letter == letter:
                letter_child = c
                break
        if not letter_child:
            letter_child = EvalNode()
            letter_child.cell = cell
            letter_child.letter = letter
            choice_child.children.append(letter_child)
            choice_child.children.sort(key=lambda c: c.letter)
            if arena:
                arena.add_node(letter_child)

        letter_child.add_word(remaining_choices, points, arena, cell_counts)

    def score_with_forces(self, forces: list[int]) -> int:
        """Requires that set_choice_point_mask() has been called on this tree."""
        choice_mask = 0
        for cell, letter in enumerate(forces):
            if letter >= 0:
                choice_mask |= 1 << cell
        return self.score_with_forces_mask(forces, choice_mask)

    def score_with_forces_mask(
        self,
        forces: list[int],
        choice_mask: int,
    ) -> int:
        """Requires that set_choice_point_mask() has been called on this tree."""
        if self.letter == CHOICE_NODE:
            force = forces[self.cell]
            if force >= 0:
                if self.points & (1 << force):
                    mask = self.points & ((1 << force) - 1)
                    idx = mask.bit_count()
                    child = self.children[idx]
                    if child:
                        return child.score_with_forces_mask(forces, choice_mask)
                return 0

        if not (self.choice_mask & choice_mask):
            # The force is irrelevant to this subtree, so we don't need to traverse it.
            return self.bound

        # Otherwise, this is the same as regular scoring
        if self.letter == CHOICE_NODE:
            v = (
                max(
                    child.score_with_forces_mask(forces, choice_mask) if child else 0
                    for child in self.children
                )
                if self.children
                else 0
            )
        else:
            v = self.points + sum(
                child.score_with_forces_mask(forces, choice_mask) if child else 0
                for child in self.children
            )
        return v

    def lift_choice(
        self,
        cell: int,
        num_lets: int,
        # TODO: make these required params
        arena=None,
        mark=None,
        dedupe=False,
        compress=False,
    ) -> Self:
        """Return a version of this tree with a choice on the cell at the root.

        Will return either a choice node for the cell, or another type of node
        if there is the tree is independent of that cell.

        mark must be some value that's never been used as a mark in this EvalTree before.
        """
        global hash_collisions
        assert mark
        hash_collisions = 0

        if self.letter == CHOICE_NODE and self.cell == cell:
            # This is already in the right form. Nothing more to do!
            # TODO: consider pulling in the compressing optimization from force_cell
            return self

        if self.choice_mask & (1 << cell) == 0:
            # There's no relevant choice below us, so we can bottom out.
            return self

        choices = self.force_cell(
            cell,
            num_lets,
            arena,
            vector_arena=None,
            mark=mark,
            dedupe=dedupe,
            compress=compress,
        )
        node = EvalNode()
        node.letter = CHOICE_NODE
        node.cell = cell
        node.points = 0
        node.bound = max(child.bound for child in choices)
        node.trie_node = None
        node.children = choices
        node.choice_mask = 1 << cell
        for child in choices:
            node.choice_mask |= child.choice_mask
        if arena:
            arena.add_node(node)
        return node

    def force_cell(
        self,
        force_cell: int,
        num_lets: int,
        arena=None,
        vector_arena=None,
        mark=None,
        dedupe=False,
        compress=False,
    ) -> Self | list[Self]:
        """Helper for lift_choice"""
        assert mark
        force_cell_cache = {}
        out = self.force_cell_work(
            force_cell,
            num_lets,
            force_cell_cache,
            arena,
            mark,
            dedupe=dedupe,
            compress=compress,
        )
        # print(f"cache size: {len(force_cell_cache)}")
        return out

    def force_cell_work(
        self,
        force_cell: int,
        num_lets: int,
        force_cell_cache,
        arena=None,
        mark=None,
        dedupe=False,
        compress=False,
    ) -> Self | list[Self]:
        """Try each possibility for a cell.

        num_lets is the number of possibilities for the cell.
        Returns a list of trees, one for each letter, or a Tree if there's no choice.
        """
        assert mark
        if self.cache_key == mark:
            return self.cache_value

        # COUNTS["force calls"] += 1
        if self.letter == CHOICE_NODE and self.cell == force_cell:
            # This is the forced cell.
            # We've already tried each possibility, but they may not be aligned.
            out = [None] * num_lets
            for child in self.children:
                if child:
                    letter = child.letter
                    if compress:
                        child = squeeze_choice_child(child)
                    out[letter] = child
                    assert child.choice_mask & (1 << force_cell) == 0
            self.cache_key = mark
            self.cache_value = out
            return out

        if self.choice_mask & (1 << force_cell) == 0:
            # There's no relevant choice below us, so we can bottom out.
            self.cache_key = mark
            self.cache_value = self
            return self

        # Make the recursive calls and align the results.
        # For a choice node, take the max. For other nodes, take the sum.
        results = [
            child.force_cell_work(
                force_cell, num_lets, force_cell_cache, arena, mark, dedupe, compress
            )
            if child
            else None
            for child in self.children
        ]

        # Construct a new sum node for each forced letter.
        out = []
        for i in range(num_lets):
            children = []
            for result in results:
                if isinstance(result, EvalNode):
                    children.append(result)
                else:
                    children.append(result[i] if result else None)

            node_choice_mask = 0
            if self.letter == CHOICE_NODE:
                node_bound = 0
                for child in children:
                    if child:
                        node_bound = max(node_bound, child.bound)
                # TODO: Why the "& self.choice_mask" here? It _is_ needed.
                node_choice_mask = (1 << self.cell) & self.choice_mask
            else:
                node_bound = self.points + sum(
                    child.bound for child in children if child
                )

            if node_bound > 0:
                node = EvalNode()
                node.letter = self.letter
                node.points = self.points
                node.trie_node = self.trie_node
                node.cell = self.cell
                node.bound = node_bound
                node.children = children
                node.choice_mask = node_choice_mask
                if self.letter == ROOT_NODE:
                    # It would be nice to leave this as a ROOT_NODE to simplify finding the
                    # edge of the max root tree vs. the eval tree.
                    node.letter = i
                    node.cell = force_cell
                for child in children:
                    if child:
                        node.choice_mask |= child.choice_mask

                prev = None
                if dedupe:
                    h = node.structural_hash()
                    match = force_cell_cache.get(h)
                    if match:
                        if (
                            match.letter == node.letter and match.cell == node.cell
                            # and match.points == node.points
                        ):
                            prev = match
                        else:
                            global hash_collisions
                            hash_collisions += 1
                else:
                    prev = h = None
                if prev:
                    node = prev
                    # COUNTS["cache hits"] += 1
                else:
                    if arena:
                        arena.add_node(node)
                    any_changes = False
                    if compress and node.letter != CHOICE_NODE:
                        any_changes = squeeze_sum_node_in_place(
                            node, arena, MERGE_TREES
                        )

                    if dedupe:
                        force_cell_cache[h] = node
                        if any_changes:
                            # This lets us cache both lifting _and_ squeezing.
                            force_cell_cache[node.structural_hash()] = node
            else:
                node = None

            out.append(node)
        self.cache_key = mark
        self.cache_value = out
        return out

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

        if non_cell_points and len(top_choice.children) < num_lets:
            # TODO: this node could be shared with a different tree representation.
            for i, child in enumerate(out):
                if not child:
                    point_node = EvalNode()
                    point_node.points = point_node.bound = non_cell_points
                    point_node.cell = cell
                    point_node.letter = i
                    arena.add_node(point_node)
                    out[i] = point_node
        return out

    def filter_below_threshold(self, min_score: int) -> int:
        """Remove choice subtrees with bounds equal to or below min_score.

        This operates in-place. It only operates on subtrees that are connected
        to the root exclusively through choice nodes. This won't reduce any bounds,
        but it will reduce the number of nodes.
        """
        # TODO: this would be more efficient to do in force_cell.
        # this could use the caching system, but it's unlikely that the max trees are cached.
        if self.letter != CHOICE_NODE:
            return 0
        assert self.bound > min_score
        n_filtered = 0
        for i, child in enumerate(self.children):
            if not child:
                continue
            if child.bound <= min_score:
                self.children[i] = None
                n_filtered += 1
            else:
                n_filtered += child.filter_below_threshold(min_score)
        return n_filtered

    def node_count(self):
        return 1 + sum(child.node_count() for child in self.children if child)

    def unique_node_count(self, mark):
        return sum(1 for _ in self.all_nodes_unique(mark))

    def structural_hash(self) -> int:
        if hasattr(self, "_hash"):
            return getattr(self, "_hash")
        text = f"{self.letter} {self.cell} {self.points} "
        # Including the trie node is an interesting trade-off.
        # It reduces the effectiveness of de-duping, but keeps tree merging
        # as a possibility post-de-duping.
        # if self.trie_node:
        #     text += str(hash(self.trie_node)) + " "
        # TODO: if child nodes are already de-duped, can we use hash(c) here?
        #       evidently not, but we don't lose too much (~5% increase in nodes)
        # text += " ".join(str(c.structural_hash()) for c in self.children if c)
        text += " ".join((str(c.structural_hash()) if c else "") for c in self.children)
        # text += " ".join(str(hash(c)) for c in self.children)
        h = hash(text)
        self._hash = h
        return h

    def set_choice_point_mask(self, num_letters: Sequence[int]):
        if self.letter == CHOICE_NODE and self.points == 0:
            n = num_letters[self.cell]
            if len(self.children) == n:
                # dense -- the children are all set, but may be null.
                self.points = (1 << n) - 1
            else:
                # sparse
                last_letter = -1
                for child in self.children:
                    if child:
                        self.points += 1 << child.letter
                        assert child.letter != last_letter
                        last_letter = child.letter
                    else:
                        # null children still affect the index in the children list.
                        last_letter += 1
                        self.points += 1 << last_letter

        for c in self.children:
            if c:
                c.set_choice_point_mask(num_letters)

    def bound_remaining_boards(
        self, cells: Sequence[str], cutoff: int, split_order: Sequence[int]
    ):
        """Try all remaining boards to determine which ones might have a score >= cutoff."""
        results = []

        # TODO: this could share a lot of work by calling score_with_forces on the root.
        for t, seq in self.max_subtrees():
            choices = [-1 for _ in cells]
            for cell, letter in seq:
                choices[cell] = letter
            remaining_split_order = []
            for order in split_order:
                if choices[order] == -1:
                    remaining_split_order.append(order)
            # print("remaining cells:", sum(1 for x in choices if x == -1))
            bound_remaining_boards_help(
                t,
                cells,
                choices,
                cutoff,
                remaining_split_order,
                0,
                results,
            )
        return results

    def max_subtrees(
        self, out=None, path=None
    ) -> list[tuple[Self, list[tuple[int, int]]]]:
        """Yield all subtrees below a choice node.

        Each yielded value is a list of (cell, letter) choices leading down to the tree.
        """
        if out is None:
            out = []
        if path is None:
            path = []

        if self.letter != CHOICE_NODE:
            out.append((self, path))
        else:
            for i, child in enumerate(self.children):
                if child:
                    child.max_subtrees(out, path + [(self.cell, i)])
        return out

    def set_computed_fields(self, num_letters: Sequence[int]):
        for c in self.children:
            if c:
                c.set_computed_fields(num_letters)

        if self.letter == CHOICE_NODE:
            self.choice_mask = 1 << self.cell if num_letters[self.cell] > 1 else 0
            self.bound = (
                max(c.bound for c in self.children if c) if self.children else 0
            )
        else:
            self.choice_mask = 0
            self.bound = self.points + sum(c.bound for c in self.children if c)

        for c in self.children:
            if c:
                self.choice_mask |= c.choice_mask

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

    def node_counts(self, out=None):
        if out is None:
            out = Counter[Self]()
        out[self] += 1
        for child in self.children:
            child.node_counts(out)
        return out

    def recompute_score(self):
        """Should return self.bound. (For debugging/testing)"""
        if self.letter == CHOICE_NODE:
            return (
                max(child.recompute_score() if child else 0 for child in self.children)
                if self.children
                else 0
            )
        else:
            return self.points + sum(
                child.recompute_score() if child else 0 for child in self.children
            )

    def structural_eq(self, other: Self) -> bool:
        """Deep structural equality (for debugging)."""
        if self.letter != other.letter or self.cell != other.cell:
            return False
        if self.bound != other.bound:
            return False
        if self.points != other.points:
            return False
        nnc = [c for c in self.children if c]
        nno = [c for c in other.children if c]
        if len(nnc) != len(nno):
            return False
        for a, b in zip(nnc, nno):
            if a == b:
                continue
            if a is None or b is None:
                return False
            if not a.structural_eq(b):
                return False
        return True

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

    def assert_invariants(self, solver, is_top_max=None):
        """Ensure the tree is well-formed. Some desirable properties:

        - Choice nodes do not have points.
        - node.bound is correct (checked shallowly)
        - node.choice_mask is correct (checked shallowly)
        - choice node children are mutually-exclusive
        - choice node children are sorted
        - no duplicate choice children for sum nodes
        """
        if is_top_max is None:
            is_top_max = self.letter == CHOICE_NODE
        if self.letter == CHOICE_NODE:
            if not hasattr(self, "points") or self.points == 0:
                pass
            else:
                pass  # TODO: assert that child mask is set properly.
            if is_top_max and all(c and c.letter == CHOICE_NODE for c in self.children):
                pass
            else:
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
            choice_mask = 1 << self.cell if len(solver.bd_[self.cell]) > 1 else 0
            for child in self.children:
                if child:
                    bound = max(bound, child.bound)
                    choice_mask |= child.choice_mask
        else:
            bound = self.points
            choice_mask = 0
            seen_choices = set[int]()
            for child in self.children:
                assert child
                bound += child.bound
                choice_mask |= child.choice_mask
                if child.letter == CHOICE_NODE:
                    assert child.cell not in seen_choices
                    seen_choices.add(child.cell)
        # if bound != self.bound:
        #     print(f"Warning {bound} != {self.bound}")
        #     self.flag = True
        assert bound == self.bound
        assert choice_mask == self.choice_mask

        for child in self.children:
            if child:
                child.assert_invariants(
                    solver, is_top_max and child.letter == CHOICE_NODE
                )

    def prune(self):
        # TODO: remove, this should always be a no-op
        if self.bound == 0 and self.letter != ROOT_NODE:
            return False  # discard
        new_children = [child for child in self.children if child and child.prune()]
        self.children = new_children
        return True  # keep

    def reset_choice_point_mask(self):
        if self.letter == CHOICE_NODE:
            self.points = 0
        for child in self.children:
            if child:
                child.reset_choice_point_mask()

    def to_string(self, cells: list[str]):
        return eval_node_to_string(self, cells)

    def check_consistency(self):
        assert self.bound == self.recompute_score()
        for child in self.children:
            if child:
                child.check_consistency()

    def print_words(self, solver: BoardClassBoggler, prefix=""):
        if self.letter >= 0:
            char = solver.bd_[self.cell][self.letter]
            prefix += char
            if self.points:
                print(f" + {self.points}: {prefix}")
        for child in self.children:
            if child:
                child.print_words(solver, prefix)

    def choice_cells(self) -> set[int]:
        out = set()
        if self.letter == CHOICE_NODE:
            out.add(self.cell)
        for child in self.children:
            if child:
                out.update(child.choice_cells())
        return out

    def choice_letters(self, out=None) -> set[tuple[int, int]]:
        """All letters on each cell that lead to points."""
        if out is None:
            out = set()
        if self.letter >= 0:
            out.add((self.cell, self.letter))
        for child in self.children:
            child.choice_letters(out)
        return out

    def all_nodes(self):
        yield self
        for child in self.children:
            if child:
                yield from child.all_nodes()

    def all_nodes_postorder(self):
        for child in self.children:
            if child:
                yield from child.all_nodes_postorder()
        yield self

    def all_nodes_unique(self, mark=None):
        if mark is None:
            global cache_count
            cache_count += 1
            mark = cache_count
        if self.cache_key == mark:
            return
        self.cache_key = mark
        yield self
        for child in self.children:
            if child:
                yield from child.all_nodes_unique(mark)

    def all_words(self, word_table: dict[PyTrie, str]) -> list[str]:
        return [
            word_table[node.trie_node] for node in self.all_nodes() if node.trie_node
        ]

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
        if self.choice_mask:
            out["mask"] = [i for i in range(16) if self.choice_mask & (1 << i)]
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


def bound_remaining_boards_help(
    t: EvalNode,
    cells: Sequence[str],
    choices: list[int],
    cutoff: int,
    split_order: Sequence[int],
    split_order_index: int,
    results: list[str],
):
    cell = (
        split_order[split_order_index] if split_order_index < len(split_order) else -1
    )

    if cell == -1:
        board = "".join(cells[cell][idx] for cell, idx in enumerate(choices))
        results.append(board)
        return

    for idx, letter in enumerate(cells[cell]):
        choices[cell] = idx
        ub = t.score_with_forces(choices)
        if ub > cutoff:
            bound_remaining_boards_help(
                t,
                cells,
                choices,
                cutoff,
                split_order,
                1 + split_order_index,
                results,
            )
    choices[cell] = -1


def squeeze_choice_child(child: EvalNode):
    """Collapse sum nodes where possible."""
    # If this choice isn't a word on its own and it only has one child,
    # then we can remove it from the tree entirely.
    # This could be applied recursively, but this is rarely helpful.
    # TODO: find a specific example where this applies
    # TODO: this could be much more aggressive.
    if child.points:
        return child
    non_null_child = None
    for c in child.children:
        if c:
            if non_null_child:
                return child  # two non-null children
            non_null_child = c
    # return the non-null child if there's exactly one.
    return non_null_child if non_null_child else child


def any_choice_collisions(choices: Sequence[EvalNode]) -> bool:
    by_cell = set[int]()
    for child in choices:
        if child:
            if child.cell in by_cell:
                return True
            by_cell.add(child.cell)
    return False


def merge_choice_collisions_in_place(choices: list[EvalNode], arena):
    choices.sort(key=lambda c: c.cell)

    i = 0
    n = len(choices)
    while i < n:
        j = i + 1
        while j < n and choices[i].cell == choices[j].cell:
            choices[i] = merge_trees(choices[i], choices[j], arena)
            for k in range(j, n - 1):
                choices[k] = choices[k + 1]
            n -= 1
        i += 1

    while n < len(choices):
        choices.pop()


def squeeze_sum_node_in_place(node: EvalNode, arena, should_merge=False):
    """Absorb non-choice nodes into this sum node. Operates in-place.

    Returns a boolean indicating whether any changes were made.
    """
    if not node.children:
        return False

    any_sum_children = False
    any_null = False
    for c in node.children:
        if c:
            if c.letter != CHOICE_NODE:
                any_sum_children = True
                break
        else:
            any_null = True

    any_collisions = any_choice_collisions(node.children)

    if not any_sum_children and not any_collisions:
        if any_null:
            node.children = [c for c in node.children if c]
            return True
        return False

    non_choice = []
    choice = []
    for c in node.children:
        if c:  # XXX this should not be necessary; sum nodes should prune
            if c.letter == CHOICE_NODE:
                choice.append(c)
            else:
                non_choice.append(c)

    # look for repeated choice cells
    if should_merge and any_choice_collisions(choice):
        merge_choice_collisions_in_place(choice, arena)

    # There's something to absorb.
    # if I keep trie nodes, this would be a place to de-dupe them and improve the bound.
    new_children = choice
    new_points_from_children = 0
    for c in non_choice:
        new_points_from_children += c.points
        new_children += c.children

    for child in new_children:
        if child:
            assert child.letter == CHOICE_NODE

    # new_children should be entirely choice nodes now, but there may be new collisions
    # TODO: is it more efficient to do this all at once, before absorbing child nodes?
    if should_merge and any_choice_collisions(new_children):
        merge_choice_collisions_in_place(new_children, arena)

    node.children = new_children
    # We need to take care here not to double-count points for the bound.
    node.points += new_points_from_children
    node.bound = node.points + sum(c.bound for c in node.children if c)

    # COUNTS["absorb"] += 1
    return True


def _into_list(node: EvalNode, cells: list[str], lines: list[str], indent=""):
    line = ""
    if node.letter == ROOT_NODE:
        line = f"{indent}ROOT ({node.bound}) mask={node.choice_mask}"
    elif node.letter == CHOICE_NODE:
        line = f"{indent}CHOICE ({node.cell} <{node.bound}) mask={node.choice_mask} points={node.points}"
    else:
        cell = cells[node.cell][node.letter]
        line = f"{indent}{cell} ({node.cell}={node.letter} {node.points}/{node.bound}) mask={node.choice_mask}"
    lines.append(line)
    for child in node.children:
        if child:
            _into_list(child, cells, lines, " " + indent)
        # There are some slight discrepancies between C++ and Python trees that
        # are functionally irrelevant but surfaced if you uncomment this:
        # else:
        #     lines.append(f"{indent} null")


def eval_node_to_string(node: EvalNode, cells: list[str]):
    lines = []
    _into_list(node, cells, lines, indent="")
    return "\n".join(lines)


def eval_all(node: EvalNode, cells: list[str]):
    """Evaluate all possible boards.

    This is defined externally to EvalNode so that it can be used with C++ EvalNode, too.
    If you're going to do anything with the tree after this, make sure to call
    node.reset_choice_point_mask().
    """
    num_letters = [len(cell) for cell in cells]
    node.set_choice_point_mask(num_letters)
    indices = [range(n) for n in num_letters]
    return {
        choices: node.score_with_forces(choices)
        for choices in itertools.product(*indices)
    }


def eval_tree_from_json(d: dict) -> EvalNode:
    node = EvalNode()
    node.cell = d["cell"]
    node.letter = d["letter"]
    node.points = d.get("points")
    node.bound = d["bound"]
    node.children = [eval_tree_from_json(c) for c in d.get("children", [])]
    # TODO: could also attach trie nodes
    node.choice_mask = 0
    if node.letter == CHOICE_NODE:
        node.choice_mask |= 1 << node.cell
    for child in node.children:
        node.choice_mask |= child.choice_mask
    return node


def dedupe_subtrees(t: EvalNode):
    """Replace identical subtrees with a single copy."""
    global cache_count
    cache_count += 1

    hash_to_node = {}
    for node in t.all_nodes_postorder():
        if node.cache_key == cache_count:
            continue  # already de-duped; save the cost of hashing it.
        node.cache_key = cache_count
        h = node.structural_hash()
        if h not in hash_to_node:
            hash_to_node[h] = node
        else:
            pass  # in C++, this would be a good place to delete the node
        for i, n in enumerate(node.children):
            node.children[i] = hash_to_node[n.structural_hash()]


def merge_choice_children(a: EvalNode, b: EvalNode, arena, out: list[EvalNode]):
    i_a = 0
    i_b = 0
    ac = a.children
    bc = b.children
    a_n = len(ac)
    b_n = len(bc)

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
            out.append(merge_trees(a, b, arena))
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


def merge_trees(a: EvalNode, b: EvalNode, arena) -> EvalNode:
    assert a.cell == b.cell, f"{a.cell} != {b.cell}"
    COUNTS["merge"] += 1

    if a.letter == CHOICE_NODE and b.letter == CHOICE_NODE:
        children = []
        merge_choice_children(a, b, arena, children)

        n = EvalNode()
        if arena:
            arena.add_node(n)
        n.letter = CHOICE_NODE
        n.cell = a.cell
        n.children = children
        n.points = 0
        n.bound = max(child.bound for child in children if child) if children else 0
        n.choice_mask = a.choice_mask | b.choice_mask  # TODO: recalculate
        return n
    elif a.letter == b.letter:
        # two sum nodes.
        # Stick the children together and let squeeze_sum_node sort it all out.
        children = [*a.children, *b.children]
        children.sort(key=lambda c: c.cell)

        n = EvalNode()
        if arena:
            arena.add_node(n)
        n.letter = a.letter
        n.cell = a.cell
        n.children = children
        n.points = a.points + b.points
        n.bound = n.points + sum(child.bound for child in children if child)
        n.choice_mask = a.choice_mask | b.choice_mask  # TODO: recalculate?
        squeeze_sum_node_in_place(n, arena, True)
        return n
    raise ValueError(
        f"Cannot merge CHOICE_NODE with non-choice: {a.cell}: {a.letter}/{b.letter}"
    )


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
    n.choice_mask = 0
    for child in children:
        n.choice_mask |= child.choice_mask
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
    n.choice_mask = 0
    for child in n.children:
        n.choice_mask |= child.choice_mask
    arena.add_node(n)
    return n


def merge_orderly_choice_children(a: EvalNode, b: EvalNode, arena: PyArena):
    """Merge two orderly choice nodes for the same cell."""
    in_a, in_b = a, b
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
    n.choice_mask = in_a.choice_mask | in_b.choice_mask
    arena.add_node(n)
    return n
