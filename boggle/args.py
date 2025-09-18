"""Standard command-line arguments share across many tools."""

import argparse

from cpp_boggle import IndexedTrie, TrieHolder

from boggle.boggler import PyBoggler
from boggle.dimensional_bogglers import (
    Bogglers,
    cpp_bucket_boggler,
    cpp_orderly_tree_builder,
)
from boggle.ibuckets import PyBucketBoggler
from boggle.orderly_tree_builder import OrderlyTreeBuilder
from boggle.trie import make_py_trie


def add_standard_args(
    parser: argparse.ArgumentParser, *, random_seed=False, python=False
):
    parser.add_argument(
        "--size",
        type=int,
        choices=(22, 23, 33, 34, 44, 45, 55),
        default=33,
        help="Size of the boggle board.",
    )
    parser.add_argument(
        "--dictionary",
        type=str,
        default="wordlists/enable2k.txt",
        help="Path to dictionary file with one word per line.",
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
        t = make_py_trie(args.dictionary)
        assert t
    else:
        t = TrieHolder.create_from_file(args.dictionary)
        assert t
    return t


def get_trie_and_boggler_from_args(args: argparse.Namespace):
    th = get_trie_from_args(args)
    dims = args.size // 10, args.size % 10

    if args.python:
        boggler = PyBoggler(th.get_trie(), dims)
    else:
        boggler = Bogglers[dims](th.get_trie())
    return th, boggler


def get_trie_boggler_builder_from_args(args: argparse.Namespace):
    dims = args.size // 10, args.size % 10
    is_tree = args.breaker == "hybrid"

    if args.python:
        th = make_py_trie(args.dictionary)
        t = it = th.get_trie()
        boggler = PyBoggler(t, dims)
        builder_class = OrderlyTreeBuilder if is_tree else PyBucketBoggler

    else:
        it = IndexedTrie.create_from_file(args.dictionary)
        assert it
        th = TrieHolder.compact_trie(it)
        assert th
        boggler = Bogglers[dims](th.get_trie())
        builder_class = cpp_orderly_tree_builder if is_tree else cpp_bucket_boggler

    builder = builder_class(it, dims)
    return th, boggler, builder
