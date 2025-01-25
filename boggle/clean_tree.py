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
from dataclasses import dataclass

from boggle.boggler import LETTER_A, LETTER_Q, SCORES
from boggle.neighbors import NEIGHBORS
from boggle.trie import PyTrie, make_py_trie

type Node = SumNode | ChoiceNode | int


@dataclass
class SumNode:
    points: int
    children: list[Node]

    def to_json(self):
        return {
            "points": self.points,
            "sum": [child.to_json() for child in self.children],
        }

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
    children: list[Node | None]

    def to_json(self):
        return {
            "ch": self.cell,
            "*": {i: child.to_json() for i, child in enumerate(self.children) if child},
        }

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


def lift_choice(node: Node, cell: int, num_lets: int) -> Node:
    if isinstance(node, int):
        return node

    if isinstance(node, ChoiceNode) and node.cell == cell:
        # TODO: eval_tree has compression here
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

    out = []
    for i in range(num_lets):
        # len(children) = len(node.children)
        # len(children[0].children) = num_lets
        children = [
            result.children[i]
            if is_choice[j]
            else result  # <-- this is where subtree duplication happens
            for j, result in enumerate(results)
        ]

        if isinstance(node, ChoiceNode):
            n = ChoiceNode(cell=node.cell, children=children)

        else:
            n = squeeze_sum_node(SumNode(points=node.points, children=children))

        out.append(n)

    return ChoiceNode(cell=cell, children=out)


def squeeze_sum_node(node: SumNode) -> Node | int | None:
    if not node.children:
        return node.points or None
    any_issues = False
    for child in node.children:
        if not child or isinstance(child, (int, SumNode)):
            any_issues = True
            break
    if not any_issues:
        if len(node.children) == 1 and not node.points:
            return node.children[0]
        return node
    new_children = []
    points = node.points
    for child in node.children:
        if child is None:
            continue
        elif isinstance(child, int):
            points += child
        elif isinstance(child, ChoiceNode):
            new_children.append(child)
        else:
            points += child.points
            new_children.extend(child.children)

    if new_children:
        if len(new_children) == 1 and not points:
            return new_children[0]
        return SumNode(children=new_children, points=points)
    return points or None


def eval(node: Node, choices: list[int]):
    if isinstance(node, int):
        return node
    elif isinstance(node, SumNode):
        return node.points + sum(eval(child, choices) for child in node.children)
    elif choices[node.cell] != -1:
        choice = node.children[choices[node.cell]]
        return eval(choice, choices) if choice else 0
    else:
        return max(eval(child, choices) for child in node.children if child)


def eval_all(node: Node, cells: list[str]):
    indices = [range(len(cell)) for cell in cells]
    return {choices: eval(node, choices) for choices in itertools.product(*indices)}


def assert_invariants(node: Node, cells: list[str]):
    """Check a few desirable tree invariants:

    - Sum nodes do not have null children.
    - Choice nodes have the correct number of children.
    - Sum nodes do not have SumNode or int children.
    """
    if isinstance(node, int):
        return
    elif isinstance(node, ChoiceNode):
        assert len(node.children) == len(cells[node.cell])
    elif isinstance(node, SumNode):
        for child in node.children:
            assert child is not None
            assert not isinstance(child, int)
            assert not isinstance(child, SumNode)
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
        dot = [f'{me} [label="choice #{node.cell}"];']
        for i, child in enumerate(node.children):
            if not child:
                continue
            child_id, child_dot = to_dot_help(child, cells, me + str(i))
            letter = cells[node.cell][i]
            dot.append(f'{me} -- {child_id} [label="{letter} ({i})"];')
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
            child = ChoiceNode(cell=i, children=[None] * len(cell))
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
            neighbor = ChoiceNode(cell=ni, children=[None] * len(self.cells[ni]))
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

    sys.stderr.write(f"node count: {t.node_count()}\n")
    with open("tree.dot", "w") as out:
        out.write(to_dot(t, etb.cells))
        out.write("\n")

    # sys.stderr.write("choices at depth:\n")
    # for (cell, depth), value in sorted(t.choices_at_depth().items()):
    #     sys.stderr.write(f"  {cell}@{depth}: {value}\n")
    # sys.stderr.write("\n")

    t1 = lift_choice(t, 1, len(cells[1]))
    sys.stderr.write(f"1 -> node count: {t1.node_count()}\n")
    with open("lift1.dot", "w") as out:
        out.write(to_dot(t1, etb.cells))
        out.write("\n")
    # json.dump(t.to_json(), sys.stdout)


if __name__ == "__main__":
    main()
