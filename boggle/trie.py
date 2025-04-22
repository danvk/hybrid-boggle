from typing import Self

LETTER_A = ord("a")


class PyTrie:
    def __init__(self):
        self.is_word = False
        self.mark = 0
        self.children = [None] * 26

    def StartsWord(self, i: int):
        return self.children[i] is not None

    def Descend(self, i: int):
        return self.children[i]

    def IsWord(self):
        return self.is_word

    def Mark(self):
        return self.mark

    def SetMark(self, mark):
        self.mark = mark

    # ---

    def SetIsWord(self):
        self.is_word = True

    def AddWord(self, word):
        if word == "":
            self.SetIsWord()
            return self
        c = ord(word[0]) - LETTER_A
        try:
            if not self.StartsWord(c):
                self.children[c] = PyTrie()
        except IndexError:
            print(c, word)
            raise
        return self.Descend(c).AddWord(word[1:])

    def Size(self):
        return (1 if self.IsWord() else 0) + sum(c.Size() for c in self.children if c)

    def NumNodes(self):
        return 1 + sum(c.NumNodes() for c in self.children if c)

    def FindWord(self, word):
        if word == "":
            return self
        c = ord(word[0]) - LETTER_A
        if self.StartsWord(c):
            return self.Descend(c).FindWord(word[1:])
        return None

    def ResetMarks(self):
        self.mark = 0
        for child in self.children:
            if not child:
                continue
            child.ResetMarks()

    @staticmethod
    def ReverseLookup(root: Self, node: Self):
        return reverse_lookup(root, node)


def reverse_lookup(root: PyTrie, node: PyTrie):
    if root is node:
        return ""
    for i, child in enumerate(root.children):
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
    for i, child in enumerate(t.children):
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
            t.AddWord(word)
    return t
