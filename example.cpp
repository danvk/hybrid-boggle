#include <pybind11/pybind11.h>
namespace py = pybind11;

#include "trie.h"
#include "boggler.h"
#include "ibuckets.h"

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
        .def("Mark", py::overload_cast<>(&Trie::Mark))
        .def("SetMark", py::overload_cast<uintptr_t>(&Trie::Mark))
        // Possible that these should be ::reference_internal instead
        // See https://pybind11.readthedocs.io/en/stable/advanced/functions.html#return-value-policies
        .def("AddWord", &Trie::AddWord, py::return_value_policy::reference)
        .def("FindWord", &Trie::FindWord, py::return_value_policy::reference)
        .def("Size", &Trie::Size)
        .def("NumNodes", &Trie::NumNodes)
        .def_static("ReverseLookup", py::overload_cast<const Trie*, const Trie*>(&Trie::ReverseLookup))
        .def_static("CreateFromFile", &Trie::CreateFromFile);

    py::class_<Boggler>(m, "Boggler")
        .def(py::init<Trie*>())
        .def("Score", &Boggler::Score);

    using BucketBoggler33 = BucketBoggler<3, 3>;
    py::class_<BucketBoggler33>(m, "BucketBoggler33")
        .def(py::init<Trie*>())
        .def("ParseBoard", &BucketBoggler33::ParseBoard)
        .def("UpperBound", &BucketBoggler33::UpperBound)
        .def("as_string",  &BucketBoggler33::as_string)
        .def("Cell",    &BucketBoggler33::Cell)
        .def("SetCell", &BucketBoggler33::SetCell)
        .def("Details", &BucketBoggler33::Details)
        .def("NumReps", &BucketBoggler33::NumReps);

    py::class_<ScoreDetails>(m, "ScoreDetails")
        .def_readwrite("max_nomark", &ScoreDetails::max_nomark)
        .def_readwrite("sum_union", &ScoreDetails::sum_union);
}
