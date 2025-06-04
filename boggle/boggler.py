from boggle.neighbors import NEIGHBORS
from boggle.trie import PyTrie, make_lookup_table

#                  1, 2, 3, 4, 5, 6, 7,  8,     9..25
SCORES = tuple([0, 0, 0, 1, 1, 2, 3, 5, 11] + [11 for _ in range(9, 26)])
assert len(SCORES) == 26
LETTER_A = ord("a")
LETTER_Q = ord("q") - LETTER_A
LETTER_Z = ord("z")


class PyBoggler:
    """Hybrid or pure-Python Boggler (depending on the Trie)."""

    _trie: PyTrie

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
        self._neighbors = NEIGHBORS[dims]
        self.lookup_table = None
        assert not self._trie.is_word()

    def set_board(self, bd: str):
        assert len(bd) == self._n
        for i, let in enumerate(bd):
            if let == ".":
                self._cells[i] = -1
            else:
                assert "a" <= let <= "z"
                self._cells[i] = ord(let) - LETTER_A

    def __str__(self):
        return "".join(chr(ord("a") + let) if let != -1 else "." for let in self._cells)

    def score(self, bd: str):
        self.set_board(bd)
        # This allows the same Trie to be used by multiple bogglers, e.g. for boggle_test.py
        self._runs = 1 + self._trie.mark()
        self._trie.set_mark(self._runs)
        self._score = 0
        if self.collect_words:
            self.words = []
            if not self.lookup_table:
                self.lookup_table = make_lookup_table(self._trie)
        t = self._trie
        for i in range(0, self._n):
            c = self._cells[i]
            if c == -1:
                continue
            d = t.descend(c)
            if d:
                self.do_dfs(i, 0, d)
        return self._score

    def do_dfs(self, i: int, length: int, t):
        c = self._cells[i]
        self._used[i] = True
        length += 1 if c != LETTER_Q else 2
        if t.is_word():
            if t.mark() != self._runs:
                t.set_mark(self._runs)
                self._score += SCORES[length]
                if self.collect_words:
                    self.words.append(self.lookup_table[t])

        for idx in self._neighbors[i]:
            if not self._used[idx]:
                cc = self._cells[idx]
                if cc == -1:
                    continue
                d = t.descend(cc)
                if d:
                    self.do_dfs(idx, length, d)

        self._used[i] = False

    def find_words(self, lets: str, multiboggle) -> list[list[int]]:
        """multiboggle is either False, "raw" or "dedupe"."""
        self._seq = []
        self._found_words = set()
        self.set_board(lets)
        self._runs = self._trie.mark() + 1
        self._trie.set_mark(self._runs)
        self._score = 0
        self._used = [False] * 16
        t = self._trie
        out = []
        for i in range(0, self._n):
            c = self._cells[i]
            if c == -1:
                continue
            d = t.descend(c)
            if d:
                self.find_words_dfs(i, d, multiboggle, out)
        return out

    def find_words_dfs(self, i: int, t: PyTrie, multiboggle, out: list[list[int]]):
        self._used[i] = True
        self._seq.append(i)

        if t.is_word():
            if multiboggle:
                key = (id(t), tuple(sorted(self._seq)))
                should_count = multiboggle == "raw" or (key not in self._found_words)
                if should_count:
                    self._found_words.add(key)
            else:
                should_count = t.mark() != self._runs
            if should_count:
                t.set_mark(self._runs)
                out.append([*self._seq])

        for idx in self._neighbors[i]:
            if not self._used[idx]:
                cc = self._cells[idx]
                if cc == -1:
                    continue
                d = t.descend(cc)
                if d:
                    self.find_words_dfs(idx, d, multiboggle, out)

        self._seq.pop()
        self._used[i] = False

    def multiboggle_score(self, lets: str) -> int:
        return sum(
            SCORES[sum(2 if lets[cell] == "q" else 1 for cell in path)]
            for path in self.find_words(lets, True)
        )
