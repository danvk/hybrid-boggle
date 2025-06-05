import sys

from boggle.boggler import SCORES
from boggle.dimensional_bogglers import LEN_TO_DIMS
from boggle.neighbors import NEIGHBORS as ALL_NEIGHBORS
from paper.sum_choice_tree import ChoiceNode, SumNode, bound, to_dot
from paper.trie import make_trie

m = 4
n = 4
NEIGHBORS = ALL_NEIGHBORS[(m, n)]
lookup = None

# TODO: import from 3b_max_tree


Path = list[(int, int)]


def find(xs, fn):
    for x in xs:
        if fn(x):
            return x
    return None


# Listing 5: add_word to sum/choice tree
def add_word(node: SumNode, path: Path, points: int):
    if len(path) == 0:
        node.points += points
        return node

    cell, letter = path[0]
    choice_child = find(node.children, lambda c: c.cell == cell)
    if not choice_child:
        choice_child = ChoiceNode(cell=cell)
        node.children.append(choice_child)

    letter_child = choice_child.children.get(letter)
    if not letter_child:
        choice_child.children[letter] = letter_child = SumNode()

    return add_word(letter_child, path[1:], points)


ORDER = [3, 7, 5, 2, 11, 15, 13, 10, 9, 14, 12, 8, 1, 6, 4, 0]


# /Listing


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


def main():
    t = make_trie("wordlists/enable2k.txt")
    # assert sum_bound("abcdefghijklmnop", t) == 18
    # t.reset_marks()
    board_class = sys.argv[1:]
    global m, n, NEIGHBORS
    m, n = LEN_TO_DIMS[len(board_class)]
    NEIGHBORS = ALL_NEIGHBORS[(m, n)]
    tree = build_orderly_tree(board_class, t)
    points = bound(tree)
    sys.stderr.write(f"{board_class}: {points}\n")
    print(to_dot(tree, board_class))
    # poetry run python -m paper.3b_max_tree lnrsy chkmpt lnrsy aeiou aeiou aeiou chkmpt lnrsy bdfgjqvwxz
    # ['lnrsy', 'chkmpt', 'lnrsy', 'aeiou', 'aeiou', 'aeiou', 'chkmpt', 'lnrsy', 'bdfgjqvwxz']: 9460


if __name__ == "__main__":
    main()
