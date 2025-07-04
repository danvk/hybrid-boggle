"""Find high-scoring Boggle boards via pure hill climbing.

This maintains a pool of boards (randomly chosen at first) and evaluates
all the boards within an edit distance of 1. It then chooses the highest
scoring of these boards plus the current pool as the pool for the next round.

Larger pool sizes will increase the odds of making it over to the next peak
at the cost of more computation per iteration.

This might be an implementation of this algorithm:
https://en.wikipedia.org/wiki/Greedy_randomized_adaptive_search_procedure
"""

import argparse
import functools
import multiprocessing
import random
import time
from collections import Counter
from typing import Sequence

from cpp_boggle import Symmetry

from boggle.anneal import A_TO_Z, initial_board
from boggle.args import add_standard_args, get_trie_and_boggler_from_args


def get_valid_letters(args):
    exclude = {ord(c) for c in (args.exclude_letters or "")}
    valid_letters = [c for c in A_TO_Z if c not in exclude]
    if len(valid_letters) < 26:
        print(f"Will use {len(valid_letters)} letters.")
    return valid_letters


def neighbors(board: str, valid_letters: Sequence[int]):
    """Find all boards within a distance of 1 of this one.

    This includes:
    - Changing any one cell to another letter.
    - Swapping any two cells.
    """
    out = set()
    out.add(board)

    # single letter changes
    for i, c in enumerate(board):
        current = ord(c)
        prefix = board[:i]
        suffix = board[i + 1 :]
        for j in valid_letters:
            if j == current:
                continue
            n = prefix + chr(j) + suffix
            out.add(n)

    # letter swaps
    for i in range(len(board) - 1):
        prefix = board[:i]
        ci = board[i]
        for j in range(i + 1, len(board)):
            cj = board[j]
            n = prefix + cj + board[i + 1 : j] + ci + board[j + 1 :]
            out.add(n)

    return out


def get_process_id():
    ids = multiprocessing.current_process()._identity
    if len(ids) == 0:
        return 1  # single-threaded case
    assert len(ids) == 1
    return ids[0]


def hillclimb(task: int):
    me = get_process_id()
    seed = hillclimb.random_seed + task

    def print_and_write(line: str):
        print(line)
        with open(f"hillclimb-{me}.txt", "a") as out:
            out.write(line + "\n")

    random.seed(seed)
    print_and_write(f"#{me} starting hillclimb with random seed = {seed}")
    args = hillclimb.args
    w, h = hillclimb.dims
    boggler = hillclimb.boggler
    num_lets = w * h
    valid_letters = get_valid_letters(args)

    sym = Symmetry(w, h)

    pool = [
        sym.canonicalize(
            "".join(chr(x) for x in initial_board(num_lets, valid_letters))
        )
        for _ in range(args.pool_size)
    ]

    @functools.cache
    def get_score(bd: str):
        # This is a convenient place to make adjustments to the score, e.g.
        # to require a "q" on the board or to exclude high-scoring boards to test
        # whether hill climbing can find other boards in their absence.
        # if "q" not in bd:
        #     return 0
        score = boggler.score(bd)
        # if score > 3512:
        #     score = 1000
        return score

    best_score = max(get_score(bd) for bd in pool)

    num_iter = 0
    while True:
        num_iter += 1
        ns = {
            sym.canonicalize(n) for seed in pool for n in neighbors(seed, valid_letters)
        }
        scores = [(get_score(n), n) for n in ns]
        scores.sort(reverse=True)
        scores = scores[: args.pool_size]
        line = f"#{me} {num_iter=}: {max(scores)=} {min(scores)=}"
        print_and_write(line)
        new_pool = [bd for _, bd in scores]
        if new_pool == pool:
            break
        pool = new_pool

    best_score, best_bd = max(scores)
    return best_score, best_bd, num_iter, scores


def hillclimb_init(args):
    hillclimb.args = args
    trie, boggler = get_trie_and_boggler_from_args(args)
    hillclimb.trie = trie  # not used directly, but must not be GC'd
    hillclimb.boggler = boggler
    if args.random_seed >= 0:
        hillclimb.random_seed = args.random_seed
    else:
        hillclimb.random_seed = time.time()

    w, h = args.size // 10, args.size % 10
    hillclimb.dims = (w, h)


def main():
    parser = argparse.ArgumentParser(
        prog="Hill climbing",
        description="Find high-scoring Boggle boards in the greediest way possible.",
    )
    parser.add_argument(
        "num_boards",
        type=int,
        default=100,
        help="Number of high-scoring boards to find before quitting.",
    )
    parser.add_argument(
        "--max_radius",
        type=int,
        default=3,
        help="Stop if there are no improvements within this radius.",
    )
    parser.add_argument(
        "--pool_size",
        type=int,
        default=100,
        help="Keep this many candidates as seeds for the next round.",
    )
    parser.add_argument(
        "--num_threads",
        type=int,
        default=1,
        help="Number of concurrent hillclimbing runs to perform.",
    )
    parser.add_argument(
        "--exclude_letters",
        type=str,
        help="List of characters to exclude from the search, e.g. 'qzj'",
    )
    add_standard_args(parser, random_seed=True, python=True)

    args = parser.parse_args()
    pool = None
    tasks = range(args.num_boards)
    if args.num_threads > 1:
        pool = multiprocessing.Pool(args.num_threads, hillclimb_init, (args,))
        it = pool.imap_unordered(hillclimb, tasks)
    else:
        hillclimb_init(args)
        it = (hillclimb(task) for task in tasks)

    out = open("hillclimb.root.txt", "w")

    def print_and_write(line: str):
        print(line)
        out.write(line)
        out.write("\n")

    best = Counter[tuple[int, str]]()
    for run, (score, board, n, score_boards) in enumerate(it):
        print_and_write(f"{run}/{args.num_boards} {score} {board} ({n} iterations)")
        best.update(score_boards)

        if args.num_boards > 1:
            print_and_write("---")
            print_and_write(f"Top {args.pool_size} boards:")
            tops = [*best.keys()]
            tops.sort(reverse=True)
            tops = tops[: args.pool_size]
            for score_board in tops:
                score, board = score_board
                freq = best[score_board]
                print_and_write(f"{score}\t{board}\t{freq}/{1+run}")


if __name__ == "__main__":
    main()
