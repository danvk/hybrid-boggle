# Try to speed up ibuckets by explicitly constructing an evaluation tree.

import itertools
from collections import Counter
from typing import Self, Sequence

from boggle.boggler import LETTER_A, LETTER_Q, SCORES
from boggle.ibuckets import PyBucketBoggler, ScoreDetails
from boggle.trie import PyTrie, make_lookup_table

ROOT_NODE = -2
CHOICE_NODE = -1


# This produces more compact, efficient trees, but this adds complexity and
# seems not to be worth the effort except for the most complex of trees.
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
        pass

    def free_the_children(self):
        pass

    def num_nodes(self):
        return "n/a"

    def mark_and_sweep(self, root, mark):
        return 0


def create_eval_node_arena_py():
    return PyArena()


cache_count = 1
hash_collisions = 0


class EvalNode:
    letter: int
    cell: int
    bound: int
    points: int
    children: list[Self | None]
    trie_node: PyTrie | None

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

    def recompute_score(self):
        # Should return self.bound
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

    def score_with_forces_dict(
        self, forces: dict[int, int], num_cells: int, cells: list[str]
    ) -> int:
        """Requires that set_choice_point_mask() has been called on this tree."""
        forces_list = [forces.get(i, -1) for i in range(num_cells)]
        return self.score_with_forces(forces_list)

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
                if child:
                    bound += child.bound
                    choice_mask |= child.choice_mask
                    if child.letter == CHOICE_NODE:
                        assert child.cell not in seen_choices
                        seen_choices.add(child.cell)
                # TODO: sum nodes should not have null children
                #       (this does happen after lifting)
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

    def lift_choice(
        self,
        cell: int,
        num_lets: int,
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

        # aligned_results is dense.
        # len(aligned_results) = len(self.children)
        # len(aligned_results[0]) = num_lets
        # TODO: transpose this to simplify the next loop
        aligned_results = [
            r if isinstance(r, list) else [r] * num_lets for r in results
        ]
        # Construct a new sum node for each forced letter.
        out = []
        for i in range(num_lets):
            children = [result[i] for result in aligned_results]
            node_choice_mask = 0
            if self.letter == CHOICE_NODE:
                non_null_children = [c for c in children if c]
                node_bound = (
                    max(child.bound for child in non_null_children)
                    if non_null_children
                    else 0
                )
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
                    any_changes = False
                    if compress and node.letter != CHOICE_NODE:
                        any_changes = squeeze_sum_node_in_place(node, MERGE_TREES)

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

    def prune(self):
        # TODO: remove, this should always be a no-op
        if self.bound == 0 and self.letter != ROOT_NODE:
            return False  # discard
        new_children = [child for child in self.children if child and child.prune()]
        self.children = new_children
        return True  # keep

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

    def print_words(self, solver: PyBucketBoggler, prefix=""):
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

    def max_subtrees(
        self, out=None, path=None
    ) -> list[tuple[list[tuple[int, int]], Self]]:
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

    def all_words(self, word_table: dict[PyTrie, str]) -> list[str]:
        return [
            word_table[node.trie_node] for node in self.all_nodes() if node.trie_node
        ]

    def print_paths(self, word: str, word_table: dict[PyTrie, str], prefix=""):
        if self.letter == ROOT_NODE:
            prefix = "r"
        elif self.letter == CHOICE_NODE:
            prefix += f"->(CH {self.cell})"
        else:
            prefix += f"->({self.cell}={self.letter})"
        if self.points and word_table[self.trie_node] == word:
            print(prefix)
        else:
            for child in self.children:
                child.print_paths(word, word_table, prefix)

    def to_dot(self, cells: list[str], max_depth=100, trie=None) -> str:
        lookup_table = make_lookup_table(trie) if trie else None
        _root_id, dot = self.to_dot_help(
            cells, "", {}, self.letter == CHOICE_NODE, max_depth, lookup_table
        )
        return f"""graph {{
    rankdir=LR;
    splines="false";
    node [shape="rect"];
    {dot}
}}
"""

    def to_dot_help(
        self, cells: list[str], prefix, cache, is_top_max, remaining_depth, lookup_table
    ) -> tuple[str, str]:
        """Returns ID of this node plus DOT for its subtree."""
        is_dupe = False  # self in cache  # hasattr(self, "flag")
        me = prefix

        # if self.letter != CHOICE_NODE:
        #     is_dupe = any_choice_collisions(self.children)

        attrs = ""
        if is_dupe:
            attrs = 'color="red"'
        if self.letter == ROOT_NODE:
            me += "r"
            label = "ROOT"
        elif self.letter == CHOICE_NODE:
            me += f"_{self.cell}c"
            label = f"{self.cell} CH"
            attrs += ' shape="oval"'
        else:
            letter = cells[self.cell][self.letter]
            me += f"_{self.cell}{letter}"
            label = f"{self.cell}={letter}"
            if self.points:
                label += f" ({self.points})"
                attrs += ' peripheries="2"'
                if self.trie_node and lookup_table:
                    word = lookup_table[self.trie_node]
                    label += f"\\nword={word}"
        label += f"\\nbound={self.bound}"
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
            )
            for i, child in enumerate(self.children)
            if child
        ]
        all_choices = len(children) == len(self.children) and all(
            c.letter == CHOICE_NODE for c in self.children
        )
        # print(f"{is_top_max=}, {all_choices=}")
        for i, (child_id, _) in enumerate(children):
            attrs = ""
            if is_top_max and all_choices:
                letter = cells[self.cell][i]
                attrs = f' [label="{self.cell}={letter}"]'
            dot.append(f"{me} -- {child_id}{attrs};")
        for _, child_dot in children:
            dot.append(child_dot)
        return me, "\n".join(dot)

    def to_json(self, solver: PyBucketBoggler, max_depth=100, lookup=None):
        if not lookup:
            lookup = make_lookup_table(solver.trie_)
        out = {
            "type": (
                "ROOT"
                if self.letter == ROOT_NODE
                else "CHOICE"
                if self.letter == CHOICE_NODE
                else f"{self.cell}={solver.bd_[self.cell][self.letter]} ({self.letter})"
            ),
            "cell": self.cell,
            "bound": self.bound,
        }
        if self.choice_mask:
            out["mask"] = [i for i in range(16) if self.choice_mask & (1 << i)]
        if self.points:
            out["points"] = self.points
        if self.trie_node:
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
                    child.to_json(solver, max_depth - 1, lookup)
                    for child in self.children
                ]
        return out

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

    def set_computed_fields_for_testing(self, cells: Sequence[str]):
        for c in self.children:
            if c:
                c.set_computed_fields_for_testing(cells)

        if self.letter == CHOICE_NODE:
            self.choice_mask = 1 << self.cell if len(cells[self.cell]) > 1 else 0
            self.bound = (
                max(c.bound for c in self.children if c) if self.children else 0
            )
        else:
            self.choice_mask = 0
            self.bound = self.points + sum(c.bound for c in self.children if c)

        for c in self.children:
            if c:
                self.choice_mask |= c.choice_mask


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
    nnc = [c for c in child.children if c]
    if len(nnc) == 1:
        child = nnc[0]
    return child


def any_choice_collisions(choices: Sequence[EvalNode]) -> bool:
    by_cell = set[int]()
    for child in choices:
        if child:
            if child.cell in by_cell:
                return True
            by_cell.add(child.cell)
    return False


def merge_choice_collisions_in_place(choices: Sequence[EvalNode]):
    choices.sort(key=lambda c: c.cell)
    children = []
    for c in choices:
        if not children or c.cell != children[-1].cell:
            children.append(c)
            continue
        assert children[-1].cell == c.cell
        children[-1] = merge_trees(children[-1], c)

    # TODO: do this in-place on choices
    # for i, c in enumerate(children):
    #     choices[i] = children[i]
    # del children[len(choices) :]
    return children


def squeeze_sum_node_in_place(node: EvalNode, should_merge=False):
    """Absorb non-choice nodes into this sum node. Operates in-place.

    Returns a boolean indicating whether any changes were made.
    """
    if not node.children:
        return False

    non_choice = []
    choice = []
    any_choice_changes = False
    for c in node.children:
        if c:  # XXX this should not be necessary; sum nodes should prune
            if c.letter == CHOICE_NODE:
                choice.append(c)
            else:
                non_choice.append(c)
        else:
            any_choice_changes = True

    # look for repeated choice cells
    if should_merge and any_choice_collisions(choice):
        choice = merge_choice_collisions_in_place(choice)
        any_choice_changes = True

    # TODO: prune NULLs here, too
    if not non_choice:
        if any_choice_changes:
            node.children = choice
            node.bound = (node.points or 0) + sum(c.bound for c in choice)
            return True
        return False

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
    if should_merge and any_choice_collisions(new_children):
        new_children = merge_choice_collisions_in_place(new_children)

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


def eval_node_to_string(node: EvalNode, cells: list[str]):
    lines = []
    _into_list(node, cells, lines)
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


def merge_trees(a: EvalNode, b: EvalNode) -> EvalNode:
    assert a.cell == b.cell, f"{a.cell} != {b.cell}"
    COUNTS["merge"] += 1

    if a.letter == CHOICE_NODE and b.letter == CHOICE_NODE:
        # merge equivalent choices
        choices = {}
        for child in a.children:
            if child:
                choices[child.letter] = child
        for child in b.children:
            if child:
                existing = choices.get(child.letter)
                if existing:
                    choices[child.letter] = merge_trees(existing, child)
                else:
                    choices[child.letter] = child
        children = [*choices.values()]
        children.sort(key=lambda c: c.letter)
        n = EvalNode()
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
        n.letter = a.letter
        n.cell = a.cell
        n.children = children
        n.points = a.points + b.points
        n.bound = n.points + sum(child.bound for child in children if child)
        n.choice_mask = a.choice_mask | b.choice_mask  # TODO: recalculate?
        squeeze_sum_node_in_place(n, True)
        return n
    raise ValueError(
        f"Cannot merge CHOICE_NODE with non-choice: {a.cell}: {a.letter}/{b.letter}"
    )


class EvalTreeBoggler(PyBucketBoggler):
    def __init__(self, trie: PyTrie, dims: tuple[int, int] = (3, 3)):
        super().__init__(trie, dims)

    def UpperBound(self, bailout_score):
        raise NotImplementedError()

    def BuildTree(self, arena=None, dedupe=False):
        root = EvalNode()
        self.root = root
        root.letter = ROOT_NODE
        root.cell = 0  # irrelevant
        root.points = 0
        self.details_ = ScoreDetails(0, 0, -1)
        self.used_ = 0
        self.runs_ = self.trie_.Mark() + 1
        self.trie_.SetMark(self.runs_)
        self.node_cache = {}
        self.dedupe = dedupe

        for i in range(len(self.bd_)):
            child = EvalNode()
            child.letter = CHOICE_NODE
            child.cell = i
            score = self.DoAllDescents(i, 0, self.trie_, child)
            if score > 0:
                self.details_.max_nomark += score
                root.children.append(child)
                if len(self.bd_[i]) > 1:
                    # TODO: consolidate this with similar code in DoDFS
                    child.choice_mask |= 1 << i
                root.choice_mask |= child.choice_mask
        root.bound = self.details_.max_nomark
        # print(f"build tree node cache size: {len(self.node_cache)}")
        self.node_cache = {}
        return root

    def DoAllDescents(self, idx: int, length: int, t: PyTrie, node: EvalNode):
        max_score = 0

        for j, char in enumerate(self.bd_[idx]):
            cc = ord(char) - LETTER_A
            if t.StartsWord(cc):
                child = EvalNode()
                child.cell = idx
                child.letter = j
                tscore = self.DoDFS(
                    idx, length + (2 if cc == LETTER_Q else 1), t.Descend(cc), child
                )
                child = self.get_canonical_node(child)
                if tscore > 0:
                    max_score = max(max_score, tscore)
                    node.children.append(child)
                    node.choice_mask |= child.choice_mask
        node.bound = max_score
        node.points = 0
        return max_score

    def DoDFS(self, i: int, length: int, t: PyTrie, node: EvalNode):
        score = 0
        self.used_ ^= 1 << i

        for idx in self.neighbors[i]:
            if not self.used_ & (1 << idx):
                neighbor = EvalNode()
                neighbor.letter = CHOICE_NODE
                neighbor.cell = idx
                if len(self.bd_[idx]) > 1:
                    neighbor.choice_mask = 1 << idx
                tscore = self.DoAllDescents(idx, length, t, neighbor)
                neighbor = self.get_canonical_node(neighbor)
                if tscore > 0:
                    score += tscore
                    node.children.append(neighbor)
                    node.choice_mask |= neighbor.choice_mask

        node.points = 0
        if t.IsWord():
            word_score = SCORES[length]
            node.points = word_score
            node.trie_node = t
            score += word_score
            if t.Mark() != self.runs_:
                self.details_.sum_union += word_score
                t.SetMark(self.runs_)
        elif len(node.children) == 1:
            # COUNTS["singleton children"] += 1
            # node.assign_from(node.children[0])
            pass

        self.used_ ^= 1 << i
        node.bound = score
        return score

    def get_canonical_node(self, node: EvalNode):
        if not self.dedupe:
            return node
        h = node.structural_hash()
        prev = self.node_cache.get(h)
        if prev:
            return prev
        self.node_cache[h] = node
        return node

    def create_arena(self):
        return create_eval_node_arena_py()
