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


type char = str

N = n


def record_candidate_board(choices: list[char], bound: int):
    cells = [""] * N
    for cell, choice in zip(SPLIT_ORDER[(m, n)], choices):
        cells[cell] = choice
    bd = "".join(cells)
    print(f"{bound} {bd}")


# Listing 9: orderly_bound
# Assumes N >= 1
# def orderly_bound(root: Orderly(N), S_high: int):
def orderly_bound(root: SumNode, board_class: list[str], S_high: int):
    def step(
        points: int,
        idx: int,
        choices: list[char],  # letters chosen on previous cells
        stack: list[ChoiceNode],
    ):
        b = points + sum(bound(n) for n in stack)
        if b < S_high:
            return  # This board class has been eliminated
        if idx == N:
            # complete board that can't be eliminated
            record_candidate_board(choices, b)
            return

        # Try each letter on the next cell in the canonical order.
        cell = CELL_ORDER[idx]
        for letter in board_class[cell]:
            next_nodes = [n for n in stack if n.cell == cell]
            next_stack = [n for n in stack if n.cell != cell]
            next_points = points
            next_choices = choices + [letter]
            for node in next_nodes:
                letter_node = node.children.get(letter)
                if letter_node:
                    next_stack += letter_node.children
                    next_points += letter_node.points

            step(next_points, idx + 1, next_choices, next_stack)

    step(root.points, 0, [], root.children)


# /Listing


def main():
    t = make_trie("wordlists/enable2k.txt")
    s_high_str, *board_class = sys.argv[1:]
    cutoff = int(s_high_str)
    global m, n, N, NEIGHBORS, ORDER, CELL_ORDER
    m, n = LEN_TO_DIMS[len(board_class)]
    N = m * n
    NEIGHBORS = ALL_NEIGHBORS[(m, n)]
    CELL_ORDER = SPLIT_ORDER[(m, n)]
    ORDER = [0] * (m * n)
    for i, x in enumerate(SPLIT_ORDER[(m, n)]):
        ORDER[x] = m * n - i

    tree = build_orderly_tree(board_class, t)
    points = bound(tree)
    n_nodes = num_nodes(tree)
    sys.stderr.write(f"{board_class}: {points}, {n_nodes=}\n")

    orderly_bound(tree, board_class, cutoff)


if __name__ == "__main__":
    main()


"""
$ time poetry run python -m boggle.orderly_tree_builder 'lnrsy chkmpt lnrsy aeiou aeiou aeiou chkmpt lnrsy bdfgjqvwxz' --python --raw_multiboggle --bound 500 > /tmp/golden.txt
$ time poetry run python -m paper.9_bound 500 lnrsy chkmpt lnrsy aeiou aeiou aeiou chkmpt lnrsy bdfgjqvwxz > /tmp/paper.txt

"""
