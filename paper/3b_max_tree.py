import sys

from boggle.boggler import SCORES
from boggle.dimensional_bogglers import LEN_TO_DIMS
from boggle.neighbors import NEIGHBORS as ALL_NEIGHBORS
from paper.sum_choice_tree import ChoiceNode, SumNode, bound, num_nodes, to_dot
from paper.trie import Trie, make_trie

m = 4
n = 4
NEIGHBORS = ALL_NEIGHBORS[(m, n)]
lookup = None


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


# /Listing


def main():
    t = make_trie("wordlists/enable2k.txt")
    # assert sum_bound("abcdefghijklmnop", t) == 18
    # t.reset_marks()
    board_class = sys.argv[1:]
    global m, n, NEIGHBORS
    m, n = LEN_TO_DIMS[len(board_class)]
    NEIGHBORS = ALL_NEIGHBORS[(m, n)]
    tree = build_tree(board_class, t)
    points = bound(tree)
    n_nodes = num_nodes(tree)
    sys.stderr.write(f"{board_class}: {points}, {n_nodes=}\n")
    print(to_dot(tree, board_class))
    # poetry run python -m paper.3b_max_tree lnrsy chkmpt lnrsy aeiou aeiou aeiou chkmpt lnrsy bdfgjqvwxz
    # ['lnrsy', 'chkmpt', 'lnrsy', 'aeiou', 'aeiou', 'aeiou', 'chkmpt', 'lnrsy', 'bdfgjqvwxz']: 9460


if __name__ == "__main__":
    main()
