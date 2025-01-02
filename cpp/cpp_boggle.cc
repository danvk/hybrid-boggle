#include <pybind11/pybind11.h>
namespace py = pybind11;

#include "trie.h"
#include "boggler.h"
#include "ibuckets.h"

PYBIND11_MODULE(cpp_boggle, m)
{
    m.doc() = "C++ Boggle Solving Tools";

    // TODO: add docstrings for all methods
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

    using BucketBoggler34 = BucketBoggler<3, 4>;
    py::class_<BucketBoggler34>(m, "BucketBoggler34")
        .def(py::init<Trie*>())
        .def("ParseBoard", &BucketBoggler34::ParseBoard)
        .def("UpperBound", &BucketBoggler34::UpperBound)
        .def("as_string",  &BucketBoggler34::as_string)
        .def("Cell",    &BucketBoggler34::Cell)
        .def("SetCell", &BucketBoggler34::SetCell)
        .def("Details", &BucketBoggler34::Details)
        .def("NumReps", &BucketBoggler34::NumReps);

    py::class_<ScoreDetails>(m, "ScoreDetails")
        .def_readwrite("max_nomark", &ScoreDetails::max_nomark)
        .def_readwrite("sum_union", &ScoreDetails::sum_union);
}
