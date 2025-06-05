from typing import Self

LETTER_A = ord("a")


def to_idx(letter: str):
    assert "a" <= letter <= "z"
    return ord(letter) - LETTER_A


class Trie:
    _children: list[Self | None]
    _mark: int
    _is_word: bool
    _length: int

    def __init__(self):
        self._is_word = False
        self._mark = False
        self._children = [None] * 26

    def has_child(self, letter: str):
        return self._children[to_idx(letter)] is not None

    def child(self, letter: str):
        return self._children[to_idx(letter)]

    def is_word(self):
        return self._is_word

    def is_visited(self):
        return self._mark

    def set_visited(self):
        self._mark = True

    def length(self):
        return self._length

    # ---

    def set_is_word(self):
        self._is_word = True

    def add_word(self, word: str) -> Self:
        if word == "":
            self.set_is_word()
            return self
        letter = word[0]
        c = to_idx(letter)
        try:
            if not self.has_child(letter):
                self._children[c] = Trie()
        except IndexError:
            print(c, word)
            raise
        return self.child(letter).add_word(word[1:])

    def size(self):
        return (1 if self.is_word() else 0) + sum(c.size() for c in self._children if c)

    def num_nodes(self):
        return 1 + sum(c.num_nodes() for c in self._children if c)

    def reset_marks(self):
        self.set_mark(0)
        for child in self._children:
            if not child:
                continue
            child.reset_marks()


def is_boggle_word(word: str):
    size = len(word)
    if size < 3:
        return False
    for i, let in enumerate(word):
        if let < "a" or let > "z":
            return False
        if let == "q" and (i + 1 >= size or word[i + 1] != "u"):
            return False
    return True


def bogglify_word(word: str) -> str | None:
    if not is_boggle_word(word):
        return None
    return word.replace("qu", "q")


def make_trie(dict_input: str):
    t = Trie()

    for word in open(dict_input):
        word = word.strip()
        word = bogglify_word(word)
        if word is not None:
            t.add_word(word)._length = len(word) + word.count("q")
    return t


def make_lookup_table(t: Trie, prefix="", out=None) -> dict[Trie, str]:
    """Construct a Trie -> str table for debugging."""
    out = out or {}
    out[t] = prefix
    for i, child in enumerate(t._children):
        if child:
            make_lookup_table(child, prefix + chr(i + LETTER_A), out)
    return out
