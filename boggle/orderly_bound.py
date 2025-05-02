from collections import Counter
from typing import Sequence

from cpp_boggle import (
    orderly_bound22,
    orderly_bound33,
    orderly_bound34,
    orderly_bound44,
)

from boggle.boggler import PyBoggler
from boggle.eval_node import ChoiceNode, SumNode


def py_orderly_bound(
    base_node: SumNode,
    cutoff: int,
    cells: list[str],
    split_order: Sequence[int],
    preset_cells: Sequence[tuple[int, int]],
    boggler: PyBoggler,
):
    """Find individual high-scoring boards in this tree without creating new nodes.

    See https://www.danvk.org/2025/04/10/following-insight.html#orderly-bound
    """
    num_letters = [len(cell) for cell in cells]
    stacks: list[list[ChoiceNode]] = [[] for _ in num_letters]
    choices = []  # for tracking unbreakable boards
    failures: list[str] = []
    # max_lens: list[int] = [0] * len(stacks)
    n_preset = len(preset_cells)
    elim_at_level = [0] * (1 + len(cells) - n_preset)
    visit_at_level = [0] * (1 + len(cells) - n_preset)

    num_visits = Counter[SumNode]()

    def advance(node: SumNode, sums: list[int]):
        num_visits[node] += 1
        for child in node.children:
            stacks[child.cell].append(child)
            sums[child.cell] += child.bound
        return node.points

    def record_failure(bound: int):
        bd = [None] * len(num_letters)
        for cell, letter in preset_cells:
            bd[cell] = cells[cell][letter]
        for cell, letter in choices:
            bd[cell] = cells[cell][letter]
        board = "".join(bd)
        nonlocal failures
        failures.append((bound, board))

    def rec(base_points: int, num_splits: int, stack_sums: list[int]):
        bound = base_points + sum(stack_sums[cell] for cell in split_order[num_splits:])
        if bound <= cutoff:
            elim_at_level[num_splits] += 1
            return  # done!
        if num_splits == len(split_order):
            record_failure(bound)
            return

        # need to advance; try each possibility in turn.
        next_to_split = split_order[num_splits]
        stack_top = [len(stack) for stack in stacks]
        base_sums = [*stack_sums]
        for letter in range(0, num_letters[next_to_split]):
            if letter > 0:
                for i, v in enumerate(base_sums):
                    stack_sums[i] = v
                for i, length in enumerate(stack_top):
                    stacks[i] = stacks[i][:length]
            choices.append((next_to_split, letter))
            points = base_points
            for node in stacks[next_to_split]:
                letter_node = None
                for n in node.children:
                    if n.letter == letter:
                        letter_node = n
                        break
                if letter_node:
                    visit_at_level[1 + num_splits] += 1
                    points += advance(letter_node, stack_sums)

            rec(points, num_splits + 1, stack_sums)
            # reset the stacks
            choices.pop()

    sums = [0] * len(num_letters)
    visit_at_level[0] += 1
    base_points = advance(base_node, sums)
    rec(base_points, 0, sums)
    base_node.num_visits = num_visits  # for visualizing backtracking behavior
    return failures, visit_at_level, elim_at_level


def orderly_bound(
    tree: SumNode,
    dims: tuple[int, int],
    cutoff: int,
    cells: list[str],
    split_order: Sequence[int],
    preset_cells: Sequence[tuple[int, int]],
    boggler: PyBoggler,
):
    """Call either the C++ or Python orderly_bound function."""
    if isinstance(boggler, PyBoggler):
        return py_orderly_bound(tree, cutoff, cells, split_order, preset_cells, boggler)
    if dims == (2, 2):
        return orderly_bound22(tree, cutoff, cells, split_order, preset_cells, boggler)
    elif dims == (3, 3):
        return orderly_bound33(tree, cutoff, cells, split_order, preset_cells, boggler)
    elif dims == (3, 4):
        return orderly_bound34(tree, cutoff, cells, split_order, preset_cells, boggler)
    elif dims == (4, 4):
        return orderly_bound44(tree, cutoff, cells, split_order, preset_cells, boggler)
    elif dims == (5, 5):
        return orderly_bound44(tree, cutoff, cells, split_order, preset_cells, boggler)
    raise ValueError(f"Invalid dims {dims}")
