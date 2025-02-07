"""Encode bucket boggle as a constraint problem."""

import json
import sys
from collections import defaultdict

from boggle.boggler import LETTER_A, LETTER_Q, SCORES
from boggle.eval_tree import CHOICE_NODE, EvalNode, EvalTreeBoggler
from boggle.neighbors import NEIGHBORS
from boggle.trie import PyTrie, make_lookup_table, make_py_trie

MARK = 2


def collect_equations(t: EvalNode, cells, eqs: list, id_to_node):
    if t.cache_key == MARK:
        return t.cache_value

    # TODO: could use trie nodes to get word labels for pointy sum nodes
    # TODO: could do a form of DAG optimization here to reduce # of equations
    if t.letter == CHOICE_NODE:
        choices = []
        for c in t.children:
            if c:
                letter_id = f"{cells[c.cell][c.letter]}{c.cell}"
                child_id = collect_equations(c, cells, eqs, id_to_node)
                choices.append((letter_id, child_id))
        if len(choices) == 1 and choices[0][1] == 1:
            t.cache_key = MARK
            t.cache_value = choices[0][0]
            return choices[0][0]
        me_id = f"n_{len(eqs)}"
        eqs.append((me_id, "choice", choices))
    else:
        # sum node
        terms = [t.points] if t.points else []
        for c in t.children:
            if c:
                child_id = collect_equations(c, cells, eqs, id_to_node)
                terms.append(child_id)
        if len(terms) > 1:
            me_id = f"n_{len(eqs)}"
            eqs.append((me_id, "sum", terms))
        else:
            t.cache_key = MARK
            t.cache_value = terms[0]
            return terms[0]

    id_to_node[me_id] = t
    t.cache_key = MARK
    t.cache_value = me_id
    return me_id


def to_cmsat(cells, best_score: int, root_id, eqs):
    # lookup = make_lookup_table(trie)
    # declare variables
    # choices
    for i, cell in enumerate(cells):
        vars = []
        for letter in cell:
            var = f"{letter}{i}"
            vars.append(var)
            print(f"(declare-const {var} Bool)")
        if len(vars) > 1:
            print(f"(assert (= (+ {' '.join(vars)}) 1))")

    # words
    terms = []
    for eq_id, eq_type, terms in eqs:
        if eq_type == "sum":
            impl = f"(+ {' '.join(str(t) for t in terms)})"
        else:
            products = []
            for letter_id, term_id in terms:
                if term_id == 1:
                    products.append(letter_id)
                else:
                    products.append(f"(* {letter_id} {term_id})")

            impl = f"(+ {' '.join(products)})"
        print(f"(define-fun {eq_id} () Int {impl})")

    print(f"(assert (> {root_id} {best_score}))")
    print("(check-sat)")
    # print("(get-model)")


def to_ortools(cells, best_score: int, root_id, eqs, eq_id_to_node):
    print("from ortools.sat.python import cp_model")
    print("model = cp_model.CpModel()")
    print("cells = []")
    for i, cell in enumerate(cells):
        vars = []
        vars_dict = {}
        for letter in cell:
            var = f"{letter}{i}"
            vars.append(var)
            vars_dict[letter] = var
            print(f"{var} = model.new_bool_var('{var}')")
        if len(vars) > 1:
            # print(f"model.add({'+'.join(vars)} == 1)")
            print(f"model.AddExactlyOne({', '.join(vars)})")
        vd = ",".join(f'"{let}": {v}' for let, v in vars_dict.items())
        print("cells.append({%s})" % vd)

    # (a, b) -> equation for a*b
    product_eqs = {}

    for eq_id, eq_type, terms in eqs:
        n = eq_id_to_node[eq_id]
        if eq_type == "sum":
            eq = "+".join(str(t) for t in terms)
        else:
            products = []
            for letter_id, term_id in terms:
                if term_id == 1:
                    products.append(letter_id)
                else:
                    if isinstance(term_id, int):
                        prod_id = f"({letter_id} * {term_id})"
                    else:
                        key = (
                            (letter_id, term_id)
                            if letter_id < term_id
                            else (term_id, letter_id)
                        )
                        prod_id = product_eqs.get(key)
                        if prod_id is None:
                            prod_id = f"p_{len(product_eqs)}"
                            product_eqs[key] = prod_id
                            term_node = eq_id_to_node.get(term_id)
                            if term_node:
                                bound = term_node.bound
                            else:
                                bound = 1
                            print(
                                f"{prod_id} = model.new_int_var(0, {bound}, '{prod_id}')"
                            )
                            print(
                                f"model.add_multiplication_equality({prod_id}, ({letter_id}, {term_id}))"
                            )
                    # TODO: if len(products) == 1, can simplify
                    products.append(prod_id)
            eq = "+".join(products)
        print(f"{eq_id} = model.new_int_var(0, {n.bound}, '{eq_id}')")
        print(f"model.add({eq_id} == {eq})")

    print(f"model.add({root_id} >= {best_score})")
    print(
        """
solver = cp_model.CpSolver()
status = solver.solve(model)

status = {
    cp_model.OPTIMAL: "optimal",
    cp_model.FEASIBLE: "feasible",
    cp_model.INFEASIBLE: "infeasible",
    cp_model.MODEL_INVALID: "model_invalid",
    cp_model.UNKNOWN: "unknown",
}[status]
print(status)
print('value:', solver.value(%s))

letters = [letter for cell in cells for letter, v in cell.items() if solver.value(v)]
print(" ".join(letters))
"""
        % root_id
    )


def to_py(cells: list[str], cutoff, root_id, eqs):
    print("import itertools\n")
    print("def w(" + ", ".join(f"c{i}" for i in range(len(cells))) + "):")
    for i, cell in enumerate(cells):
        vars = []
        for letter in cell:
            var = f"{letter}{i}"
            vars.append(var)
        if len(vars) > 1:
            print(f'    {",".join(vars)} = c{i}')
    for eq_id, eq_type, terms in eqs:
        print(f"    {eq_id}=", end="")
        if eq_type == "sum":
            print("+".join(str(t) for t in terms))
        else:
            products = []
            for letter_id, term_id in terms:
                if term_id == 1:
                    products.append(letter_id)
                else:
                    products.append(f"({letter_id}*{term_id})")
            print("+".join(products))
    print(f"    return {root_id}")

    counts = ", ".join(str(len(c)) for c in cells)
    print(f"counts = ({counts})")
    print("""
c = [[False] * n for n in counts]

best_score = 0

for idxs in itertools.product(*(range(n) for n in counts)):
    for i, idx in enumerate(idxs):
        c[i][idx] = True
    score = w(*c)
    best_score = max(score, best_score)
    for i, idx in enumerate(idxs):
        c[i][idx] = False

print(best_score)
""")


def main():
    # trie = PyTrie()
    # trie.AddWord("tar")
    # trie.AddWord("tie")
    # trie.AddWord("tier")
    # trie.AddWord("tea")
    # trie.AddWord("the")
    # trie = make_py_trie("mini-dict.txt")
    (
        cutoff_str,
        board,
    ) = sys.argv[1:]
    trie = make_py_trie("boggle-words.txt")
    cutoff = int(cutoff_str)
    cells = board.split(" ")
    dims = {
        4: (2, 2),
        6: (2, 3),
        9: (3, 3),
        12: (3, 4),
        16: (4, 4),
    }[len(cells)]
    etb = EvalTreeBoggler(trie, dims)
    assert etb.ParseBoard(board)
    tree = etb.BuildTree(None, dedupe=True)
    eqs = []
    eq_id_to_node = {}
    root_id = collect_equations(tree, cells, eqs, eq_id_to_node)
    sys.stderr.write(f"eq count: {len(eqs)}\n")
    # print(eqs)
    # print("---\n")
    # to_cmsat(cells, cutoff, root_id, eqs)
    to_py(cells, cutoff, root_id, eqs)
    # to_ortools(cells, cutoff, root_id, eqs, eq_id_to_node)


if __name__ == "__main__":
    main()
