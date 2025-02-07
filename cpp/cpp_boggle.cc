#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

using std::string;
using std::vector;

#include "trie.h"
#include "boggler.h"
#include "ibuckets.h"
#include "eval_node.h"
#include "tree_builder.h"
// #include "breaker.h"

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

template<int M, int N>
void declare_tree_builder(py::module &m, const string &pyclass_name) {
    using BB = TreeBuilder<M, N>;
    // TODO: do I care about buffer_protocol() here?
    py::class_<BB>(m, pyclass_name.c_str(), py::buffer_protocol())
        .def(py::init<Trie*>())
        .def("BuildTree", &BB::BuildTree, py::return_value_policy::reference)
        .def("ParseBoard", &BB::ParseBoard)
        .def("as_string",  &BB::as_string)
        .def("Cell",    &BB::Cell)
        .def("SetCell", &BB::SetCell)
        .def("Details", &BB::Details)
        .def("NumReps", &BB::NumReps);
}

template<int M, int N>
void declare_boggler(py::module &m, const string &pyclass_name) {
    using BB = Boggler<M, N>;
    // TODO: do I care about buffer_protocol() here?
    py::class_<BB>(m, pyclass_name.c_str(), py::buffer_protocol())
        .def(py::init<Trie*>())
        .def("score", &BB::Score)
        .def("cell",    &BB::Cell)
        .def("set_cell", &BB::SetCell);
}

// PYBIND11_MAKE_OPAQUE(EvalNode);
// PYBIND11_MAKE_OPAQUE(vector<EvalNode*>);

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

    declare_boggler<2, 3>(m, "Boggler23");
    declare_boggler<3, 3>(m, "Boggler33");
    declare_boggler<3, 4>(m, "Boggler34");
    declare_boggler<4, 4>(m, "Boggler44");

    declare_bucket_boggler<3, 3>(m, "BucketBoggler33");
    declare_bucket_boggler<3, 4>(m, "BucketBoggler34");
    declare_bucket_boggler<4, 4>(m, "BucketBoggler44");

    declare_tree_builder<3, 3>(m, "TreeBuilder33");
    declare_tree_builder<3, 4>(m, "TreeBuilder34");
    declare_tree_builder<4, 4>(m, "TreeBuilder44");

    py::class_<ScoreDetails>(m, "ScoreDetails", py::buffer_protocol())
        .def_readwrite("max_nomark", &ScoreDetails::max_nomark)
        .def_readwrite("sum_union", &ScoreDetails::sum_union)
        .def_readwrite("bailout_cell", &ScoreDetails::bailout_cell);

    py::class_<EvalNode>(m, "EvalNode")
        .def_readonly("letter", &EvalNode::letter)
        .def_readonly("cell", &EvalNode::cell)
        .def_readonly("bound", &EvalNode::bound)
        .def_readonly("choice_mask", &EvalNode::choice_mask)
        .def("score_with_forces", &EvalNode::ScoreWithForces)
        .def("recompute_score", &EvalNode::RecomputeScore)
        .def("node_count", &EvalNode::NodeCount)
        .def("force_cell", &EvalNode::ForceCell, py::return_value_policy::reference);

    m.def("create_eval_node_arena", &create_eval_node_arena);

    py::class_<EvalNodeArena>(m, "EvalNodeArena")
        .def(py::init())
        .def("free_the_children", &EvalNodeArena::FreeTheChildren)
        .def("num_nodes", &EvalNodeArena::NumNodes);

    // py::class_<Breaker>(m, "Breaker")
    //     .def(py::init<TreeBuilder<3,4>*, unsigned int>())
    //     .def("SetBoard", &Breaker::SetBoard)
    //     .def("Break", &Breaker::Break);
}
