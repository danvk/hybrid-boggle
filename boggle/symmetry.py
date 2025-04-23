# Calculate all symmetries for 2D matrices.
#
# TODO: this may not be in sync w/ board_id.py

from itertools import chain

from boggle.dimensional_bogglers import LEN_TO_DIMS


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


def all_symmetries[T](mat: list[list[T]]):
    """Return all symmetries of a 2D matrix."""
    fy = flip_y(mat)
    flips = [
        flip_x(mat),
        fy,
        flip_x(fy),
    ]
    if len(mat) != len(mat[0]):
        return flips
    r90 = rot90(mat)
    r90fy = flip_y(r90)
    return [*flips, r90, flip_x(r90), r90fy, flip_x(r90fy)]


def mat_to_str[T](mat: list[list[T]]):
    """Convert a 2D matrix to a string."""
    return "".join("".join(str(v) for v in row) for row in mat)


def list_to_matrix(letters):
    w, h = LEN_TO_DIMS[len(letters)]

    bd_2d = [[0 for _y in range(0, h)] for _x in range(0, w)]
    for i in range(0, len(letters)):
        bd_2d[i // h][i % h] = letters[i]
    return bd_2d


def canonicalize[T](mat: list[list[T]]):
    """Return the canonical form of a 2D matrix."""
    return min(chain([mat], all_symmetries(mat)), key=mat_to_str)


def canonicalize_board(bd: str):
    return mat_to_str(canonicalize(list_to_matrix(bd)))
