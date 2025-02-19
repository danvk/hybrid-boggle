import math

from boggle.neighbors import NEIGHBORS
from boggle.trie import PyTrie


class BoardClassBoggler:
    """Base class for any boggler than works with board classes."""

    trie_: PyTrie
    bd_: list[str]
    used_: int
    neighbors: list[list[int]]
    cells: list[int]

    def __init__(self, trie: PyTrie, dims: tuple[int, int]):
        self.trie_ = trie
        self.used_ = 0
        self.bd_ = []
        self.neighbors = NEIGHBORS[dims]
        self.dims = dims
        self.cells = []

    def ParseBoard(self, board: str):
        cells = board.split(" ")
        if len(cells) != self.dims[0] * self.dims[1] or not all(cells):
            return False
        # '.' is an explicit "don't go here," which is useful for testing.
        self.bd_ = [b if b != "." else "" for b in cells]
        return True

    def NumReps(self) -> int:
        return math.prod(len(cell) for cell in self.bd_)

    def as_string(self):
        return " ".join(b if b else "." for b in self.bd_)
