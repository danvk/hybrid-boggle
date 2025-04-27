"""Find the highest-scoring path between two boards."""

import argparse

from boggle.args import add_standard_args, get_trie_and_boggler_from_args
from boggle.winner_hierarchy import closest, distance, symmetry_group


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


if __name__ == "__main__":
    main()
