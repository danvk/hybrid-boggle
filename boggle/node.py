import json
import sys
from dataclasses import dataclass

type Node = SumNode | ChoiceNode | PointNode


@dataclass
class SumNode:
    children: list[Node]

    def to_json(self):
        return {
            "sum": [child.to_json() for child in self.children],
        }

    def node_count(self):
        return 1 + sum(child.node_count() for child in self.children)

    def max_bound(self):
        return sum(child.max_bound() for child in self.children)

    def depth(self):
        return 1 + max(child.depth() for child in self.children)

    def eval(self, choices: dict[int, int]) -> int:
        return sum(child.eval(choices) for child in self.children)


@dataclass
class PointNode:
    points: int

    def to_json(self):
        return self.points

    def node_count(self):
        return 1

    def max_bound(self):
        return self.points

    def depth(self):
        return 1

    def eval(self, choices: dict[int, int]) -> int:
        return self.points


@dataclass
class ChoiceNode:
    cell: int
    children: list[Node]

    def to_json(self):
        return {
            "ch": self.cell,
            "*": {i: child.to_json() for i, child in enumerate(self.children) if child},
        }

    def node_count(self):
        return 1 + sum(child.node_count() for child in self.children if child)

    def max_bound(self):
        return max(child.max_bound() for child in self.children if child)

    def depth(self):
        return 1 + max(child.depth() for child in self.children if child)

    def eval(self, choices: dict[int, int]) -> int:
        choice = choices.get(self.cell)
        if choice is None:
            return max(child.eval(choices) for child in self.children if child)
        else:
            child = self.children[choice] if choice < len(self.children) else None
            return child.eval(choices) if child else 0


def from_json(v) -> Node:
    if isinstance(v, int):
        return PointNode(points=v)
    elif "sum" in v:
        return SumNode(children=[from_json(c) for c in v["sum"]])
    assert "ch" in v
    m = max(int(k) for k in v["*"].keys())
    children = [None for _ in range(m + 1)]
    for k, c in v["*"].items():
        children[int(k)] = from_json(c)
    return ChoiceNode(cell=v["ch"], children=children)


def main():
    (input_file,) = sys.argv[1:]
    data = json.load(open(input_file))

    node = from_json(data)
    print(f"Loaded {node.node_count()} nodes")
    print(f"Tree depth: {node.depth()}")
    print(f"Upper bound: {node.max_bound()}")

    choices = [5, 0, 4, 5, 1, 2, 3, 1, 1]
    score = node.eval({i: v for i, v in enumerate(choices)})
    print(f"{choices} -> {score}")


if __name__ == "__main__":
    main()
