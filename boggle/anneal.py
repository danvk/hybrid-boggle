"""Find high-scoring Boggle boards via simulated annealing.

Ported from https://github.com/danvk/performance-boggle/blob/master/anneal.cc
"""

import argparse
import math
import random
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from boggle.args import add_standard_args, get_trie_and_boggler_from_args
from boggle.boggler import LETTER_A, LETTER_Z, PyBoggler


@dataclass
class Options:
    cool_t0: float = 100.0
    cool_k: float = 0.05
    swap_ratio: float = 1.0
    mutation_p: float = 0.75
    max_stall: int = 2000


A_TO_Z = [*range(LETTER_A, LETTER_Z + 1)]


def initial_board(num_lets: int, letters: Sequence[int]) -> list[int]:
    return [random.choice(letters) for _ in range(num_lets)]


# TODO: make this operate on strings like hillclimb.neighbors
def mutate(board: list[int], opts: Options):
    num_cells = len(board)
    while True:
        if (1 + opts.swap_ratio) * random.random() > 1.0:
            # swap two cells
            while True:
                a = random.randint(0, num_cells - 1)
                b = random.randint(0, num_cells - 1)
                if a != b:
                    break
            board[a], board[b] = board[b], board[a]
        else:
            # change a cell
            while True:
                cell = random.randint(0, num_cells - 1)
                letter = random.randint(LETTER_A, LETTER_Z)
                if board[cell] != letter:
                    break
            board[cell] = letter

        if random.random() < opts.mutation_p:
            break


def accept_transition(cur_score: int, new_score: int, T: float) -> bool:
    """Should we transition between boards with these two scores?"""
    if new_score > cur_score:
        return True
    if T < 1e-20:
        return False
    p = math.exp((new_score - cur_score) / T)
    return random.random() < p


def temperature(n: int, opts: Options) -> float:
    """The "temperature" after n iterations"""
    return opts.cool_t0 * math.exp(-opts.cool_k * n)


def anneal(boggler: PyBoggler, num_lets: int, opts: Options):
    last_board = initial_board(num_lets, A_TO_Z)
    best_score = 0
    last_accept = 0

    n = 0
    while n < last_accept + opts.max_stall:
        n += 1
        board = [*last_board]
        mutate(board, opts)
        # TODO: could just pass the list; or mutate the boggler
        board_str = "".join(chr(x) for x in board)
        score = boggler.score(board_str)
        T = temperature(n, opts)
        if accept_transition(best_score, score, T):
            last_accept = n
            best_score = score
            last_board = board

    board_str = "".join(chr(x) for x in last_board)
    return (best_score, board_str, n)


def main():
    parser = argparse.ArgumentParser(
        prog="Simulated annealing",
        description="Find high-scoring Boggle boards using simulated annealing",
    )
    parser.add_argument(
        "num_boards",
        type=int,
        default=100,
        help="Number of high-scoring boards to find before quitting.",
    )
    parser.add_argument(
        "--swap_ratio",
        type=float,
        default=1.0,
        help="Ratio of swaps to letter changes. 1.0=50/50, 0.0=no swaps.",
    )
    parser.add_argument(
        "--max_stall",
        type=int,
        default=2000,
        help="Reset after this many iterations without improvement.",
    )
    # TODO: character list
    add_standard_args(parser, random_seed=True, python=True)

    args = parser.parse_args()
    options = Options()
    options.max_stall = args.max_stall
    options.swap_ratio = args.swap_ratio

    if args.random_seed >= 0:
        random.seed(args.random_seed)

    w, h = args.size // 10, args.size % 10
    t, boggler = get_trie_and_boggler_from_args(args)

    best = Counter[str]()
    for run in range(args.num_boards):
        score, board, n = anneal(boggler, w * h, options)
        print(f"{score} {board} ({n} iterations)")
        best[board] = score

    if args.num_boards > 10:
        print("---")
        print("Top ten boards:")
        for score, board in best.most_common(10):
            print(f"{score} {board}")


if __name__ == "__main__":
    main()
