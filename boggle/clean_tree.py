"""Clean-room re-implementation of EvalTree.

Goals:

- 2-3 distinct node types, rather than shoe-horning everything into one.
- Dense representation for choice nodes.
- Sum nodes have no identity.
- Fully-squeezed tree, ala https://stackoverflow.com/q/79381817/388951
"""

import itertools
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from boggle.boggler import LETTER_A, LETTER_Q, SCORES
from boggle.breaker import SPLIT_ORDER
from boggle.neighbors import NEIGHBORS
from boggle.trie import PyTrie, make_py_trie

type Node = SumNode | ChoiceNode | int


@dataclass
class SumNode:
    points: int  # TODO: eliminate this
    children: list[Node]

    def node_count(self):
        return 1 + sum(
            0 if isinstance(child, int) else child.node_count()
            for child in self.children
        )

    def choices_at_depth(self, depth=0, out=None):
        if out is None:
            out = {}
        for child in self.children:
            if isinstance(child, int):
                continue
            child.choices_at_depth(depth + 1, out)
        return out

    def has_choice(self, cell: int):
        return any(
            child.has_choice(cell)
            for child in self.children
            if not isinstance(child, int)
        )


@dataclass
class ChoiceNode:
    cell: int
    points: int  # you get these points no matter what
    children: list[Node | None]

    def node_count(self):
        return 1 + sum(
            0 if isinstance(child, int) else child.node_count()
            for child in self.children
            if child
        )

    def choices_at_depth(self, depth=0, out=None):
        if out is None:
            out = {}
        k = (
            self.cell,
            depth,
        )  # TODO: number of non-null choices might be interesting, too
        out[k] = out.get(k, 0) + 1
        for child in self.children:
            if child and not isinstance(child, int):
                child.choices_at_depth(depth + 1, out)
        return out

    def has_choice(self, cell: int):
        if cell == self.cell:
            return True
        return any(
            child.has_choice(cell)
            for child in self.children
            if child and not isinstance(child, int)
        )


def to_json(node: Node):
    if isinstance(node, int):
        return node
    elif isinstance(node, ChoiceNode):
        return {
            "ch": node.cell,
            "points": node.points,
            "*": {i: to_json(child) for i, child in enumerate(node.children) if child},
        }
    elif isinstance(node, SumNode):
        return {
            "points": node.points,
            "sum": [to_json(child) for child in node.children],
        }


def max_bound(node: Node):
    if isinstance(node, int):
        return node
    elif isinstance(node, ChoiceNode):
        children = [c for c in node.children if c]
        return node.points + max(max_bound(child) for child in children)
    elif isinstance(node, SumNode):
        return node.points + sum(max_bound(child) for child in node.children)


def add_scalar(node: Node | None, scalar: int) -> Node:
    if scalar == 0:
        return node
    if node is None:
        return scalar
    elif isinstance(node, int):
        return node + scalar
    elif isinstance(node, SumNode):
        return SumNode(points=node.points + scalar, children=node.children)
    return ChoiceNode(
        points=node.points + scalar, cell=node.cell, children=node.children
    )


def lift_choice(node: Node, cell: int, num_lets: int) -> Node:
    if isinstance(node, int):
        return node

    if isinstance(node, ChoiceNode) and node.cell == cell:
        return node

    if not node.has_choice(cell):
        # TODO: switch to choice_mask here
        return node

    results = [
        lift_choice(child, cell, num_lets) if child else None for child in node.children
    ]
    is_choice = [
        isinstance(result, ChoiceNode) and result.cell == cell for result in results
    ]

    # len(results) = len(node.children)
    # len(results[0].children) = num_lets

    points = 0
    out = []
    to_add = 0
    if isinstance(node, ChoiceNode):
        to_add = node.points

    for i in range(num_lets):
        # len(children) = len(node.children)
        # len(children[0].children) = num_lets
        children = [
            add_scalar(
                result.children[i],
                to_add + (result.points if isinstance(node, ChoiceNode) else 0),
            )
            if is_choice[j]
            else add_scalar(
                result, to_add
            )  # <-- this is where subtree duplication happens
            # ^^^ this makes copies unnecessarily (across range(num_lets))
            for j, result in enumerate(results)
        ]

        if isinstance(node, ChoiceNode):
            if any(children):
                n = squeeze_choice_node(
                    ChoiceNode(points=0, cell=node.cell, children=children)
                )
            else:
                n = None  # can this happen?

        else:
            n = squeeze_sum_node(SumNode(points=node.points, children=children))

        out.append(n)

    if isinstance(node, SumNode):
        for i, result in enumerate(results):
            if is_choice[i]:
                points += result.points

    return squeeze_choice_node(ChoiceNode(points=points, cell=cell, children=out))


def squeeze_sum_node(node: SumNode) -> Node | int | None:
    """This normalizes the SumNode in a few ways to make it more compact.

    Does not mutate node. May return the same node object.
    """
    if not node.children:
        return node.points or None

    # Fast-track for un-problematic nodes.
    # TODO: test whether this is helpful.
    any_issues = False
    choices = set[int]()
    for child in node.children:
        if not child or isinstance(child, (int, SumNode)) or child.cell in choices:
            any_issues = True
            break
        choices.add(child.cell)
    if not any_issues:
        if len(node.children) == 1:
            return add_scalar(node.children[0], node.points)
        return node

    # Fold sum nodes into this one.
    exploded = []
    points = node.points
    for child in node.children:
        if child is None:
            continue
        elif isinstance(child, int):
            points += child
        elif isinstance(child, ChoiceNode):
            exploded.append(child)
        else:
            points += child.points
            exploded.extend(child.children)

    # Look for duplicate choice nodes that can be merged.
    # It's important that this happens _after_ folding in grandchild nodes.
    choices = defaultdict(list)
    for child in exploded:
        assert isinstance(child, ChoiceNode)
        choices[child.cell].append(child)

    # TODO: consider optimizing for common case that there are no dupes
    new_children = []
    for nodes in choices.values():
        if len(nodes) == 1:
            new_children.append(nodes[0])
        else:
            # We own this ChoiceNode, so we're free to mutate it.
            merged = merge_choices(nodes)
            new_children.append(merged)

    if new_children:
        if len(new_children) == 1:
            return add_scalar(new_children[0], points)
        return SumNode(children=new_children, points=points)
    return points or None


def merge_choices(nodes: Sequence[ChoiceNode]) -> ChoiceNode:
    """Merge multiple choice nodes into a single one."""
    out = ChoiceNode(
        points=0,
        cell=nodes[0].cell,
        children=[SumNode(points=0, children=[]) for _ in nodes[0].children],
    )
    for node in nodes:
        assert node.cell == out.cell
        assert len(node.children) == len(out.children)
        out.points += node.points
        for i, choice in enumerate(node.children):
            out.children[i].children.append(choice)
    for i, child in enumerate(out.children):
        out.children[i] = squeeze_sum_node(child)
    return out


def points_on_node(node: Node | None) -> int:
    if node is None:
        return 0
    if isinstance(node, int):
        return node
    return node.points


def squeeze_choice_node(node: ChoiceNode) -> ChoiceNode | int:
    """Pull up the minimum value across the choices."""
    if any(c is None for c in node.children):
        return node  # no minimum to pull up

    min_points = min(points_on_node(c) for c in node.children)
    if min_points == 0:
        return node
    new_children = []
    for child in node.children:
        if isinstance(child, int):
            child = (child - min_points) or None
        elif isinstance(child, SumNode):
            child = SumNode(points=child.points - min_points, children=child.children)
        elif isinstance(child, ChoiceNode):
            child = ChoiceNode(
                points=child.points - min_points,
                cell=child.cell,
                children=child.children,
            )
        new_children.append(child)
    if all(c is None for c in new_children):
        return node.points + min_points
    return ChoiceNode(
        points=node.points + min_points, cell=node.cell, children=new_children
    )


def eval(node: Node, choices: list[int]):
    if isinstance(node, int):
        return node
    elif isinstance(node, SumNode):
        return node.points + sum(eval(child, choices) for child in node.children)
    elif choices[node.cell] != -1:
        choice = node.children[choices[node.cell]]
        return node.points + (eval(choice, choices) if choice else 0)
    else:
        return node.points + max(
            eval(child, choices) for child in node.children if child
        )


def eval_all(node: Node, cells: list[str]):
    indices = [range(len(cell)) for cell in cells]
    return {choices: eval(node, choices) for choices in itertools.product(*indices)}


def assert_invariants(node: Node, cells: list[str]):
    """Check a few desirable tree invariants:

    - Sum nodes do not have null children.
    - Sum nodes do not have SumNode or int children.
    - Sum nodes do not have duplicate ChoiceNode children.
    - Choice nodes have the correct number of children.
    - Choice nodes have at least one choice that leads to points.
    """
    if isinstance(node, int):
        return
    elif isinstance(node, ChoiceNode):
        assert len(node.children) == len(cells[node.cell])
        assert any(node.children)
    elif isinstance(node, SumNode):
        choices = set[int]()
        # TODO: assert >= 2 children
        for child in node.children:
            assert child is not None
            assert not isinstance(child, int)
            assert not isinstance(child, SumNode)
            assert isinstance(child, ChoiceNode)
            assert child.cell not in choices
            choices.add(child.cell)

    for child in node.children:
        if child:
            assert_invariants(child, cells)


def to_dot(node: Node, cells: list[str]) -> str:
    _root_id, dot = to_dot_help(node, cells)
    return f"""graph {{
rankdir=LR;
splines="false";
node [shape="rect"];
{dot}
}}
"""


def to_dot_help(node: Node, cells: list[str], prefix="") -> tuple[str, str]:
    """Returns ID of this node plus DOT for its subtree."""
    me = prefix
    if isinstance(node, int):
        me += "_p"
        return me, f'{me} [label="+{node}" shape="oval"];'

    elif isinstance(node, ChoiceNode):
        me += f"_{node.cell}c"
        points = f"\\n{node.points}" if node.points else ""
        dot = [f'{me} [label="choice #{node.cell}{points}"];']
        for i, child in enumerate(node.children):
            if not child:
                continue
            child_id, child_dot = to_dot_help(child, cells, me + str(i))
            letter = cells[node.cell][i]
            dot.append(f'{me} -- {child_id} [label="{letter}"];')
            dot.append(child_dot)

    else:
        # assert node.children  # otherwise should have been an int
        me += "_s"
        points = f"\\n{node.points}" if node.points else ""
        flags = ""
        if not node.children:
            flags = ' color="red"'
        elif any(isinstance(n, SumNode) for n in node.children):
            flags = ' color="red"'
        elif len(node.children) < 2:
            flags = ' color="red"'
        dot = [f'{me} [label="sum{points}"{flags}];']
        for i, child in enumerate(node.children):
            if not child:
                continue
            child_id, child_dot = to_dot_help(child, cells, me + str(i))
            dot.append(f"{me} -- {child_id};")
            dot.append(child_dot)

    return me, "\n".join(dot)


class TreeBuilder:
    def __init__(self, trie: PyTrie, dims=(3, 3)):
        self.trie = trie
        self.dims = dims
        self.neighbors = NEIGHBORS[dims]

    def build_tree(self, board: str):
        self.used = 0
        self.mark = self.trie.Mark() + 1
        self.trie.SetMark(self.mark)
        self.cells = [cell if cell != "." else "" for cell in board.split(" ")]
        assert len(self.cells) == self.dims[0] * self.dims[1]
        root = SumNode(points=0, children=[])
        for i, cell in enumerate(self.cells):
            child = ChoiceNode(cell=i, children=[None] * len(cell), points=0)
            score = self.make_choices(i, 0, self.trie, child)
            if score > 0:
                if len(cell) > 1:
                    root.children.append(child)
                else:
                    # This isn't really a choice, so don't model it as such.
                    root.children.append(child.children[0])
        return squeeze_sum_node(root)

    def make_choices(self, cell: int, length: int, t: PyTrie, node: ChoiceNode):
        """Fill in the choice node given the choices available on this cell."""
        max_score = 0
        for j, char in enumerate(self.cells[cell]):
            cc = ord(char) - LETTER_A
            if t.StartsWord(cc):
                child = SumNode(children=[], points=0)
                tscore = self.explore_neighbors(
                    cell, length + (2 if cc == LETTER_Q else 1), t.Descend(cc), child
                )
                if tscore > 0:
                    node.children[j] = squeeze_sum_node(child)
                    max_score = max(tscore, max_score)
                else:
                    node.children[j] = None
        return max_score

    def explore_neighbors(self, cell: int, length: int, t: PyTrie, node: SumNode):
        score = 0
        self.used ^= 1 << cell

        for ni in self.neighbors[cell]:
            if self.used & (1 << ni):
                continue
            neighbor = ChoiceNode(
                cell=ni, children=[None] * len(self.cells[ni]), points=0
            )
            neighbor.cell = ni
            tscore = self.make_choices(ni, length, t, neighbor)
            if tscore > 0:
                # squeeze! since this array is dense, this means there's no choice.
                if len(neighbor.children) == 1:
                    neighbor = neighbor.children[0]
                if isinstance(neighbor, SumNode):
                    neighbor = squeeze_sum_node(neighbor)
                node.children.append(neighbor)
                score += tscore

        if t.IsWord():
            word_score = SCORES[length]
            score += word_score
            node.points += word_score

        self.used ^= 1 << cell
        return score


def main():
    # trie = PyTrie()
    # trie.AddWord("tar")
    # trie.AddWord("tie")
    # trie.AddWord("tier")
    # trie.AddWord("tea")
    # trie.AddWord("the")
    # trie = make_py_trie("mini-dict.txt")
    trie = make_py_trie("boggle-words.txt")
    (board,) = sys.argv[1:]
    cells = board.split(" ")
    dims = {
        4: (2, 2),
        9: (3, 3),
        12: (3, 4),
        16: (4, 4),
    }[len(cells)]
    etb = TreeBuilder(trie, dims)
    # board = ". . . . lnrsy e aeiou aeiou ."
    # board = "t i z ae z z r z z"
    t = etb.build_tree(board)
    # print(t)
    assert_invariants(t, cells)

    sys.stderr.write(f"node count: {t.node_count()}, bound={max_bound(t)}\n")

    if True:
        for cell in SPLIT_ORDER[dims]:
            if len(cells[cell]) <= 1:
                continue
            t = lift_choice(t, cell, len(cells[cell]))
            assert_invariants(t, cells)
            sys.stderr.write(
                f"lift {cell} -> node count: {t.node_count()}, bound={max_bound(t)}\n"
            )

    if False:
        with open("tree.dot", "w") as out:
            out.write(to_dot(t, etb.cells))
            out.write("\n")

        # sys.stderr.write("choices at depth:\n")
        # for (cell, depth), value in sorted(t.choices_at_depth().items()):
        #     sys.stderr.write(f"  {cell}@{depth}: {value}\n")
        # sys.stderr.write("\n")

        t4 = lift_choice(t, 4, len(cells[4]))
        sys.stderr.write(f"4 -> node count: {t4.node_count()}\n")
        with open("lift1.dot", "w") as out:
            out.write(to_dot(t4, etb.cells))
            out.write("\n")

        t6 = lift_choice(t4, 6, len(cells[6]))
        sys.stderr.write(f"6 -> node count: {t6.node_count()}\n")
        with open("lift2.dot", "w") as out:
            out.write(to_dot(t6, etb.cells))
            out.write("\n")
        # json.dump(t.to_json(), sys.stdout)


if __name__ == "__main__":
    main()
