from paper.trie import Trie


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

    def __init__(self, points: int = 0):
        self.points = points
        self.children = []
        self.trie_node = None


def bound(n: SumNode | ChoiceNode) -> int:
    if isinstance(n, SumNode):
        return n.points + sum(bound(c) for c in n.children)
    elif isinstance(n, ChoiceNode):
        return max(bound(c) for c in n.children.values()) if n.children else 0
    raise ValueError(n)


def num_nodes(n: SumNode | ChoiceNode) -> int:
    children = n.children if isinstance(n, SumNode) else n.children.values()
    return 1 + sum(num_nodes(c) for c in children)


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
        label = f"{node.cell}" if depth > 1 else f"cell={node.cell}"
    else:
        attrs += ' penwidth="1"'
        # if depth == 0:
        #     label = f"bound={b}"
        if node.points:
            word = (
                f"\\n{node.trie_node.word().upper()}"
                if getattr(node, "trie_node")
                else ""
            )
            label = f"+{node.points}{word}"
        else:
            label = "+"

    dot = [f'{me} [label="{label}"{attrs}];']
    b = bound(node)
    bound_label = f"bound={b}" if depth == 0 else f"{b}"
    dot.append(
        f'subgraph cluster_{me} {{ {me}; penwidth="0" margin=0 label="{bound_label}"; labelloc="b"; }}'
    )

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
