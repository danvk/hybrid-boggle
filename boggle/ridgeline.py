"""Find the highest-scoring path between two boards."""

import argparse

from tqdm import tqdm

from boggle.args import add_standard_args, get_trie_and_boggler_from_args
from boggle.boggler import PyBoggler
from boggle.winner_hierarchy import distance, symmetry_group


def score_intermediates(boggler: PyBoggler, board1: str, board2: str):
    # collect inidices of differing letters
    n = len(board1)
    diff_indices = [i for i in range(n) if board1[i] != board2[i]]
    nd = len(diff_indices)
    print(f"{nd=} {diff_indices=}")
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


if __name__ == "__main__":
    main()
