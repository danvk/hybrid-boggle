"""Experimenting with Python multiprocessing."""

import multiprocessing
import random
import time

from tqdm import tqdm


def f(x: int):
    (me,) = multiprocessing.current_process()._identity
    # print(f"{me} Start {x=}")
    if x == 2:
        # print(f"{me} waiting long time")
        time.sleep(5)
    time.sleep(random.random())
    # print(f"{me} Finish {x=}")
    return x


def main():
    p = multiprocessing.Pool(3)
    it = p.imap_unordered(f, range(10))

    total = 0
    for x in tqdm(it, total=10):
        # print(f"Main thread: {x=}")
        total += x
    print(total)


if __name__ == "__main__":
    main()
