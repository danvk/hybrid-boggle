from cpp_boggle import Trie


def asc(char: str):
    assert len(char) == 1
    return ord(char) - ord("a")


def test_trie():
    t = Trie()
    t.AddWord("agriculture")
    t.AddWord("culture")
    t.AddWord("boggle")
    t.AddWord("tea")
    t.AddWord("sea")
    t.AddWord("teapot")

    assert t.Size() == 6
    assert t.FindWord("agriculture") is not None
    assert t.FindWord("culture") is not None
    assert t.FindWord("boggle") is not None
    assert t.FindWord("tea") is not None
    assert t.FindWord("sea") is not None
    assert t.FindWord("teapot") is not None

    assert t.FindWord("teap") is None
    assert t.FindWord("random") is None
    assert t.FindWord("cultur") is None

    wd = t.Descend(asc("t"))
    assert wd is not None
    wd = wd.Descend(asc("e"))
    assert wd is not None
    wd = wd.Descend(asc("a"))
    assert wd is not None
    assert wd.Mark() == 0
    wd.SetMark(12345)
    assert wd.Mark() == 12345

    child = t.FindWord("agriculture")
    assert child is not None
    assert Trie.ReverseLookup(t, child) == "agriculture"
