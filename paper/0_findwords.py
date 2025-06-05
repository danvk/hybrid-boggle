import sys

from boggle.boggler import SCORES
from boggle.neighbors import NEIGHBORS as ALL_NEIGHBORS
from paper.trie import Trie, make_lookup_table, make_trie

m = 4
n = 4
NEIGHBORS = ALL_NEIGHBORS[(m, n)]
lookup = None


# Listing 0: Scoring a Boggle Board
def score(board: str, trie: Trie) -> int:
    score = 0
    for i in range(m * n):
        score += score_dfs(board, i, trie.child(board[i]), {})
    return score


def score_dfs(board: str, idx: int, trie_node: Trie, used) -> int:
    score = 0
    used[idx] = True
    if trie_node.is_word() and not trie_node.is_visited():
        print(f"{lookup[trie_node]}: {trie_node.length()}")
        score += SCORES[trie_node.length()]
        trie_node.set_visited()
    for n_idx in NEIGHBORS[idx]:
        if not used.get(n_idx) and trie_node.has_child(board[n_idx]):
            score += score_dfs(board, n_idx, trie_node.child(board[n_idx]), used)
    used[idx] = False
    return score


# /Listing


def main():
    global lookup
    t = make_trie("wordlists/enable2k.txt")
    lookup = make_lookup_table(t)
    (board,) = sys.argv[1:]
    points = score(board, t)
    print(f"{board}: {points}")


if __name__ == "__main__":
    main()
