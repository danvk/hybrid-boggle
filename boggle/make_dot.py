#!/usr/bin/env python


import argparse
import sys

from boggle.args import add_standard_args
from boggle.dimensional_bogglers import LEN_TO_DIMS
from boggle.eval_node import ChoiceNode, SumNode
from boggle.split_order import SPLIT_ORDER
from boggle.trie import make_py_trie


def to_dot(node: SumNode, cells: list[str], max_depth=100, node_data=None) -> str:
    _root_id, dot = to_dot_help(
        node,
        cells,
        "",
        max_depth,
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
    node: SumNode | ChoiceNode,
    cells: list[str],
    prefix,
    remaining_depth,
    node_data,
    last_cell=None,
) -> tuple[str, str]:
    """Returns ID of this node plus DOT for its subtree."""
    is_dupe = False  # self in cache  # hasattr(self, "flag")
    me = prefix

    if node_data:
        label = str(node_data.get(node, "-"))
    else:
        label = f"{node.bound}"
    attrs = ""
    if is_dupe:
        attrs = 'color="red"'
    if isinstance(node, SumNode) and last_cell is None:
        me += "r"
        attrs += ' penwidth="1"'
    elif isinstance(node, ChoiceNode):
        me += f"_{node.cell}c"
        color = DOT_FILL_COLORS[node.cell]
        attrs += f' style="rounded, filled" fillcolor="{color}"'
    else:
        # This is a SumNode that represents a choice
        me += f"_{last_cell}s"
        attrs += ' penwidth="1"'
        if node.points and node.bound != node.points:
            attrs += ' peripheries="2"'
    dot = [f'{me} [label="{label}"{attrs}];']

    if remaining_depth == 0:
        return me, dot[0]

    last_cell = node.cell if isinstance(node, ChoiceNode) else None
    children = [
        to_dot_help(
            child,
            cells,
            f"{me}{i}",
            remaining_depth - 1,
            node_data,
            last_cell=last_cell,
        )
        for i, child in enumerate(node.children)
    ]

    child_labels = (
        node.get_labeled_children()
        if isinstance(node, ChoiceNode)
        else [(child.cell, child) for child in node.get_children()]
    )

    for (label, _), (child_id, _) in zip(child_labels, children):
        attrs = ""
        if isinstance(node, ChoiceNode) and len(children) < len(cells[node.cell]):
            # incomplete set of choices; label them for clarity.
            attrs = f' [label="{label}"]'
        dot.append(f"{me} -- {child_id}{attrs};")
    for _, child_dot in children:
        dot.append(child_dot)
    return me, "\n".join(dot)


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


def main():
    from boggle.orderly_tree_builder import OrderlyTreeBuilder

    parser = argparse.ArgumentParser(
        prog="DOT renderer",
        description="Visualize what's going on with those trees.",
    )
    # TODO: don't set size, we just need the dictionary
    add_standard_args(parser)
    parser.add_argument("board", type=str, help="Board class to render.")
    args = parser.parse_args()
    trie = make_py_trie(args.dictionary)
    board = args.board

    cells = board.split(" ")
    dims = LEN_TO_DIMS[len(cells)]
    etb = OrderlyTreeBuilder(trie, dims)
    etb.parse_board(board)
    t = etb.build_tree()  # dedupe=False)
    # assert_invariants(t, cells)
    # dedupe_subtrees(t)

    t.orderly_bound(1, cells, SPLIT_ORDER[dims], [])
    # node_counts = t.cache_value
    node_counts = None

    mark = 1

    # t0 = t.children[0]
    # t0t = t0.children[0]
    # t = t0t

    with open("tree.dot", "w") as out:
        # out.write(t.to_dot(cells, max_depth=2))
        out.write(to_dot(t, cells, node_data=node_counts))
        out.write("\n")

    mark += 1
    sys.stderr.write(f"tree.dot node count: {t.node_count()}, bound={t.bound}\n")


if __name__ == "__main__":
    main()
