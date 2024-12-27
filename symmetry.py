# Calculate all symmetries for 2D matrices.

from itertools import chain


def rot90[T](mat: list[list[T]]):
    """Rotate an NxM matrix 90 degrees clockwise."""
    n = len(mat)
    m = len(mat[0])
    return [[mat[n - 1 - j][i] for j in range(n)] for i in range(m)]


def flip_x[T](mat: list[list[T]]):
    """Flip an NxM matrix along the x-axis."""
    return mat[::-1]


def flip_y[T](mat: list[list[T]]):
    """Flip an NxM matrix along the y-axis."""
    return [row[::-1] for row in mat]


def all_symmetries[T](mat: list[list[T]], no_rotations=False):
    """Return all symmetries of a 2D matrix."""
    fy = flip_y(mat)
    flips = [
        flip_x(mat),
        fy,
        flip_x(fy),
    ]
    if no_rotations:
        return flips
    r90 = rot90(mat)
    r90fy = flip_y(r90)
    return [
        *flips,
        r90,
        flip_x(r90),
        r90fy,
        flip_x(r90fy)
    ]


def mat_to_str[T](mat: list[list[T]]):
    """Convert a 2D matrix to a string."""
    return '\n'.join(' '.join(str(row) for row in mat))


def canonicalize[T](mat: list[list[T]]):
    """Return the canonical form of a 2D matrix."""
    return min(chain([mat], all_symmetries(mat)), key=mat_to_str)
