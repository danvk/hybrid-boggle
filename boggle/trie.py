from typing import Self

LETTER_A = ord("a")


class PyTrie:
    _children: list[Self | None]
    _mark: int
    _is_word: bool

    def __init__(self):
        self._is_word = False
        self._mark = 0
        self._children = [None] * 26

    def starts_word(self, i: int):
        return self._children[i] is not None

    def descend(self, i: int):
        return self._children[i]

    def is_word(self):
        return self._is_word

    def mark(self):
        return self._mark

    def set_mark(self, mark):
        self._mark = mark

    # ---

    def set_is_word(self):
        self._is_word = True

    def add_word(self, word: str) -> Self:
        if word == "":
            self.set_is_word()
            return self
        c = ord(word[0]) - LETTER_A
        try:
            if not self.starts_word(c):
                self._children[c] = PyTrie()
        except IndexError:
            print(c, word)
            raise
        return self.descend(c).add_word(word[1:])

    def size(self):
        return (1 if self.is_word() else 0) + sum(c.size() for c in self._children if c)

    def num_nodes(self):
        return 1 + sum(c.num_nodes() for c in self._children if c)

    def find_word(self, word: str):
        if word == "":
            return self
        c = ord(word[0]) - LETTER_A
        if self.starts_word(c):
            return self.descend(c).find_word(word[1:])
        return None

    def reset_marks(self):
        self.set_mark(0)
        for child in self._children:
            if not child:
                continue
            child.reset_marks()

    @staticmethod
    def reverse_lookup(root: Self, node: Self):
        return reverse_lookup(root, node)


def reverse_lookup(root: PyTrie, node: PyTrie):
    if root is node:
        return ""
    for i, child in enumerate(root._children):
        if not child:
            continue
        child_result = reverse_lookup(child, node)
        if child_result is not None:
            return chr(i + LETTER_A) + child_result
    return None


def make_lookup_table(t: PyTrie, prefix="", out=None) -> dict[PyTrie, str]:
    """Construct a Trie -> str table for debugging."""
    out = out or {}
    out[t] = prefix
    for i, child in enumerate(t._children):
        if child:
            make_lookup_table(child, prefix + chr(i + LETTER_A), out)
    return out


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


def make_py_trie(dict_input: str):
    t = PyTrie()

    for word in open(dict_input):
        word = word.strip()
        word = bogglify_word(word)
        if word is not None:
            t.add_word(word)
    return t
