from boggle.neighbors import NEIGHBORS
from boggle.trie import make_lookup_table

#                  1, 2, 3, 4, 5, 6, 7,  8
SCORES = tuple([0, 0, 0, 1, 1, 2, 3, 5, 11] + [11 for _ in range(9, 25 + 1)])
assert len(SCORES) == 25 + 1
LETTER_A = ord("a")
LETTER_Q = ord("q") - LETTER_A
LETTER_Z = ord("z")


class PyBoggler:
    """Pure-Python Boggler. Has the same API as Boggler<M, N> plus some extra."""

    def __init__(self, trie, dims: tuple[int, int]):
        self._trie = trie
        self._runs = 0
        w, h = dims
        self._n = w * h
        self._cells = [0] * self._n
        self._used = [False] * self._n
        self._score = 0
        self.collect_words = False
        self.words = None
        self._is_multi = False
        self._neighbors = NEIGHBORS[dims]
        self.lookup_table = None
        assert not self._trie.IsWord()

    def set_board(self, bd: str):
        assert len(bd) == self._n
        for i, let in enumerate(bd):
            if let == ".":
                self._cells[i] = -1
            else:
                assert "a" <= let <= "z"
                self._cells[i] = ord(let) - LETTER_A

    def set_cell_at_index(self, cell: int, letter: int):
        self._cells[cell] = letter

    def __str__(self):
        return "".join(chr(ord("a") + let) if let != -1 else "." for let in self._cells)

    def score(self, bd: str):
        self.set_board(bd)
        self._used = [False] * self._n
        return self.score_internal()

    def score_with_mask(self, mask: int):
        """mask=0 is equivalent to normal scoring"""
        assert mask >= 0
        self._used = [mask & (1 << i) != 0 for i in range(self._n)]
        return self.score_internal()

    def multi_score_with_mask(self, mask: int):
        self._is_multi = True
        score = self.score_with_mask(mask)
        self._is_multi = False
        return score

    def score_internal(self):
        # This allows the same Trie to be used by multiple bogglers, e.g. for boggle_test.py
        self._runs = 1 + self._trie.Mark()
        self._trie.SetMark(self._runs)
        self._score = 0
        if self.collect_words:
            self.words = []
            if not self.lookup_table:
                self.lookup_table = make_lookup_table(self._trie)
        t = self._trie
        for i in range(0, self._n):
            c = self._cells[i]
            if c == -1 or self._used[i]:
                continue
            d = t.Descend(c)
            if d:
                self.do_dfs(i, 0, d)
        return self._score

    def do_dfs(self, i: int, length: int, t):
        c = self._cells[i]
        self._used[i] = True
        length += 1 if c != LETTER_Q else 2
        if t.IsWord():
            if self._is_multi or t.Mark() != self._runs:
                t.SetMark(self._runs)
                self._score += SCORES[length]
                if self.collect_words:
                    self.words.append(self.lookup_table[t])

        for idx in self._neighbors[i]:
            if not self._used[idx]:
                cc = self._cells[idx]
                if cc == -1:
                    continue
                d = t.Descend(cc)
                if d:
                    self.do_dfs(idx, length, d)

        self._used[i] = False
