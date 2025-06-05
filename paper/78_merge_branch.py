import sys

from boggle.boggler import SCORES
from boggle.dimensional_bogglers import LEN_TO_DIMS
from boggle.neighbors import NEIGHBORS as ALL_NEIGHBORS
from boggle.split_order import SPLIT_ORDER
from paper.sum_choice_tree import ChoiceNode, SumNode, bound, num_nodes, to_dot
from paper.trie import make_trie

m = 4
n = 4
NEIGHBORS = ALL_NEIGHBORS[(m, n)]
lookup = None

Path = list[(int, int)]


def find(xs, fn):
    for x in xs:
        if fn(x):
            return x
    return None


def add_word(node: SumNode, path: Path, points: int):
    if len(path) == 0:
        node.points += points
        return node

    cell, letter = path[0]
    choice_child = find(node.children, lambda c: c.cell == cell)
    if not choice_child:
        choice_child = ChoiceNode(cell=cell)
        node.children.append(choice_child)
        node.children.sort(key=lambda c: -ORDER[c.cell])

    letter_child = choice_child.children.get(letter)
    if not letter_child:
        choice_child.children[letter] = letter_child = SumNode()

    return add_word(letter_child, path[1:], points)


ORDER = SPLIT_ORDER[(4, 4)]


def build_orderly_tree(board_class, trie):
    root = SumNode()
    for i in range(m * n):
        choice_step(board_class, i, trie, [], root)
    return root


def choice_step(board_class, idx, trie_node, choices, root):
    letters = board_class[idx]
    for letter in letters:
        if trie_node.has_child(letter):
            choices.append((idx, letter))
            sum_step(board_class, idx, trie_node.child(letter), choices, root)
            choices.pop()


def sum_step(board_class, idx, trie_node, choices, root):
    if trie_node.is_word():
        ordered_choices = sorted(choices, key=lambda c: -ORDER[c[0]])
        score = SCORES[trie_node.length()]
        add_word(root, ordered_choices, score)
    for n_idx in NEIGHBORS[idx]:
        if n_idx not in (cell for cell, _letter in choices):
            choice_step(board_class, n_idx, trie_node, choices, root)


def group_by(xs, fn):
    d = {}
    for x in xs:
        v = fn(x)
        d.setdefault(v, [])
        d[v].append(x)
    return [*d.values()]


# Listing 7: merge operation on orderly trees
# def merge(a: Orderly(N), b: Orderly(N)) -> Orderly(N):
def merge(a: SumNode, b: SumNode) -> SumNode:
    cell_to_child = {c.cell: c for c in a.children}
    for bc in b.children:
        ac = cell_to_child.get(bc.cell)
        cell_to_child[bc.cell] = merge_choice(ac, bc) if ac else bc
    children = sorted(cell_to_child.values(), key=lambda c: -ORDER[c.cell])
    return SumNode(points=a.points + b.points, children=children)


# def merge_choice(a: OrderlyChoice(N), b: OrderlyChoice(N)) -> OrderlyChoice(N):
def merge_choice(a: ChoiceNode, b: ChoiceNode) -> ChoiceNode:
    children = {**a.children}
    for choice, bc in b.children.items():
        ac = children.get(choice)
        children[choice] = merge(ac, bc) if ac else bc
    return ChoiceNode(cell=a.cell, children=children)


# /Listing


# Listing 8: branch operation on orderly trees
# def branch(o: Orderly(N)) -> list(Orderly(N-1)):
def branch(o: SumNode, top_cell: int, board_class: list[str]) -> list[SumNode]:
    top_choice = o.children[0]
    if top_choice.cell != top_cell:
        # edge case: the choice on the top cell is irrelevant, so o is Orderly(N-1).
        return [o for _letter in board_class[top_cell]]

    other_choices = o.children[1:]
    skip_tree = SumNode(children=other_choices, points=o.points)  # Orderly(N-1)
    return [
        merge(top_choice.children[letter], skip_tree)  # both are Orderly(N-1)
        if top_choice.children.get(letter)
        else skip_tree  # no words use this letter on the top choice cell
        for letter in board_class[top_cell]
    ]


# /Listing


def main():
    t = make_trie("wordlists/enable2k.txt")
    # assert sum_bound("abcdefghijklmnop", t) == 18
    # t.reset_marks()
    board_class = sys.argv[1:]
    global m, n, NEIGHBORS, ORDER
    m, n = LEN_TO_DIMS[len(board_class)]
    NEIGHBORS = ALL_NEIGHBORS[(m, n)]
    split_order = SPLIT_ORDER[(m, n)]
    ORDER = [0] * (m * n)
    for i, x in enumerate(split_order):
        ORDER[x] = m * n - i
    tree = build_orderly_tree(board_class, t)
    points = bound(tree)
    n_nodes = num_nodes(tree)
    sys.stderr.write(f"{board_class}: {points}, {n_nodes=}\n")

    cell = split_order[0]
    subtrees = branch(tree, cell, board_class)
    assert len(subtrees) == len(board_class[cell])
    for letter, subtree in zip(board_class[cell], subtrees):
        b = bound(subtree)
        n = num_nodes(subtree)
        print(f"  {cell=} {letter=} bound={b} num_nodes={n}")

    # print(to_dot(tree, board_class))
    # poetry run python -m paper.3b_max_tree lnrsy chkmpt lnrsy aeiou aeiou aeiou chkmpt lnrsy bdfgjqvwxz
    # ['lnrsy', 'chkmpt', 'lnrsy', 'aeiou', 'aeiou', 'aeiou', 'chkmpt', 'lnrsy', 'bdfgjqvwxz']: 9460


if __name__ == "__main__":
    main()

"""
Compare:

$ time poetry run python -m boggle.orderly_tree_builder 'lnrsy chkmpt lnrsy aeiou aeiou aeiou chkmpt lnrsy bdfgjqvwxz' --force --python --raw_multiboggle
1.56s OrderlyTreeBuilder: t.bound=1523, 333492 nodes
  cell=4 letter='a' t.bound=1198, 86420 nodes
  cell=4 letter='e' t.bound=1417, 98585 nodes
  cell=4 letter='i' t.bound=994, 81062 nodes
  cell=4 letter='o' t.bound=862, 75474 nodes
  cell=4 letter='u' t.bound=753, 60457 nodes
poetry run python -m boggle.orderly_tree_builder  --force --python   2.77s user 0.08s system 95% cpu 2.984 total

$ time poetry run python -m paper.78_merge_branch lnrsy chkmpt lnrsy aeiou aeiou aeiou chkmpt lnrsy bdfgjqvwxz
['lnrsy', 'chkmpt', 'lnrsy', 'aeiou', 'aeiou', 'aeiou', 'chkmpt', 'lnrsy', 'bdfgjqvwxz']: 1523, n_nodes=333492
  cell=4 letter='a' bound=1198 num_nodes=86420
  cell=4 letter='e' bound=1417 num_nodes=98585
  cell=4 letter='i' bound=994 num_nodes=81062
  cell=4 letter='o' bound=862 num_nodes=75474
  cell=4 letter='u' bound=753 num_nodes=60457
poetry run python -m paper.78_merge_branch lnrsy chkmpt lnrsy aeiou aeiou      3.59s user 0.08s system 96% cpu 3.806 total

"""
