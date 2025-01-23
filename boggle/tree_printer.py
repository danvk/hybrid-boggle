#!/usr/bin/env python
"""Output DOT for graph visualization.

Used as the starting point for the tree in this question:
https://stackoverflow.com/q/79381817/388951
"""

from boggle.eval_tree import EvalTreeBoggler
from boggle.trie import PyTrie


def main():
    trie = PyTrie()
    trie.AddWord("tar")
    trie.AddWord("tie")
    trie.AddWord("tier")
    trie.AddWord("tea")
    trie.AddWord("the")
    etb = EvalTreeBoggler(trie, (3, 3))
    assert etb.ParseBoard("t i z ae z z r z z")
    t = etb.BuildTree(dedupe=False)
    print(t.to_dot(etb))


if __name__ == "__main__":
    main()
