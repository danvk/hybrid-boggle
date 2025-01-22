# Try to speed up ibuckets by explicitly constructing an evaluation tree.

import math
from collections import Counter, defaultdict
from typing import Self, Sequence

from boggle.boggler import LETTER_A, LETTER_Q, SCORES
from boggle.ibuckets import PyBucketBoggler, ScoreDetails
from boggle.trie import PyTrie, make_lookup_table
from boggle.util import group_by, partition

ROOT_NODE = -2
CHOICE_NODE = -1


# This produces more compact, efficient trees, but this adds complexity and
# seems not to be worth the effort except for the most complex of trees.
MERGE_AFTER_SPLIT = False


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


def create_eval_node_arena_py():
    return PyArena()


cache_count = 1
force_cell_cache = {}


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

    def score_with_forces_dict(self, forces: dict[int, int], num_cells: int) -> int:
        forces_list = [forces.get(i, -1) for i in range(num_cells)]
        return self.score_with_forces(forces_list)

    def score_with_forces(self, forces: list[int]) -> int:
        global cache_count
        cache_count += 1

        choice_mask = 0
        for cell, letter in enumerate(forces):
            if letter >= 0:
                choice_mask |= 1 << cell
        return self.score_with_forces_mask(forces, choice_mask, cache_count)

    def score_with_forces_mask(
        self, forces: list[int], choice_mask: int, cache_key: int
    ) -> int:
        if self.cache_key == cache_key:
            return self.cache_value

        if self.letter == CHOICE_NODE:
            force = forces[self.cell]
            if force >= 0:
                for child in self.children:
                    if child and child.letter == force:
                        v = child.score_with_forces_mask(forces, choice_mask, cache_key)
                        self.cache_key = cache_key
                        self.cache_value = v
                        return v
                self.cache_key = cache_key
                self.cache_value = 0
                return 0

        if not (self.choice_mask & choice_mask):
            # The force is irrelevant to this subtree, so we don't need to traverse it.
            return self.bound

        # Otherwise, this is the same as regular scoring
        if self.letter == CHOICE_NODE:
            v = (
                max(
                    child.score_with_forces_mask(forces, choice_mask, cache_key)
                    if child
                    else 0
                    for child in self.children
                )
                if self.children
                else 0
            )
        else:
            v = self.points + sum(
                child.score_with_forces_mask(forces, choice_mask, cache_key)
                if child
                else 0
                for child in self.children
            )
        self.cache_key = cache_key
        self.cache_value = v
        return v

    def lift_choice(
        self, cell: int, num_lets: int, arena=None, dedupe=False, compress=False
    ) -> Self:
        """Return a version of this tree with a choice on the cell at the root.

        Will return either a choice node for the cell, or another type of node
        if there is the tree is independent of that cell.
        """
        global cache_count
        cache_count += 1

        if self.letter == CHOICE_NODE and self.cell == cell:
            # This is already in the right form. Nothing more to do!
            # TODO: consider pulling in the compressing optimization from force_cell
            return self

        if self.choice_mask & (1 << cell) == 0:
            # There's no relevant choice below us, so we can bottom out.
            return self

        # TODO: make the code for constructing this directly (below) work.
        #       (or don't if this is more efficient!)
        choices = self.force_cell(
            cell, num_lets, arena, dedupe=dedupe, compress=compress
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

        subtrees = [child.lift_choice(cell, num_lets) for child in self.children]
        # Force the subtrees to all be choice nodes on the specified cell.
        # At least one must be a choice node, otherwise we would have returned earlier.
        non_choices, choices = partition(
            subtrees, lambda t: t.letter == CHOICE_NODE and t.cell == cell
        )
        assert choices

        # this is where copies of subtrees get made
        # an alternative is that a choice node could have a "baseline" subtree that
        # always contributes and does not involve the choice cell.
        aligned_results = [non_choices for _ in range(num_lets)]
        for choice in choices:
            # print("-", choice.letter, choice.cell)
            for c in choice.children:
                # print(c.cell, c.letter)
                assert 0 <= c.letter < num_lets
                aligned_results[c.letter].append(c)

        out_children = []
        for i, children in enumerate(aligned_results):
            node_choice_mask = 0
            if self.letter == CHOICE_NODE:
                node_bound = max(child.bound for child in children) if children else 0
                node_choice_mask = (1 << self.cell) & self.choice_mask
            else:
                node_bound = self.points + sum(child.bound for child in children)

            if node_bound > 0:
                node = EvalNode()
                node.letter = i
                node.points = self.points
                node.trie_node = self.trie_node  # is this right?
                node.cell = cell
                node.bound = node_bound
                node.children = children
                node.choice_mask = node_choice_mask
                for child in children:
                    node.choice_mask |= child.choice_mask
                out_children.append(node)

        # Produce the choice node
        node = EvalNode()
        node.letter = CHOICE_NODE
        node.cell = cell
        node.points = 0
        node.bound = max(child.bound for child in out_children)
        node.trie_node = None
        node.children = out_children
        node.choice_mask = 1 << cell
        for child in children:
            node.choice_mask |= child.choice_mask
        return node

    def force_cell(
        self, force_cell: int, num_lets: int, arena=None, dedupe=False, compress=False
    ) -> Self | list[Self]:
        global cache_count, force_cell_cache
        cache_count += 1
        force_cell_cache = {}
        out = self.force_cell_work(
            force_cell, num_lets, arena, dedupe=dedupe, compress=compress
        )
        # print(f"cache size: {len(force_cell_cache)}")
        force_cell_cache = {}
        return out

    def force_cell_work(
        self, force_cell: int, num_lets: int, arena=None, dedupe=False, compress=False
    ) -> Self | list[Self]:
        """Try each possibility for a cell.

        num_lets is the number of possibilities for the cell.
        Returns a list of trees, one for each letter, or a Tree if there's no choice.
        """
        if self.cache_key == cache_count:
            return self.cache_value

        # COUNTS["force calls"] += 1
        if self.letter == CHOICE_NODE and self.cell == force_cell:
            # This is the forced cell.
            # We've already tried each possibility, but they may not be aligned.
            out = [None] * num_lets
            for child in self.children:
                if child:
                    # If this choice isn't a word on its own and it only has one child,
                    # then we can remove it from the tree entirely.
                    # This could be applied recursively, but this is rarely helpful.
                    # TODO: find a specific example where this applies
                    letter = child.letter
                    if not child.points:
                        nnc = [c for c in child.children if c]
                        if len(nnc) == 1:
                            child = nnc[0]
                    out[letter] = child
                    assert child.choice_mask & (1 << force_cell) == 0
            self.cache_key = cache_count
            self.cache_value = out
            return out

        if self.choice_mask & (1 << force_cell) == 0:
            # There's no relevant choice below us, so we can bottom out.
            self.cache_key = cache_count
            self.cache_value = self
            return self

        # Make the recursive calls and align the results.
        # For a choice node, take the max. For other nodes, take the sum.
        results = [
            child.force_cell_work(force_cell, num_lets, arena, dedupe, compress)
            if child
            else None
            for child in self.children
        ]

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
                # TODO: Why the "& self.choice_mask" here?
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
                    # TODO: leave this as a root node if I adopt child index = choice
                    #       this would make it clearer where the end of the choice tree is.
                    node.letter = i
                    node.cell = force_cell
                for child in children:
                    if child:
                        node.choice_mask |= child.choice_mask

                if dedupe:
                    h = node.structural_hash()
                    prev = force_cell_cache.get(h)
                else:
                    prev = h = None
                if prev:
                    node = prev
                    # COUNTS["cache hits"] += 1
                else:
                    any_changes = False
                    if compress and node.children and node.letter != CHOICE_NODE:
                        # try to absorb non-choice nodes
                        # TODO: iterate on performance here.
                        non_choice = []
                        choice = []
                        for c in node.children:
                            if c:  # XXX this should not be necessary; sum nodes should prune
                                if c.letter == CHOICE_NODE:
                                    choice.append(c)
                                else:
                                    non_choice.append(c)
                        if non_choice:
                            # something to absorb
                            # if I keep trie nodes, this would be a place to de-dupe them and improve the bound.
                            any_changes = True
                            new_children = choice
                            for c in non_choice:
                                node.points = (node.points or 0) + c.points
                                new_children += c.children
                            node.children = new_children
                            # COUNTS["absorb"] += 1
                    if dedupe:
                        force_cell_cache[h] = node
                        if any_changes:
                            # TODO: check whether both hashes are necessary / helpful
                            force_cell_cache[node.structural_hash()] = node
            else:
                node = None

            out.append(node)
        self.cache_key = cache_count
        self.cache_value = out
        return out

    def prune(self):
        # TODO: remove, this should always be a no-op
        if self.bound == 0 and self.letter != ROOT_NODE:
            return False  # discard
        new_children = [child for child in self.children if child and child.prune()]
        self.children = new_children
        return True  # keep

    def filter_below_threshold(self, min_score: int):
        """Remove choice subtrees with bounds equal to or below min_score.

        This operates in-place. It only operates on subtrees that are connected
        to the root exclusively through choice nodes. This won't reduce any bounds,
        but it will reduce the number of nodes.
        """
        # TODO: this would be more efficient to do in force_cell.
        # this could use the caching system, but it's unlikely that the max trees are cached.
        if self.letter != CHOICE_NODE:
            return
        assert self.bound > min_score
        # any_dropped = False
        for i, child in enumerate(self.children):
            if not child:
                continue
            if child.bound <= min_score:
                self.children[i] = None
                # any_dropped = True
            else:
                child.filter_below_threshold(min_score)
        # XXX this might be the source of my bug
        # if any_dropped:
        #     self.children = [child for child in self.children if child]

    def compress_in_place(self, mark=None):
        # TODO: could this be done with a post-order version of all_nodes_unique?
        if mark is None:
            global cache_count
            cache_count += 1
            mark = cache_count
        if self.cache_key == mark:
            return  # we've already compressed this one
        self.cache_key = mark  # we're committed
        for child in self.children:
            child.compress_in_place(mark)
        if self.letter == CHOICE_NODE or not self.children:
            pass  # nothing to do here
        else:
            # absorb all of our non-choice children
            non_choice, choice = partition(
                self.children, lambda c: c.letter == CHOICE_NODE
            )
            if not non_choice:
                return  # all choice nodes, nothing left to do
            new_children = choice
            for c in non_choice:
                self.points = (self.points or 0) + c.points
                new_children += c.children
            self.children = new_children

    def node_count(self):
        return 1 + sum(child.node_count() for child in self.children if child)

    def unique_node_count(self):
        return sum(1 for _ in self.all_nodes_unique())

    def unique_node_count_by_hash(self):
        nodes = set()
        queue = [self]
        while queue:
            node = queue.pop()
            h = hash(node)
            if h in nodes:
                continue  # already visited this one
            nodes.add(h)
            for child in node.children:
                queue.append(child)
        return len(nodes)

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
        text += " ".join(str(c.structural_hash()) for c in self.children if c)
        # text += " ".join(str(hash(c)) for c in self.children)
        h = hash(text)
        self._hash = h
        return h

    def _into_list(self, solver: PyBucketBoggler, lines: list[str], indent=""):
        line = ""
        if self.letter == ROOT_NODE:
            line = f"{indent}ROOT ({self.bound}) mask={self.choice_mask}"
        elif self.letter == CHOICE_NODE:
            line = f"{indent}CHOICE ({self.cell} <{self.bound}) mask={self.choice_mask}"
        else:
            cell = solver.bd_[self.cell][self.letter]
            line = f"{indent}{cell} ({self.cell}={self.letter} {self.points}/{self.bound}) mask={self.choice_mask}"
        lines.append(line)
        for child in self.children:
            if child:
                child._into_list(solver, lines, " " + indent)

    def to_string(self, solver: PyBucketBoggler):
        lines = []
        self._into_list(solver, lines)
        return "\n".join(lines)

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

    def max_subtrees(self):
        """Yield all subtrees below a choice node.

        Each yielded value is a list of (cell, letter) choices leading down to the tree.
        """
        if self.letter != CHOICE_NODE:
            yield [self]
        else:
            for i, child in enumerate(self.children):
                if child:
                    for seq in child.max_subtrees():
                        yield [(self.cell, i)] + seq

    def all_words(self, word_table: dict[PyTrie, str]) -> list[str]:
        return [word_table[node.trie_node] for node in self.all_nodes() if node.points]

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

    def assign_from(self, other: Self):
        self.letter = other.letter
        self.cell = other.cell
        self.bound = other.bound
        self.points = other.points
        self.children = other.children
        self.choice_mask = other.choice_mask

    def to_dot(self, solver: PyBucketBoggler) -> str:
        _root_id, dot = self.to_dot_help(solver)
        return f"""digraph {{
    splines="false";
    node [shape="rect"];
    {dot}
}}
"""

    def to_dot_help(self, solver: PyBucketBoggler, prefix="") -> tuple[str, str]:
        """Returns ID of this node plus DOT for its subtree."""
        me = prefix
        attrs = ""
        if self.letter == ROOT_NODE:
            me += "r"
            label = "ROOT"
            attrs += ' shape="oval"'
        elif self.letter == CHOICE_NODE:
            me += f"_{self.cell}c"
            label = f"{self.cell} CH"
            attrs += ' shape="oval"'
        else:
            letter = solver.bd_[self.cell][self.letter]
            me += f"_{self.cell}{letter}"
            label = f"{self.cell}={letter}"
            if self.points:
                label += f" ({self.points})"
                attrs += ' peripheries="2"'
        dot = [f'{me} [label="{label}"{attrs}];']
        children = [child.to_dot_help(solver, me) for child in self.children if child]
        for child_id, _ in children:
            dot.append(f"{me} -> {child_id};")
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


def num_possibilities(letters: Sequence[tuple[int, int]]) -> int:
    by_cell = group_by(letters, lambda x: x[0])
    return math.prod(len(v) for v in by_cell.values())


def merge_trees(a: EvalNode, b: EvalNode) -> EvalNode:
    assert a.cell == b.cell, f"{a.cell} != {b.cell}"
    COUNTS["merge"] += 1

    if a.letter == CHOICE_NODE and b.letter == CHOICE_NODE:
        # merge equivalent choices
        choices = {}
        for child in a.children:
            choices[child.letter] = child
        for child in b.children:
            # choices[child.letter] = child
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
        n.bound = max(child.bound for child in children) if children else 0
        n.choice_mask = a.choice_mask | b.choice_mask  # TODO: recalculate
        return n
    elif a.letter == b.letter:
        # two sum nodes; merge equivalent children.
        # merge equivalent choices
        choices = {}
        for child in a.children:
            choices[child.cell] = child
        for child in b.children:
            # choices[child.letter] = child
            existing = choices.get(child.cell)
            if existing:
                choices[child.cell] = merge_trees(existing, child)
            else:
                choices[child.cell] = child
        children = [*choices.values()]
        children.sort(key=lambda c: c.cell)

        n = EvalNode()
        n.letter = a.letter
        n.cell = a.cell
        n.children = children
        # assert a.points == b.points, f"{a.cell}/{a.letter}: {a.points} != {b.points}"
        n.points = max(a.points, b.points)  # TODO: why would these ever not match?
        n.trie_node = a.trie_node or b.trie_node  # TODO: check for match
        n.bound = n.points + sum(child.bound for child in children)
        n.choice_mask = a.choice_mask | b.choice_mask  # TODO: recalculate?
        return n
    raise ValueError(
        f"Cannot merge CHOICE_NODE with non-choice: {a.cell}: {a.letter}/{b.letter}"
    )


def cells_from_mask(mask: int) -> list[int]:
    i = 0
    out = []
    while mask:
        if mask % 2:
            out.append(i)
        mask >>= 1
        i += 1
    return out


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
