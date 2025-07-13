from cpp_boggle import Packed5Array


def test_get_set():
    a = Packed5Array()
    assert a.get(0) == 0
    assert a.get(1) == 0
    assert a.get(31) == 0

    a.set(16, 12)
    assert a.get(16) == 12


def test_compare():
    a = Packed5Array()
    b = Packed5Array()

    assert 0 == a.compare(b)
    a.set(0, 1)
    assert 1 == a.compare(b)
    b.set(1, 2)
    assert 1 == a.compare(b)
    b.set(0, 1)
    assert -1 == a.compare(b)
    a.set(1, 2)
    assert 0 == a.compare(b)


def test_edge_cases():
    """Test edge cases for 5-bit values (0-31)"""
    a = Packed5Array()

    # Test all valid 5-bit values
    for i in range(32):
        a.set(i, i)
        assert a.get(i) == i

    # Test maximum value
    a.set(0, 31)
    assert a.get(0) == 31

    # Test that other positions are unaffected
    a.set(5, 15)
    assert a.get(0) == 31
    assert a.get(5) == 15
    assert a.get(1) == 1  # from previous loop


def test_boundary_positions():
    """Test positions that cross byte boundaries"""
    a = Packed5Array()

    # These positions should cross byte boundaries due to 5-bit packing
    test_positions = [0, 1, 2, 7, 8, 9, 15, 16, 17, 23, 24, 25, 31]

    for pos in test_positions:
        value = (pos * 3) % 32  # Generate different values
        a.set(pos, value)
        assert a.get(pos) == value, f"Failed at position {pos}"


def test_lexicographic_compare():
    """Test that compare() implements lexicographic ordering correctly"""
    a = Packed5Array()
    b = Packed5Array()

    # Test prefix comparison
    a.set(0, 1)
    a.set(1, 2)
    b.set(0, 1)
    b.set(1, 3)
    assert a.compare(b) < 0  # [1,2] < [1,3]

    # Test different first element
    a.set(0, 2)
    assert a.compare(b) > 0  # [2,2] > [1,3]

    # Test equal arrays
    b.set(0, 2)
    b.set(1, 2)
    assert a.compare(b) == 0  # [2,2] == [2,2]


def test_zero_termination():
    """Test comparison with zero values (null termination logic)"""
    a = Packed5Array()
    b = Packed5Array()

    # Both empty should be equal
    assert a.compare(b) == 0

    # Test with zeros in the middle
    a.set(0, 1)
    a.set(1, 0)  # explicit zero
    a.set(2, 2)

    b.set(0, 1)
    b.set(1, 0)  # explicit zero
    b.set(2, 3)

    # Should compare as [1,0,2] vs [1,0,3]
    assert a.compare(b) < 0


def test_path_like_comparison():
    """Test comparison that mimics the WordPath usage pattern"""
    a = Packed5Array()
    b = Packed5Array()

    # Simulate path [(0,0), (1,0), (2,0)] -> [1,1,2,1,3,1] (1-indexed)
    a.set(0, 1)  # cell 0 + 1
    a.set(1, 1)  # letter 0 + 1
    a.set(2, 2)  # cell 1 + 1
    a.set(3, 1)  # letter 0 + 1
    a.set(4, 3)  # cell 2 + 1
    a.set(5, 1)  # letter 0 + 1

    # Simulate path [(0,0), (1,0), (2,1)] -> [1,1,2,1,3,2]
    b.set(0, 1)  # cell 0 + 1
    b.set(1, 1)  # letter 0 + 1
    b.set(2, 2)  # cell 1 + 1
    b.set(3, 1)  # letter 0 + 1
    b.set(4, 3)  # cell 2 + 1
    b.set(5, 2)  # letter 1 + 1

    assert a.compare(b) < 0  # [1,1,2,1,3,1] < [1,1,2,1,3,2]


def test_consistency_with_list():
    """Test that packed array comparison matches Python list comparison"""
    import random

    random.seed(2025)
    for _ in range(50):  # Test multiple random cases
        a = Packed5Array()
        b = Packed5Array()
        list_a = []
        list_b = []

        # Generate random arrays of length 8
        length = 8
        for i in range(length):
            val_a = random.randint(0, 31)
            val_b = random.randint(0, 31)

            a.set(i, val_a)
            b.set(i, val_b)
            list_a.append(val_a)
            list_b.append(val_b)

        # Compare results
        packed_result = a.compare(b)
        list_result = 0
        if list_a < list_b:
            list_result = -1
        elif list_a > list_b:
            list_result = 1

        assert packed_result == list_result, (
            f"Mismatch: {list_a} vs {list_b}, packed={packed_result}, list={list_result}"
        )
