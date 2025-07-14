from cpp_boggle import Trie

from boggle.trie import bogglify_word


def asc(char: str):
    assert len(char) == 1
    return ord(char) - ord("a")


def test_trie():
    t = Trie.create_from_wordlist(
        [
            "agriculture",
            "culture",
            "boggle",
            "tea",
            "sea",
            "teapot",
        ]
    )
    assert not t.is_word()

    assert t.size() == 6
    assert t.find_word("agriculture") is not None
    assert t.find_word("culture") is not None
    assert t.find_word("boggle") is not None
    assert t.find_word("tea") is not None
    assert t.find_word("sea") is not None
    assert t.find_word("teapot") is not None

    assert t.find_word("teap") is None
    assert t.find_word("random") is None
    assert t.find_word("cultur") is None

    wd = t.descend(asc("t"))
    assert wd is not None
    wd = wd.descend(asc("e"))
    assert wd is not None
    wd = wd.descend(asc("a"))
    assert wd is not None
    assert wd.mark() == 0
    wd.set_mark(12345)
    assert wd.mark() == 12345

    child = t.find_word("agriculture")
    assert child is not None
    assert Trie.reverse_lookup(t, child) == "agriculture"


def test_bogglify_word():
    assert bogglify_word("quart") == "qart"
    assert bogglify_word("qi") is None
    assert bogglify_word("is") is None
    assert bogglify_word("boggle") == "boggle"
    assert bogglify_word("quinquennia") == "qinqennia"


def test_load_file():
    t = Trie.create_from_file("testdata/boggle-words-4.txt")
    assert not t.is_word()

    assert t.find_word("wood") is not None
    assert t.find_word("woxd") is None
