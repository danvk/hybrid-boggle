#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

using std::string;
using std::vector;

#include "arena.h"
#include "boggler.h"
#include "eval_node.h"
#include "ibuckets.h"
#include "orderly_tree_builder.h"
#include "symmetry.h"
#include "trie.h"

// See https://stackoverflow.com/a/47749076/388951
template <int M, int N>
void declare_bucket_boggler(py::module &m, const string &pyclass_name) {
  using BB = BucketBoggler<M, N>;
  py::class_<BB>(m, pyclass_name.c_str())
      .def(py::init<Trie *>())
      .def("parse_board", &BB::ParseBoard)
      .def("upper_bound", &BB::UpperBound)
      .def("as_string", &BB::as_string)
      .def("details", &BB::Details)
      .def("num_reps", &BB::NumReps);
}

template <typename TB>
void declare_tree_builder(py::module &m, const string &pyclass_name) {
  py::class_<TB>(m, pyclass_name.c_str())
      .def(py::init<Trie *>())
      .def(
          "build_tree",
          &TB::BuildTree,
          py::return_value_policy::reference,
          py::arg("arena")
      )
      .def("parse_board", &TB::ParseBoard)
      .def("as_string", &TB::as_string)
      .def("num_reps", &TB::NumReps)
      .def("create_arena", &TB::CreateArena);
}

template <int M, int N>
void declare_boggler(py::module &m, const string &pyclass_name) {
  using BB = Boggler<M, N>;
  py::class_<BB>(m, pyclass_name.c_str())
      .def(py::init<Trie *>())
      .def("score", &BB::Score)
      .def("find_words", &BB::FindWords)
      .def("cell", &BB::Cell)
      .def("set_cell", &BB::SetCell);
}

PYBIND11_MODULE(cpp_boggle, m) {
  m.doc() = "C++ Boggle Solving Tools";

  // TODO: add docstrings for all methods
  py::class_<Trie>(m, "Trie")
      .def(py::init())
      .def("starts_word", &Trie::StartsWord)
      .def("descend", &Trie::Descend, py::return_value_policy::reference)
      .def("is_word", &Trie::IsWord)
      .def("mark", py::overload_cast<>(&Trie::Mark))
      .def("set_mark", py::overload_cast<uintptr_t>(&Trie::Mark))
      // Possible that these should be ::reference_internal instead. See
      // https://pybind11.readthedocs.io/en/stable/advanced/functions.html#return-value-policies
      .def("add_word", &Trie::AddWord, py::return_value_policy::reference)
      .def("find_word", &Trie::FindWord, py::return_value_policy::reference)
      .def("size", &Trie::Size)
      .def("num_nodes", &Trie::NumNodes)
      .def("reset_marks", &Trie::ResetMarks)
      .def("set_all_marks", &Trie::SetAllMarks)
      .def_static(
          "reverse_lookup",
          py::overload_cast<const Trie *, const Trie *>(&Trie::ReverseLookup)
      )
      .def_static("create_from_file", &Trie::CreateFromFile);

  declare_boggler<2, 2>(m, "Boggler22");
  declare_boggler<2, 3>(m, "Boggler23");
  declare_boggler<3, 3>(m, "Boggler33");
  declare_boggler<3, 4>(m, "Boggler34");
  declare_boggler<4, 4>(m, "Boggler44");
  declare_boggler<4, 5>(m, "Boggler45");
  declare_boggler<5, 5>(m, "Boggler55");

  declare_bucket_boggler<2, 2>(m, "BucketBoggler22");
  declare_bucket_boggler<2, 3>(m, "BucketBoggler23");
  declare_bucket_boggler<3, 3>(m, "BucketBoggler33");
  declare_bucket_boggler<3, 4>(m, "BucketBoggler34");
  declare_bucket_boggler<4, 4>(m, "BucketBoggler44");
  declare_bucket_boggler<4, 5>(m, "BucketBoggler45");
  declare_bucket_boggler<5, 5>(m, "BucketBoggler55");

  declare_tree_builder<OrderlyTreeBuilder<2, 2>>(m, "OrderlyTreeBuilder22");
  declare_tree_builder<OrderlyTreeBuilder<2, 3>>(m, "OrderlyTreeBuilder23");
  declare_tree_builder<OrderlyTreeBuilder<3, 3>>(m, "OrderlyTreeBuilder33");
  declare_tree_builder<OrderlyTreeBuilder<3, 4>>(m, "OrderlyTreeBuilder34");
  declare_tree_builder<OrderlyTreeBuilder<4, 4>>(m, "OrderlyTreeBuilder44");
  declare_tree_builder<OrderlyTreeBuilder<4, 5>>(m, "OrderlyTreeBuilder45");
  declare_tree_builder<OrderlyTreeBuilder<5, 5>>(m, "OrderlyTreeBuilder55");

  py::class_<ScoreDetails>(m, "ScoreDetails")
      .def_readwrite("max_nomark", &ScoreDetails::max_nomark)
      .def_readwrite("sum_union", &ScoreDetails::sum_union)
      .def_readwrite("bailout_cell", &ScoreDetails::bailout_cell);

  py::class_<SumNode>(m, "SumNode")
      .def_readonly("letter", &SumNode::letter_)
      .def_property_readonly("bound", &SumNode::Bound)
      .def_readonly("points", &SumNode::points_)
      .def("node_count", &SumNode::NodeCount)
      .def("add_word_with_points_for_testing", &SumNode::AddWordWithPointsForTesting)
      .def("decode_points_and_bound", &SumNode::DecodePointsAndBound)
      .def(
          "orderly_force_cell",
          &SumNode::OrderlyForceCell,
          py::return_value_policy::reference,
          py::arg("cell"),
          py::arg("num_lets"),
          py::arg("arena")
      )
      .def("get_children", &SumNode::GetChildren, py::return_value_policy::reference)
      .def("score_with_forces", &SumNode::ScoreWithForces)
      .def("orderly_bound", &SumNode::OrderlyBound);

  py::class_<ChoiceNode>(m, "ChoiceNode")
      .def_readonly("bound", &ChoiceNode::bound_)
      .def_readonly("cell", &ChoiceNode::cell_)
      .def("node_count", &ChoiceNode::NodeCount)
      .def(
          "get_children", &ChoiceNode::GetChildren, py::return_value_policy::reference
      );

  m.def("create_eval_node_arena", &create_eval_node_arena);
  py::class_<EvalNodeArena>(m, "EvalNodeArena")
      .def(py::init())
      .def(
          "new_root_node_with_capacity",
          &EvalNodeArena::NewRootNodeWithCapacity,
          py::return_value_policy::reference
      )
      .def("save_level", &EvalNodeArena::SaveLevel)
      .def("reset_level", &EvalNodeArena::ResetLevel)
      .def("num_nodes", &EvalNodeArena::NumNodes)
      .def("bytes_allocated", &EvalNodeArena::BytesAllocated);

  py::class_<Symmetry>(m, "Symmetry")
      .def(py::init<int, int>())
      .def("canonicalize", &Symmetry::Canonicalize);
}
