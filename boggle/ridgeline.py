"""Find the highest-scoring path between two boards."""

import argparse
import heapq

import networkx as nx
from tqdm import tqdm

from boggle.args import add_standard_args, get_trie_and_boggler_from_args
from boggle.boggler import PyBoggler
from boggle.winner_hierarchy import distance, symmetry_group


def score_intermediates(boggler: PyBoggler, board1: str, board2: str):
    # collect indices of differing letters
    n = len(board1)
    diff_indices = [i for i in range(n) if board1[i] != board2[i]]
    nd = len(diff_indices)
    bd1list = [*board1]

    scores = {}
    for i in tqdm(range(0, 2**nd)):
        bd = [*bd1list]
        for j in range(nd):
            if i & (1 << j):
                dij = diff_indices[j]
                bd[dij] = board2[dij]
        bd_str = "".join(bd)
        scores[bd_str] = boggler.score(bd_str)

    return scores


def make_graph(board1: str, board2: str, scores: dict[str, int]):
    n = len(board1)
    diff_indices = [i for i in range(n) if board1[i] != board2[i]]

    G = nx.Graph()
    for board, score in scores.items():
        G.add_node(board, score=score)

    # Add an edge from each board to the boards an edit distance of 1 away
    for board in tqdm(scores.keys()):
        for i in diff_indices:
            if board[i] == board1[i]:
                other = board[:i] + board2[i] + board[i + 1 :]
                assert len(other) == len(board)
                assert other != board
                G.add_edge(board, other)
            elif board[i] == board2[i]:
                other = board[:i] + board1[i] + board[i + 1 :]
                assert len(other) == len(board)
                assert other != board
                G.add_edge(board, other)
            else:
                raise ValueError(board)

    return G


def highest_scoring_path(G: nx.Graph, start: str, end: str):
    """Returns a sequence of nodes in G representing the shortest path from start to end.

    Amongst all shortest paths, this path will have the maximum value for:
    min(G[node]['score'] for node in path)
    """

    # Use a priority queue to find the best path with the maximum minimum score

    # Priority queue stores (-min_score, current_node, path)
    pq = [(-G.nodes[start]["score"], start, [start])]
    visited = set()

    best_path = None
    best_min_score = float("-inf")

    # TODO: does this return the shortest, then highest path? Or just highest?
    while pq:
        neg_min_score, current, path = heapq.heappop(pq)
        min_score = -neg_min_score

        if current in visited:
            continue
        visited.add(current)

        if current == end:
            if min_score > best_min_score:
                best_min_score = min_score
                best_path = path
            continue

        for neighbor in G.neighbors(current):
            if neighbor not in visited:
                new_min_score = min(min_score, G.nodes[neighbor]["score"])
                heapq.heappush(pq, (-new_min_score, neighbor, path + [neighbor]))

    return best_path


CYELLOW = "\33[33m"
CBOLD = "\33[1m"
CEND = "\33[0m"


def yellow(txt: str):
    return f"{CYELLOW}{CBOLD}{txt}{CEND}"


def color_diffs(board: str, prev: str | None):
    if prev is None:
        return board
    return "".join(a if a == b else yellow(a) for a, b in zip(board, prev))


def main():
    parser = argparse.ArgumentParser(
        prog="Ridgeline",
        description="Find the highest-scoring path between two boards",
    )
    add_standard_args(parser, random_seed=False, python=True)
    parser.add_argument("board1", type=str, help="Start board")
    parser.add_argument("board2", type=str, help="Destination board")
    args = parser.parse_args()
    _, boggler = get_trie_and_boggler_from_args(args)

    board1 = args.board1
    board2 = min(symmetry_group(args.board2), key=lambda b: distance(board1, b))

    if board2 != args.board2:
        print(f"Rotated {args.board2} -> {board2}")

    d = distance(board1, board2)
    print(f"d({board1}, {board2}) = {d}")

    scores = score_intermediates(boggler, board1, board2)
    print(f"Scored {len(scores)} intermediate boards.")

    G = make_graph(board1, board2, scores)
    print(f"{G.number_of_nodes()=} {G.number_of_edges()=}")

    path = highest_scoring_path(G, board1, board2)
    prev = None
    for board in path:
        print(f"{color_diffs(board, prev)}\t{scores[board]}")
        prev = board


if __name__ == "__main__":
    main()
