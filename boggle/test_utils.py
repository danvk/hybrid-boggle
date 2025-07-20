import functools

from cpp_boggle import Trie

from boggle.dimensional_bogglers import cpp_orderly_tree_builder
from boggle.orderly_tree_builder import OrderlyTreeBuilder
from boggle.trie import make_py_trie


@functools.cache
def get_trie(dict_file: str, is_python: bool):
    if is_python:
        return make_py_trie(dict_file)
    else:
        return Trie.create_from_file(dict_file)


def get_trie_otb(dict_file: str, dims: tuple[int, int], is_python: bool):
    trie = get_trie(dict_file, is_python)
    if is_python:
        otb = OrderlyTreeBuilder(trie, dims=dims)
    else:
        otb = cpp_orderly_tree_builder(trie, dims=dims)
    return trie, otb
