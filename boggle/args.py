"""Standard command-line arguments share across many tools."""

import argparse

from cpp_boggle import Trie

from boggle.boggler import PyBoggler
from boggle.dimensional_bogglers import Bogglers
from boggle.trie import get_letter_map, make_py_trie


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
    parser.add_argument(
        "--letter_grouping",
        type=str,
        default="",
        help="Letter chunks, space-delimited. The first letter in each chunk is "
        'the canonical one, so "abc" would change "b" and "c" to "a". Omitted letters '
        "get their own class. Default is no chunking.",
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
    if args.python:
        t = make_py_trie(args.dictionary, args.letter_grouping)
        assert t
    else:
        if args.letter_grouping:
            m = get_letter_map(args.letter_grouping)
            t = Trie.CreateFromFileWithGrouping(args.dictionary, m)
        else:
            t = Trie.CreateFromFile(args.dictionary)
        assert t
    return t


def get_trie_and_boggler_from_args(args: argparse.Namespace):
    t = get_trie_from_args(args)
    dims = args.size // 10, args.size % 10

    if args.python:
        boggler = PyBoggler(t, dims)
    else:
        boggler = Bogglers[dims](t)
    return t, boggler
