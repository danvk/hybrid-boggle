#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

using std::string;
using std::vector;

#include "boggler.h"
#include "eval_node.h"
#include "ibuckets.h"
#include "orderly_tree_builder.h"
#include "trie.h"

// See https://stackoverflow.com/a/47749076/388951
template <int M, int N>
void declare_bucket_boggler(py::module &m, const string &pyclass_name) {
  using BB = BucketBoggler<M, N>;
  // TODO: do I care about buffer_protocol() here?
  py::class_<BB>(m, pyclass_name.c_str(), py::buffer_protocol())
      .def(py::init<Trie *>())
      .def("ParseBoard", &BB::ParseBoard)
      .def("UpperBound", &BB::UpperBound)
      .def("as_string", &BB::as_string)
      .def("Details", &BB::Details)
      .def("NumReps", &BB::NumReps);
}

template <typename TB>
void declare_tree_builder(py::module &m, const string &pyclass_name) {
  // TODO: do I care about buffer_protocol() here?
  py::class_<TB>(m, pyclass_name.c_str(), py::buffer_protocol())
      .def(py::init<Trie *>())
      .def(
          "BuildTree",
          &TB::BuildTree,
          py::return_value_policy::reference,
          py::arg("arena"),
          py::arg("dedupe") = false
      )
      .def("ParseBoard", &TB::ParseBoard)
      .def("as_string", &TB::as_string)
      .def("SumUnion", &TB::SumUnion)
      .def("NumReps", &TB::NumReps)
      .def("create_arena", &TB::CreateArena);
}

template <int M, int N>
void declare_boggler(py::module &m, const string &pyclass_name) {
  using BB = Boggler<M, N>;
  // TODO: do I care about buffer_protocol() here?
  py::class_<BB>(m, pyclass_name.c_str(), py::buffer_protocol())
      .def(py::init<Trie *>())
      .def("score", &BB::Score)
      .def("cell", &BB::Cell)
      .def("set_cell", &BB::SetCell);
}

// PYBIND11_MAKE_OPAQUE(EvalNode);
// PYBIND11_MAKE_OPAQUE(vector<EvalNode*>);

PYBIND11_MODULE(cpp_boggle, m) {
  m.doc() = "C++ Boggle Solving Tools";

  // TODO: add docstrings for all methods
  py::class_<Trie>(m, "Trie")
      .def(py::init())
      .def("StartsWord", &Trie::StartsWord)
      .def("Descend", &Trie::Descend, py::return_value_policy::reference)
      .def("IsWord", &Trie::IsWord)
      .def("Mark", py::overload_cast<>(&Trie::Mark))
      .def("SetMark", py::overload_cast<uintptr_t>(&Trie::Mark))
      // Possible that these should be ::reference_internal instead. See
      // https://pybind11.readthedocs.io/en/stable/advanced/functions.html#return-value-policies
      .def("AddWord", &Trie::AddWord, py::return_value_policy::reference)
      .def("FindWord", &Trie::FindWord, py::return_value_policy::reference)
      .def("Size", &Trie::Size)
      .def("NumNodes", &Trie::NumNodes)
      .def("SetAllMarks", &Trie::SetAllMarks)
      .def_static(
          "ReverseLookup",
          py::overload_cast<const Trie *, const Trie *>(&Trie::ReverseLookup)
      )
      .def_static("CreateFromFile", &Trie::CreateFromFile)
      .def_static("CreateFromFileWithGrouping", &Trie::CreateFromFileWithGrouping);

  declare_boggler<3, 3>(m, "Boggler33");
  declare_boggler<3, 4>(m, "Boggler34");
  declare_boggler<4, 4>(m, "Boggler44");
  declare_boggler<5, 5>(m, "Boggler55");

  declare_bucket_boggler<3, 3>(m, "BucketBoggler33");
  declare_bucket_boggler<3, 4>(m, "BucketBoggler34");
  declare_bucket_boggler<4, 4>(m, "BucketBoggler44");

  declare_tree_builder<OrderlyTreeBuilder<2, 2>>(m, "OrderlyTreeBuilder22");
  declare_tree_builder<OrderlyTreeBuilder<3, 3>>(m, "OrderlyTreeBuilder33");
  declare_tree_builder<OrderlyTreeBuilder<3, 4>>(m, "OrderlyTreeBuilder34");
  declare_tree_builder<OrderlyTreeBuilder<4, 4>>(m, "OrderlyTreeBuilder44");

  py::class_<ScoreDetails>(m, "ScoreDetails", py::buffer_protocol())
      .def_readwrite("max_nomark", &ScoreDetails::max_nomark)
      .def_readwrite("sum_union", &ScoreDetails::sum_union)
      .def_readwrite("bailout_cell", &ScoreDetails::bailout_cell);

  py::class_<EvalNode>(m, "EvalNode")
      .def_readonly("letter", &EvalNode::letter_)
      .def_readonly("cell", &EvalNode::cell_)
      .def_readonly("bound", &EvalNode::bound_)
      .def_readonly("children", &EvalNode::children_)
      .def_readonly("points", &EvalNode::points_)
      .def("score_with_forces", &EvalNode::ScoreWithForces)
      .def("node_count", &EvalNode::NodeCount)
      .def("unique_node_count", &EvalNode::UniqueNodeCount)
      .def("add_word", &EvalNode::AddWord)
      .def(
          "orderly_force_cell",
          &EvalNode::OrderlyForceCell,
          py::return_value_policy::reference,
          py::arg("cell"),
          py::arg("num_lets"),
          py::arg("arena")
      )
      .def("structural_hash", &EvalNode::StructuralHash)
      .def("orderly_bound", &EvalNode::OrderlyBound);

  m.def("create_eval_node_arena", &create_eval_node_arena);
  py::class_<EvalNodeArena>(m, "EvalNodeArena")
      .def(py::init())
      .def("free_the_children", &EvalNodeArena::FreeTheChildren)
      .def(
          "new_node_with_capacity",
          &EvalNodeArena::NewNodeWithCapcity,
          py::return_value_policy::reference
      )
      .def("num_nodes", &EvalNodeArena::NumNodes);
}
