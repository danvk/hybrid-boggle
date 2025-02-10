import argparse
import random
from collections import Counter

from cpp_boggle import Trie

from boggle.anneal import initial_board
from boggle.args import add_standard_args
from boggle.boggler import PyBoggler
from boggle.dimensional_bogglers import Bogglers
from boggle.trie import LETTER_A, make_py_trie


def neighbors(board: str):
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
        for j in range(LETTER_A, LETTER_A + 26):
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


def hillclimb(boggler: PyBoggler, num_lets: int, args):
    pool = [
        "".join(chr(x) for x in initial_board(num_lets)) for _ in range(args.pool_size)
    ]
    score_cache = dict[str, int]()
    for bd in pool:
        score_cache[bd] = boggler.score(bd)

    best_score = max(score_cache.values())

    num_iter = 0
    while True:
        num_iter += 1
        ns = {n for seed in pool for n in neighbors(seed)}
        scores = []
        for n in ns:
            score = score_cache.get(n) or boggler.score(n)
            score_cache[n] = score
            scores.append((score, n))
        scores.sort(reverse=True)
        scores = scores[: args.pool_size]
        print(f"{num_iter=}: {max(scores)=} {min(scores)=}")
        new_pool = [bd for _, bd in scores]
        if new_pool == pool:
            break
        pool = new_pool

    best_score, best_bd = max(scores)
    return best_score, best_bd, num_iter


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
    # TODO: character list
    add_standard_args(parser, random_seed=True, python=True)

    args = parser.parse_args()

    if args.random_seed >= 0:
        random.seed(args.random_seed)

    w, h = dims = args.size // 10, args.size % 10

    if args.python:
        t = make_py_trie(args.dictionary)
        assert t
        boggler = PyBoggler(t, dims)
    else:
        t = Trie.CreateFromFile(args.dictionary)
        assert t
        boggler = Bogglers[dims](t)

    best = Counter[str]()
    for run in range(args.num_boards):
        score, board, n = hillclimb(boggler, w * h, args)
        print(f"{run=} {score} {board} ({n} iterations)")
        best[board] = score

    if args.num_boards > 10:
        print("---")
        print("Top ten boards:")
        for score, board in best.most_common(10):
            print(f"{score} {board}")


if __name__ == "__main__":
    main()
