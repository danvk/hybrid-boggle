from itertools import permutations

DICE = [
    "aeaneg",
    "ahspco",
    "aspffk",
    "objoab",
    "iotmuc",
    "ryvdel",
    "lreixd",
    "eiunes",
    "wngeeh",
    "lnhnrz",
    "tstiyd",
    "owtoat",
    "erttyl",
    "toessi",
    "terwhv",
    "nuihmq",
]


def count_valid_grids(grid_letters):
    if len(grid_letters) != 16:
        raise ValueError("Grid must be exactly 16 letters")

    count = 0
    dice_indices = range(16)

    for dice_perm in permutations(dice_indices):
        match = True
        for i, die_index in enumerate(dice_perm):
            letter = grid_letters[i].lower()
            die = DICE[die_index]
            if letter not in die:
                match = False
                break
        if match:
            count += 1

    return count


# Example usage:
# Provide a 16-letter string representing the 4x4 grid (row-wise)
grid = "examplegridof16l"  # Replace with actual 16-letter grid
print(count_valid_grids(grid))
