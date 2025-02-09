"""Standard command-line arguments share across many tools."""

import argparse


def add_standard_args(
    parser: argparse.ArgumentParser, *, random_seed=False, python=False
):
    parser.add_argument(
        "--size",
        type=int,
        choices=(22, 23, 33, 34, 44, 55),
        default=33,
        help="Size of the boggle board.",
    )
    parser.add_argument(
        "--dictionary",
        type=str,
        default="wordlists/enable2k.txt",
        help="Path to dictionary file with one word per line. Words must be "
        '"bogglified" via make_boggle_dict.py to convert "qu" -> "q".',
    )

    if random_seed:
        parser.add_argument(
            "--random_seed",
            help="Explicitly set the random seed.",
            type=int,
            default=-1,
        )
    if python:
        parser.add_argument(
            "--python",
            action="store_true",
            help="Use Python implementation instead of C++. This is ~50x slower!",
        )


def get_trie_from_args(args: argparse.Namespace):
    pass
