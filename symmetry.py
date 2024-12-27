# Calculate all symmetries for 2D matrices.

def rot90[T](mat: list[list[T]]):
    """Rotate an NxM matrix 90 degrees clockwise."""
    n = len(mat)
    m = len(mat[0])
    return [[mat[n - 1 - j][i] for j in range(n)] for i in range(m)]
