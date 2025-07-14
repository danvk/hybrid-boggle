# Find equal ranges in xs[a:b]
def equal_ranges(xs, a, b):
    if a >= b:
        return []
    first = xs[a]
    last = xs[b - 1]
    if first == last:
        # Complete range; just return this.
        return [(first, a, b)]

    if b - a == 2:
        return [(first, a, a + 1), (last, a + 1, b)]

    mid_idx = a + ((b - a) // 2)
    mid = xs[mid_idx]

    if mid == first:
        # Find equal_ranges for the second half and add to the first range.
        ranges = equal_ranges(xs, mid_idx, b)
        val, start, end = ranges[0]
        assert val == mid
        assert start == mid_idx
        ranges[0] = (val, a, end)
        return ranges
    elif mid == last:
        # Find equal ranges for the back half and add to the last range
        ranges = equal_ranges(xs, a, mid_idx + 1)
        val, start, end = ranges[-1]
        assert val == mid
        assert end == mid_idx + 1
        ranges[-1] = (val, start, b)
        return ranges
    else:
        # Search both halves and smoosh them together
        low_ranges = equal_ranges(xs, a, mid_idx + 1)
        hi_ranges = equal_ranges(xs, mid_idx, b)
        assert mid == low_ranges[-1][0]
        assert low_ranges[-1][0] == hi_ranges[0][0]
        assert low_ranges[-1][2] == hi_ranges[0][1] + 1

        return (
            low_ranges[:-1]
            + [(mid, low_ranges[-1][1], hi_ranges[0][2])]
            + hi_ranges[1:]
        )
