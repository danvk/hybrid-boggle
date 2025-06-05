import sys

from boggle.boggler import SCORES
from boggle.dimensional_bogglers import LEN_TO_DIMS
from boggle.neighbors import NEIGHBORS as ALL_NEIGHBORS
from paper.trie import Trie, make_trie

m = 4
n = 4
NEIGHBORS = ALL_NEIGHBORS[(m, n)]
lookup = None


# Listing 4: Build+Force operation on Tree
def forced_tree(board_class, board, trie):
    bound = 0
    for i in range(m * n):
        bound += choice_step(board_class, board, i, trie, {})
    return bound


def choice_step(board_class, board, idx, parent_node, used):
    score = 0
    used[idx] = True
    letter = board[idx]
    if parent_node.has_child(letter):
        score = sum_step(board_class, board, idx, parent_node.child(letter), used)
    used[idx] = False
    return score


def sum_step(board_class, board, idx, trie_node, used):
    score = 0
    if trie_node.is_word():
        score += SCORES[trie_node.length()]
        print(f"+{score}: {trie_node.word()}")
    for n_idx in NEIGHBORS[idx]:
        if not used.get(n_idx):
            score += choice_step(board_class, board, n_idx, trie_node, used)
    return score


# /Listing


def main():
    t = make_trie("wordlists/enable2k.txt")
    # assert sum_bound("abcdefghijklmnop", t) == 18
    # t.reset_marks()
    board, *board_class = sys.argv[1:]
    global m, n, NEIGHBORS
    m, n = LEN_TO_DIMS[len(board)]
    NEIGHBORS = ALL_NEIGHBORS[(m, n)]
    points = forced_tree(board_class, board, t)
    print(f"{board_class} -> {board}: {points}")
    # poetry run python -m paper.4_force aceh x
    # ['x'] -> aceh: 4
    # poetry run python -m paper.4_force beef x
    # ['x'] -> beef: 6
    # poetry run python -m paper.4_force eebfee x
    # ['x'] -> eebfee: 12


if __name__ == "__main__":
    main()
