# Try to speed up ibuckets by explicitly constructing an evaluation tree.

import math
from collections import Counter, defaultdict
from typing import Callable, Self, Sequence

from boggle.boggler import LETTER_A, LETTER_Q, SCORES
from boggle.ibuckets import PyBucketBoggler, ScoreDetails
from boggle.trie import PyTrie

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
        choice_mask = 0
        for cell, letter in enumerate(forces):
            if letter >= 0:
                choice_mask |= 1 << cell
        return self.score_with_forces_mask(forces, choice_mask)

    def score_with_forces_mask(self, forces: list[int], choice_mask: int) -> int:
        if self.letter == CHOICE_NODE:
            force = forces[self.cell]
            if force >= 0:
                for child in self.children:
                    if child and child.letter == force:
                        return child.score_with_forces_mask(forces, choice_mask)
                return 0

        if not (self.choice_mask & choice_mask):
            # The force is irrelevant to this subtree, so we don't need to traverse it.
            return self.bound

        # Otherwise, this is the same as regular scoring
        if self.letter == CHOICE_NODE:
            return (
                max(
                    child.score_with_forces_mask(forces, choice_mask) if child else 0
                    for child in self.children
                )
                if self.children
                else 0
            )
        else:
            return self.points + sum(
                child.score_with_forces_mask(forces, choice_mask) if child else 0
                for child in self.children
            )

    def force_cell(self, force_cell: int, num_lets: int) -> Self | list[Self]:
        """Try each possibility for a cell.

        num_lets is the number of possibilities for the cell.
        Returns a list of trees, one for each letter, or a Tree if there's no choice.
        """
        # COUNTS["force calls"] += 1
        if self.letter == CHOICE_NODE and self.cell == force_cell:
            # This is the forced cell.
            # We've already tried each possibility, but they may not be aligned.
            out = [None] * num_lets
            for child in self.children:
                if child:
                    # If this choice isn't a word on its own and it only has one child,
                    # then we can remove it from the tree entirely.
                    letter = child.letter
                    if not child.points and len(child.children) == 1:
                        child = child.children[0]
                    out[letter] = child
                    assert child.choice_mask & (1 << force_cell) == 0
            return out

        if self.choice_mask & (1 << force_cell) == 0:
            # There's no relevant choice below us, so we can bottom out.
            return self

        # Make the recursive calls and align the results.
        # For a choice node, take the max. For other nodes, take the sum.
        results = [
            child.force_cell(force_cell, num_lets) if child else None
            for child in self.children
        ]

        aligned_results = [
            r if isinstance(r, list) else [r] * num_lets for r in results
        ]
        # Construct a new choice node for each forced letter.
        out = []
        for i in range(num_lets):
            children = [result[i] for result in aligned_results if result[i]]
            node_choice_mask = 0
            if self.letter == CHOICE_NODE:
                node_bound = max(child.bound for child in children) if children else 0
                node_choice_mask = (1 << self.cell) & self.choice_mask
            else:
                node_bound = self.points + sum(child.bound for child in children)
                if MERGE_AFTER_SPLIT:
                    if children and len(children) > 1:
                        # This groups twice because almost all the time there are no collisions.
                        by_cell = {}
                        any_collisions = False
                        for child in children:
                            if by_cell.get(child.cell):
                                any_collisions = True
                                break
                            by_cell[child.cell] = True
                        if any_collisions:
                            # COUNTS["MERGE"] += 1
                            by_cell = defaultdict(list)
                            for c in children:
                                by_cell[c.cell].append(c)
                            children = []
                            for letter, trees in by_cell.items():
                                if len(trees) == 1:
                                    children.append(trees[0])
                                else:
                                    child = trees[0]
                                    for c in trees[1:]:
                                        child = merge_trees(child, c)
                                    children.append(child)
                            children.sort(key=lambda c: c.cell)
                            node_bound = self.points + sum(
                                child.bound for child in children
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
                for child in children:
                    node.choice_mask |= child.choice_mask
                # assert node.choice_mask == self.choice_mask
                # if len(node.children) == 1 and node.letter >= 0 and node.points == 0:
                #     node = node.children[0]
            else:
                node = None

            out.append(node)
        return out

    def prune(self):
        if self.bound == 0 and self.letter != ROOT_NODE:
            return False  # discard
        new_children = [child for child in self.children if child and child.prune()]
        self.children = new_children
        return True  # keep

    def compress(self):
        if (
            self.letter >= 0
            and len(self.children) == 1
            and self.children[0]
            and self.children[0].letter >= 0
            and not self.children[0].points
        ):
            self.children = self.children[0].children
        for child in self.children:
            child.compress()
        return self

    def node_count(self):
        return 1 + sum(child.node_count() for child in self.children if child)

    def _into_list(self, solver: PyBucketBoggler, lines: list[str], indent=""):
        line = ""
        if self.letter == ROOT_NODE:
            line = f"ROOT ({self.bound}) mask={self.choice_mask}"
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

    def to_json(self, solver: PyBucketBoggler, max_depth=100):
        out = {
            "type": (
                "ROOT"
                if self.letter == ROOT_NODE
                else "CHOICE"
                if self.letter == CHOICE_NODE
                else f"{self.letter}={solver.bd_[self.cell][self.letter]}"
            ),
            "cell": self.cell,
            "bound": self.bound,
            "mask": [i for i in range(16) if self.choice_mask & (1 << i)],
        }
        if self.points:
            out["points"] = self.points
        if self.children:
            child_range = [child.bound for child in self.children]
            child_range.sort()
            out["child_bound_range"] = child_range
            out["num_reps"] = num_possibilities(self.choice_letters())
            if max_depth == 0:
                out["children"] = self.node_count()
            else:
                out["children"] = [
                    child.to_json(solver, max_depth - 1) for child in self.children
                ]
        return out


def group_by[T, R](seq: Sequence[T], fn: Callable[[T], R]) -> dict[R, list[T]]:
    out = dict[R, list[T]]()
    for v in seq:
        k = fn(v)
        out.setdefault(k, [])
        out[k].append(v)
    return out


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

    def BuildTree(self):
        root = EvalNode()
        self.root = root
        root.letter = ROOT_NODE
        root.cell = 0  # irrelevant
        root.points = 0
        self.details_ = ScoreDetails(0, 0, -1)
        self.used_ = 0
        self.runs_ += 1

        for i in range(len(self.bd_)):
            child = EvalNode()
            child.letter = CHOICE_NODE
            child.cell = i
            score = self.DoAllDescents(i, 0, self.trie_, child)
            if score > 0:
                self.details_.max_nomark += score
                root.children.append(child)
                root.choice_mask |= child.choice_mask
        root.bound = self.details_.max_nomark
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
