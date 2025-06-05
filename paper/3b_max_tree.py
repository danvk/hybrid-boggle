import sys
from dataclasses import dataclass

from boggle.boggler import SCORES
from boggle.dimensional_bogglers import LEN_TO_DIMS
from boggle.neighbors import NEIGHBORS as ALL_NEIGHBORS
from paper.trie import Trie, make_trie

m = 4
n = 4
NEIGHBORS = ALL_NEIGHBORS[(m, n)]
lookup = None


"""
Node := SumNode | ChoiceNode

ChoiceNode:
  cell: int
  children: {letter -> SumNode}

SumNode:
	points: int
	children: ChoiceNode[]
"""


class ChoiceNode:
    cell: int
    children: dict[str, "SumNode"]

    def __init__(self, cell: int):
        self.cell = cell
        self.children = {}


class SumNode:
    points: int = 0
    children: list[ChoiceNode]
    trie_node: Trie

    def __init__(self, points: int):
        self.points = points
        self.children = []
        self.trie_node = None


# Listing 3b: Calculating max bound with a tree
def build_tree(board_class: str, trie: Trie) -> SumNode:
    root = SumNode(points=0)
    for i in range(m * n):
        root.children.append(choice_step(board_class, i, trie, {}))
    return root


def choice_step(board_class, idx, parent_node, used) -> ChoiceNode:
    node = ChoiceNode(cell=idx)
    used[idx] = True
    letters = board_class[idx]
    for letter in letters:
        if parent_node.has_child(letter):
            n = sum_step(board_class, idx, parent_node.child(letter), used)
            if bound(n):
                node.children[letter] = n
    used[idx] = False
    return node


def sum_step(board_class, idx, trie_node, used) -> SumNode:
    node = SumNode(points=0)
    if trie_node.is_word():
        node.points = SCORES[trie_node.length()]
        node.trie_node = trie_node
    for n_idx in NEIGHBORS[idx]:
        if not used.get(n_idx):
            n = choice_step(board_class, n_idx, trie_node, used)
            if bound(n):
                node.children.append(n)
    return node


def bound(n: SumNode | ChoiceNode) -> int:
    if isinstance(n, SumNode):
        return n.points + sum(bound(c) for c in n.children)
    elif isinstance(n, ChoiceNode):
        return max(bound(c) for c in n.children.values()) if n.children else 0
    raise ValueError(n)


# /Listing


def to_dot(node: SumNode, cells: list[str]):
    _root_id, dot = to_dot_help(node, cells, "r", 0)
    return f"""graph {{
rankdir=LR;
nodesep=0.1;
node [shape="rect" penwidth="0" fontname="Comic Sans MS"];
edge [fontname="Comic Sans MS"];
{dot}
}}
"""


def to_dot_help(
    node: SumNode | ChoiceNode,
    cells: list[str],
    prefix: str,
    depth: int,
) -> tuple[str, str]:
    me = prefix
    attrs = ""
    b = bound(node)
    label = f"{b}"
    if isinstance(node, ChoiceNode):
        me += f"_{node.cell}"
        attrs += ' style="rounded, filled"'
    else:
        attrs += ' penwidth="1"'
        if depth == 0:
            label = f"bound={b}"

    dot = [f'{me} [label="{label}"{attrs}];']
    # b = bound(node)
    # bound_label = f"bound={b}" if depth == 0 else f"{b}"
    # dot.append(
    #     f'subgraph cluster_{me} {{ {me}; penwidth="0" margin=0 label="{bound_label}"; labelloc="b"; }}'
    # )

    if isinstance(node, ChoiceNode):
        for letter, child in sorted(node.children.items()):
            child_id, child_dot = to_dot_help(child, cells, f"{me}{letter}", depth + 1)
            dot.append(child_dot)
            dot.append(f'{me} -- {child_id} [label="{letter.upper()}"]')
    else:
        for i, child in enumerate(node.children):
            child_id, child_dot = to_dot_help(child, cells, f"{me}{i}", depth + 1)
            dot.append(child_dot)
            dot.append(f"{me} -- {child_id}")

    return me, "\n".join(dot)


def main():
    t = make_trie("wordlists/enable2k.txt")
    # assert sum_bound("abcdefghijklmnop", t) == 18
    # t.reset_marks()
    board_class = sys.argv[1:]
    global m, n, NEIGHBORS
    m, n = LEN_TO_DIMS[len(board_class)]
    NEIGHBORS = ALL_NEIGHBORS[(m, n)]
    tree = build_tree(board_class, t)
    # points = bound(tree)
    # print(f"{board_class}: {points}")
    print(to_dot(tree, board_class))
    # poetry run python -m paper.3b_max_tree lnrsy chkmpt lnrsy aeiou aeiou aeiou chkmpt lnrsy bdfgjqvwxz
    # ['lnrsy', 'chkmpt', 'lnrsy', 'aeiou', 'aeiou', 'aeiou', 'chkmpt', 'lnrsy', 'bdfgjqvwxz']: 9460


if __name__ == "__main__":
    main()
