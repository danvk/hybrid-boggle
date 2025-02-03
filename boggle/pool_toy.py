"""Experimenting with Python multiprocessing."""

import multiprocessing
import random
import time

from tqdm import tqdm


def init(args, fn):
    (me,) = multiprocessing.current_process()._identity
    fn.bias = args.bias + me


def f(x: int):
    bias = f.bias
    # (me,) = multiprocessing.current_process()._identity
    # print(f"{me=} {bias=}")
    # print(f"{me} Start {x=}")
    if x == 2:
        # print(f"{me} waiting long time")
        time.sleep(5)
    time.sleep(random.random())
    # print(f"{me} Finish {x=}")
    return x + bias


def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="Pool toy",
        description="Playing around with multiprocessing.Pool",
    )
    parser.add_argument("--bias", type=int, default=0)
    args = parser.parse_args()

    p = multiprocessing.Pool(3, init, (args, f))
    it = p.imap_unordered(f, [*range(10)])

    total = 0
    for x in tqdm(it, total=10):
        # print(f"Main thread: {x=}")
        total += x
    print(total)


if __name__ == "__main__":
    main()
