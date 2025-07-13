from cpp_boggle import Packed5Array


def test_get_set():
    a = Packed5Array()
    assert a.get(0) == 0
    assert a.get(1) == 0
    assert a.get(31) == 0

    a.set(16, 12)
    assert a.get(16) == 12
