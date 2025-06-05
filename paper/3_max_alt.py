import sys

from boggle.boggler import SCORES
from boggle.dimensional_bogglers import LEN_TO_DIMS
from boggle.neighbors import NEIGHBORS as ALL_NEIGHBORS
from paper.trie import Trie, make_trie

m = 4
n = 4
NEIGHBORS = ALL_NEIGHBORS[(m, n)]
lookup = None


# Listing 3: Calculating max bound with two mutally recursive functions
def max_bound(board_class: str, trie: Trie) -> int:
    bound = 0
    for i in range(m * n):
        bound += choice_step(board_class, i, trie, {})
    return bound


def choice_step(board_class, idx, parent_node, used):
    max_score = 0
    used[idx] = True
    letters = board_class[idx]
    for letter in letters:
        if parent_node.has_child(letter):
            max_score = max(
                max_score,
                sum_step(board_class, idx, parent_node.child(letter), used),
            )
    used[idx] = False
    return max_score


def sum_step(board_class, idx, trie_node, used):
    score = 0
    if trie_node.is_word():
        score += SCORES[trie_node.length()]
    for n_idx in NEIGHBORS[idx]:
        if not used.get(n_idx):
            score += choice_step(board_class, n_idx, trie_node, used)
    return score


# /Listing


def main():
    t = make_trie("wordlists/enable2k.txt")
    # assert sum_bound("abcdefghijklmnop", t) == 18
    # t.reset_marks()
    board_class = sys.argv[1:]
    global m, n, NEIGHBORS
    m, n = LEN_TO_DIMS[len(board_class)]
    NEIGHBORS = ALL_NEIGHBORS[(m, n)]
    points = max_bound(board_class, t)
    print(f"{board_class}: {points}")
    # poetry run python -m paper.3_max_alt lnrsy chkmpt lnrsy aeiou aeiou aeiou chkmpt lnrsy bdfgjqvwxz
    # ['lnrsy', 'chkmpt', 'lnrsy', 'aeiou', 'aeiou', 'aeiou', 'chkmpt', 'lnrsy', 'bdfgjqvwxz']: 9460


if __name__ == "__main__":
    main()
