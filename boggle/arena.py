# An Arena isn't particularly useful in Python, but this
# maintains identical APIs between EvalNode methods in Python & C++.


class PyArena:
    """This class is useless, but it helps maintain the same API as C++."""

    def __init__(self):
        self.count = 0

    def free_the_children(self):
        pass

    def num_nodes(self):
        return self.count

    def new_node_with_capacity(self, n: int):
        from boggle.eval_tree import ROOT_NODE, EvalNode

        n = EvalNode()
        n.letter = ROOT_NODE
        n.cell = 0
        n.bound = 0
        n.points = 0
        self.count += 1
        return n

    def new_root_node_with_capacity(self, n: int):
        return self.new_node_with_capacity(n)

    def add_node(self, node):
        self.count += 1


def create_eval_node_arena_py():
    return PyArena()
