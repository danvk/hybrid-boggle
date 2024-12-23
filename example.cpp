#include <pybind11/pybind11.h>
namespace py = pybind11;

#include "trie.h"

int add(int i, int j)
{
    return i + j;
}

int fib(int n)
{
    int a = 0, b = 1;
    while (b < n) {
        int tmp = b;
        b = a + b;
        a = tmp;
    }
    return a;
}

PYBIND11_MODULE(example, m)
{
    m.doc() = "pybind11 example plugin"; // optional module docstring

    m.def("add", &add, "A function which adds two numbers",
          py::arg("i"), py::arg("j"));

    m.def("fib", &fib, "Largest fibonacci number less than n.");

    py::class_<Trie>(m, "Trie")
        // .def(py::init())
        .def("StartsWord", &Trie::StartsWord)
        .def("Descend", &Trie::Descend, py::return_value_policy::reference)
        .def("IsWord", &Trie::IsWord)
        .def("Mark", static_cast<uintptr_t (Trie::*)()>(&Trie::Mark))
        .def("SetMark", static_cast<void (Trie::*)(uintptr_t)>(&Trie::Mark))
        // Possible that these should be ::reference_internal instead
        // See https://pybind11.readthedocs.io/en/stable/advanced/functions.html#return-value-policies
        .def("AddWord", &Trie::AddWord, py::return_value_policy::reference)
        .def("FindWord", &Trie::FindWord, py::return_value_policy::reference)
        .def("Size", &Trie::Size)
        .def("NumNodes", &Trie::NumNodes)
        .def_static("ReverseLookup", py::overload_cast<const Trie*, const Trie*>(&Trie::ReverseLookup))
        .def_static("CreateFromFile", &Trie::CreateFromFile);
}
