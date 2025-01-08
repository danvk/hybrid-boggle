from boggle.max_tree import MaxTreeUniverse

fs = frozenset


def freeze_keys(d):
    return {frozenset(k): v for k, v in d.items()}


def test_add_scalar():
    u = MaxTreeUniverse(["abc", "de"], 2)
    abc = u.from_ints(0, {"a": 3, "b": 4, "c": 0})
    assert u.to_dict(abc) == {fs({(0, "a")}): 3, fs({(0, "b")}): 4, fs({(0, "c")}): 0}

    assert u.to_dict(u.scalar(7)) == {fs(): 7}

    abc7 = u.add(abc, u.scalar(7))
    assert u.to_dict(abc7) == {
        fs({(0, "a")}): 10,
        fs({(0, "b")}): 11,
        fs({(0, "c")}): 7,
    }


def test_scalars():
    u = MaxTreeUniverse(["abc", "de"], 2)
    assert 7 == u.scalar(7)
    assert 12 == u.add(u.scalar(7), u.scalar(5))
    assert 7 == u.max(u.scalar(7), u.scalar(5))
    assert 7 == u.value(u.scalar(7), {0: "a"})
    assert 7 == u.max_value(u.scalar(7))


def test_value():
    u = MaxTreeUniverse(["abc", "de"], 2)
    abc = u.from_ints(0, {"a": 3, "b": 4, "c": 0})
    assert u.value(abc, {0: "a"}) == 3
    assert u.value(abc, {0: "b"}) == 4
    assert u.value(abc, {0: "c"}) == 0
    assert u.value(abc, {}) == 4
    assert u.value(abc, {1: "d"}) == 4


def test_add_max_disjoint():
    u = MaxTreeUniverse(["abc", "de"], 2)
    abc = u.from_ints(0, {"a": 3, "b": 4, "c": 0})
    de = u.from_ints(1, {"d": 5, "e": 7})

    s = u.add(abc, de)
    assert u.to_dict(s) == freeze_keys(
        {
            ((0, "a"), (1, "d")): 8,
            ((0, "a"), (1, "e")): 10,
            ((0, "b"), (1, "d")): 9,
            ((0, "b"), (1, "e")): 11,
            ((0, "c"), (1, "d")): 5,
            ((0, "c"), (1, "e")): 7,
        }
    )

    for cell0 in ("a", "b", "c"):
        for cell1 in ("d", "e"):
            choice = {0: cell0, 1: cell1}
            assert u.value(abc, choice) + u.value(de, choice) == u.value(s, choice)

    m = u.max(abc, de)
    assert u.to_dict(m) == freeze_keys(
        {
            ((0, "a"), (1, "d")): 5,
            ((0, "a"), (1, "e")): 7,
            ((0, "b"), (1, "d")): 5,
            ((0, "b"), (1, "e")): 7,
            ((0, "c"), (1, "d")): 5,
            ((0, "c"), (1, "e")): 7,
        }
    )
    for cell0 in ("a", "b", "c"):
        for cell1 in ("d", "e"):
            choice = {0: cell0, 1: cell1}
            assert max(u.value(abc, choice), u.value(de, choice)) == u.value(m, choice)

    add0 = u.add(s, abc)
    assert u.to_dict(add0) == freeze_keys(
        {
            ((0, "a"), (1, "d")): 11,
            ((0, "a"), (1, "e")): 13,
            ((0, "b"), (1, "d")): 13,
            ((0, "b"), (1, "e")): 15,
            ((0, "c"), (1, "d")): 5,
            ((0, "c"), (1, "e")): 7,
        }
    )

    add1 = u.add(de, s)
    assert u.to_dict(add1) == freeze_keys(
        {
            ((0, "a"), (1, "d")): 13,
            ((0, "a"), (1, "e")): 17,
            ((0, "b"), (1, "d")): 14,
            ((0, "b"), (1, "e")): 18,
            ((0, "c"), (1, "d")): 10,
            ((0, "c"), (1, "e")): 14,
        }
    )


def test_forget():
    u = MaxTreeUniverse(["abc", "de"], 2)
    abc = u.from_ints(0, {"a": 3, "b": 4, "c": 0})
    de = u.from_ints(1, {"d": 2, "e": 7})

    s = u.add(abc, de)
    assert u.to_dict(u.forget(s, 0)) == freeze_keys({((1, "d"),): 6, ((1, "e"),): 11})
    assert u.to_dict(u.forget(s, 1)) == freeze_keys(
        {
            ((0, "a"),): 10,
            ((0, "b"),): 11,
            ((0, "c"),): 7,
        }
    )


def test_collapse():
    u = MaxTreeUniverse(["ab", "cd", "ef"], 2)
    ab = u.from_ints(0, {"a": 1, "b": 2})
    cd = u.from_ints(1, {"c": 3, "d": 4})
    ef = u.from_ints(2, {"e": 5, "f": 6})
    abcd = u.add(ab, cd)
    assert len(abcd.cells) == 2
    assert u.to_dict(abcd) == freeze_keys(
        {
            ((0, "a"), (1, "c")): 4,
            ((0, "a"), (1, "d")): 5,
            ((0, "b"), (1, "c")): 5,
            ((0, "b"), (1, "d")): 6,
        }
    )

    abcdef = u.add(abcd, ef)
    assert abcdef.cells == [0, 2]
    assert u.to_dict(abcdef) == freeze_keys(
        {
            ((0, "a"), (2, "e")): 10,
            ((0, "a"), (2, "f")): 11,
            ((0, "b"), (2, "e")): 11,
            ((0, "b"), (2, "f")): 12,
        }
    )

    cdef = u.add(cd, ef)
    assert u.to_dict(cdef) == freeze_keys(
        {
            ((1, "c"), (2, "f")): 9,
            ((1, "d"), (2, "e")): 9,
            ((1, "d"), (2, "f")): 10,
            ((1, "c"), (2, "e")): 8,
        }
    )
    abcdef = u.add(abcd, cdef)
    assert abcdef.cells == [1, 2]


def test_from_choices():
    u = MaxTreeUniverse(["ab", "cd", "ef"], 2)
    acd = u.from_ints(1, {"c": 3, "d": 4})
    bcd = u.from_ints(1, {"c": 4, "d": 2})
    abcd = u.from_choices(0, {"a": acd, "b": bcd})
    assert u.to_dict(abcd) == freeze_keys(
        {
            ((0, "a"), (1, "c")): 3,
            ((0, "a"), (1, "d")): 4,
            ((0, "b"), (1, "c")): 4,
            ((0, "b"), (1, "d")): 2,
        }
    )

    # test collapse
    ef = u.from_choices(2, {"e": acd, "f": abcd})
    assert ef.cells == [2, 1]
    assert u.to_dict(ef) == freeze_keys(
        {
            ((2, "e"), (1, "c")): 3,
            ((2, "e"), (1, "d")): 4,
            ((2, "f"), (1, "c")): 4,
            ((2, "f"), (1, "d")): 4,
        }
    )


def test_choices_from_scalar():
    u = MaxTreeUniverse(["ab", "cd", "ef"], 2)
    ab = u.from_choices(0, {"a": u.scalar(1), "b": u.scalar(2)})
    assert u.to_dict(ab) == {frozenset({(0, "a")}): 1, frozenset({(0, "b")}): 2}


def test_op_crash():
    u = MaxTreeUniverse(
        "aeiou chkmpt lnrsy lnrsy lnrsy aeiou aeiou aeiou bdfgjvwxz".split(" "), 3
    )
    a7 = u.from_ints(7, {"a": 1, "e": 2, "i": 3, "o": 4, "u": 5})
    a74 = u.from_choices(
        4, {"l": u.scalar(1), "n": a7, "r": a7, "s": a7, "y": u.scalar(2)}
    )
    assert a74.cells == [4, 7]
    a1 = u.from_ints(1, {c: i for i, c in enumerate("chkmpt")})
    a = u.add(a1, a74)
    assert a.cells == [1, 4, 7]
