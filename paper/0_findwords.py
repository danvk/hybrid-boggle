import sys

from boggle.boggler import SCORES
from boggle.neighbors import NEIGHBORS as ALL_NEIGHBORS
from paper.trie import Trie, make_trie

m = 4
n = 4
NEIGHBORS = ALL_NEIGHBORS[(m, n)]


# Listing 0: Scoring a Boggle Board
def score(board: str, trie: Trie) -> int:
    score = 0
    for i in range(m * n - 1):
        score += score_dfs(board, i, trie, {})
    return score


def score_dfs(board: str, idx: int, parent_node: Trie, used) -> int:
    score = 0
    used[idx] = True
    if parent_node.has_child(board[idx]):
        trie_node = parent_node.child(board[idx])
        if trie_node.is_word() and not trie_node.is_visited():
            score += SCORES[trie_node.length()]
            trie_node.set_visited()
        for n_idx in NEIGHBORS[idx]:
            if not used.get(n_idx):
                score += score_dfs(board, n_idx, trie_node, used)
    used[idx] = False
    return score


# /Listing


def main():
    t = make_trie("wordlists/enable2k.txt")
    (board,) = sys.argv[1:]
    points = score(board, t)
    print(f"{board}: {points}")


if __name__ == "__main__":
    main()
