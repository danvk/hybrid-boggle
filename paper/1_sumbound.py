import sys

from boggle.boggler import SCORES
from boggle.dimensional_bogglers import LEN_TO_DIMS
from boggle.neighbors import NEIGHBORS as ALL_NEIGHBORS
from paper.trie import Trie, make_trie

m = 4
n = 4
NEIGHBORS = ALL_NEIGHBORS[(m, n)]
lookup = None


# Listing 1: Calcluating sum bound on a Boggle board class
def sum_bound(board_class: list[str], trie: Trie) -> int:
    score = 0
    for i in range(m * n):
        score += sum_bound_dfs(board_class, i, trie, {})
    return score


def sum_bound_dfs(board_class: str, idx: int, parent_node: Trie, used) -> int:
    score = 0
    used[idx] = True
    letters = board_class[idx]
    for letter in letters:
        if parent_node.has_child(letter):
            trie_node = parent_node.child(letter)
            if trie_node.is_word() and not trie_node.is_visited():
                score += SCORES[trie_node.length()]
                trie_node.set_visited()
            for n_idx in NEIGHBORS[idx]:
                if not used.get(n_idx):
                    score += sum_bound_dfs(board_class, n_idx, trie_node, used)
    used[idx] = False
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
    points = sum_bound(board_class, t)
    print(f"{board_class}: {points}")
    # poetry run python -m paper.1_sumbound lnrsy chkmpt lnrsy aeiou aeiou aeiou chkmpt lnrsy bdfgjqvwxz
    # 109524


if __name__ == "__main__":
    main()
