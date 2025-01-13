#include <pybind11/pybind11.h>
namespace py = pybind11;

using std::string;

#include "trie.h"
#include "boggler.h"
#include "ibuckets.h"

// See https://stackoverflow.com/a/47749076/388951
template<int M, int N>
void declare_bucket_boggler(py::module &m, const string &pyclass_name) {
    using BB = BucketBoggler<M, N>;
    // TODO: do I care about buffer_protocol() here?
    py::class_<BB>(m, pyclass_name.c_str(), py::buffer_protocol())
        .def(py::init<Trie*>())
        .def("ParseBoard", &BB::ParseBoard)
        .def("UpperBound", &BB::UpperBound)
        .def("as_string",  &BB::as_string)
        .def("Cell",    &BB::Cell)
        .def("SetCell", &BB::SetCell)
        .def("Details", &BB::Details)
        .def("NumReps", &BB::NumReps);
}

PYBIND11_MODULE(cpp_boggle, m)
{
    m.doc() = "C++ Boggle Solving Tools";

    // TODO: add docstrings for all methods
    py::class_<Trie>(m, "Trie")
        .def(py::init())
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
        .def("SetAllMarks", &Trie::SetAllMarks)
        .def_static("ReverseLookup", py::overload_cast<const Trie*, const Trie*>(&Trie::ReverseLookup))
        .def_static("CreateFromFile", &Trie::CreateFromFile);

    py::class_<Boggler>(m, "Boggler")
        .def(py::init<Trie*>())
        .def("Score", &Boggler::Score);

    declare_bucket_boggler<3, 3>(m, "BucketBoggler33");
    declare_bucket_boggler<3, 4>(m, "BucketBoggler34");
    declare_bucket_boggler<4, 4>(m, "BucketBoggler44");

    py::class_<ScoreDetails>(m, "ScoreDetails", py::buffer_protocol())
        .def_readwrite("max_nomark", &ScoreDetails::max_nomark)
        .def_readwrite("sum_union", &ScoreDetails::sum_union)
        .def_readwrite("bailout_cell", &ScoreDetails::bailout_cell);
}
