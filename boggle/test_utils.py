from cpp_boggle import Trie

from boggle.dimensional_bogglers import cpp_orderly_tree_builder
from boggle.orderly_tree_builder import OrderlyTreeBuilder
from boggle.trie import make_py_trie


# TODO: cache the trie
def get_trie_otb(dict_file: str, dims: tuple[int, int], is_python: bool):
    if is_python:
        trie = make_py_trie(dict_file)
        otb = OrderlyTreeBuilder(trie, dims=dims)
    else:
        trie = Trie.create_from_file(dict_file)
        otb = cpp_orderly_tree_builder(trie, dims=dims)
    return trie, otb
