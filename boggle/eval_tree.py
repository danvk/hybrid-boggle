"""A tree representing the evaluation of a class of Boggle boards.

See https://www.danvk.org/2025/02/13/boggle2025.html#the-evaluation-tree

There are two types of nodes: sum and choice:

- Sum nodes sum points across their children. This models how you can move in any direction
  to extend a word, or start words from any cell on the board.
- Choice nodes reflect a choice that must be made, namely which letter to choose for
  a cell in the board class. To get a bound, we can take the max across any
  choice, but this is imprecise because the same choice can appear in many subtrees and
  our choices won't be synchronized across those subtrees.

The children of sum nodes are choice nodes, and vice versa.
The root of the tree is always a sum node.

You can use node.bound to get the current upper bound for any subtree.

To reduce the bound, you can "force" a choice on a cell to get a subtree
for each possibility for that cell. This has the effect of merging other
choices and reducing the bound.
"""

import itertools
from collections import Counter
from typing import Self, Sequence

from cpp_boggle import ChoiceNode, SumNode

from boggle.arena import PyArena
from boggle.board_class_boggler import BoardClassBoggler
from boggle.trie import make_lookup_table

ROOT_NODE = -2
CHOICE_NODE = -1


cache_count = 1


class EvalNode:
    pass
