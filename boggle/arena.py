# An Arena isn't particularly useful in Python, but this
# maintains identical APIs between EvalNode methods in Python & C++.


class PyArena:
    """This class is useless, but it helps maintain the same API as C++."""

    def __init__(self):
        self.count = 0

    def num_nodes(self):
        return self.count

    def bytes_allocated(self):
        return self.count * 32

    def new_sum_node_with_capacity(self, n: int):
        from boggle.eval_node import SumNode

        n = SumNode()
        n.bound = 0
        n.points = 0
        self.count += 1
        return n

    def new_choice_node_with_capacity(self, n: int):
        from boggle.eval_node import ChoiceNode

        n = ChoiceNode()
        n.bound = 0
        self.count += 1
        return n

    def add_node(self, node):
        self.count += 1

    def save_level(self):
        return (0, 0)

    def reset_level(self, level):
        pass


def create_eval_node_arena_py():
    return PyArena()
