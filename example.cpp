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
        .def(py::init())
        .def("AddWord", &Trie::AddWord)
        .def("FindWord", &Trie::FindWord)
        .def("Size", &Trie::Size)
        .def("NumNodes", &Trie::NumNodes)
        .def_static("CreateFromFile", &Trie::CreateFromFile);
}
