#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "arena.h"
#include "boggler.h"
#include "ibucket_breaker.h"
#include "ibuckets.h"
#include "orderly_tree_builder.h"
#include "trie.h"

namespace py = pybind11;

PYBIND11_MODULE(cpp_boggle, m) {
  m.doc() = "C++ Boggle solver";

  py::class_<Trie>(m, "Trie")
      .def(py::init<const std::string&>())
      .def("starts_word", &Trie::StartsWord)
      .def("is_word", &Trie::IsWord)
      .def("word_id", &Trie::WordId)
      .def("descend", &Trie::Descend, py::return_value_policy::reference);

  py::class_<EvalNodeArena::State>(m, "ArenaState");

  py::class_<EvalNodeArena>(m, "EvalNodeArena")
      .def(py::init<>())
      .def("num_nodes", &EvalNodeArena::NumNodes)
      .def("bytes_allocated", &EvalNodeArena::BytesAllocated)
      .def("save_level", &EvalNodeArena::SaveLevel)
      .def("reset_level", &EvalNodeArena::ResetLevel)
      .def("print_stats", &EvalNodeArena::PrintStats);

  py::class_<SumNode>(m, "SumNode")
      .def_property_readonly("bound", &SumNode::Bound)
      .def_property_readonly("points", &SumNode::Points)
      .def("node_count", &SumNode::NodeCount)
      .def("word_count", &SumNode::WordCount)
      .def("set_bounds_for_testing", &SumNode::SetBoundsForTesting)
      .def(
          "orderly_force_cell",
          &SumNode::OrderlyForceCell,
          py::return_value_policy::reference,
          py::arg("cell"),
          py::arg("num_lets"),
          py::arg("arena")
      )
      .def("get_children_map", &SumNode::GetChildrenMap, py::return_value_policy::reference)
      .def_property_readonly("children", &SumNode::GetChildrenMap)
      .def("score_with_forces", &SumNode::ScoreWithForces)
      .def("orderly_bound", &SumNode::OrderlyBound);

  py::class_<ChoiceNode>(m, "ChoiceNode")
      .def_property_readonly("bound", &ChoiceNode::Bound)
      .def_property_readonly("child_letters", &ChoiceNode::ChildLetters)
      .def("node_count", &ChoiceNode::NodeCount)
      .def(
          "get_child_for_letter",
          &ChoiceNode::GetChildForLetter,
          py::return_value_policy::reference
      )
      .def(
          "get_children",
          &ChoiceNode::GetChildren,
          py::return_value_policy::reference
      );

  py::class_<TreeBuilderStats>(m, "TreeBuilderStats")
      .def_readonly("collect_s", &TreeBuilderStats::collect_s)
      .def_readonly("sort_s", &TreeBuilderStats::sort_s)
      .def_readonly("build_s", &TreeBuilderStats::build_s)
      .def_readonly("n_paths", &TreeBuilderStats::n_paths)
      .def_readonly("n_uniq", &TreeBuilderStats::n_uniq);

  py::class_<OrderlyTreeBuilder<2, 2>>(m, "OrderlyTreeBuilder22")
      .def(py::init<Trie*>())
      .def("build_tree", &OrderlyTreeBuilder<2, 2>::BuildTree, py::return_value_policy::reference)
      .def("get_stats", &OrderlyTreeBuilder<2, 2>::GetStats);

  py::class_<OrderlyTreeBuilder<2, 3>>(m, "OrderlyTreeBuilder23")
      .def(py::init<Trie*>())
      .def("build_tree", &OrderlyTreeBuilder<2, 3>::BuildTree, py::return_value_policy::reference)
      .def("get_stats", &OrderlyTreeBuilder<2, 3>::GetStats);

  py::class_<OrderlyTreeBuilder<3, 3>>(m, "OrderlyTreeBuilder33")
      .def(py::init<Trie*>())
      .def("build_tree", &OrderlyTreeBuilder<3, 3>::BuildTree, py::return_value_policy::reference)
      .def("get_stats", &OrderlyTreeBuilder<3, 3>::GetStats);

  py::class_<OrderlyTreeBuilder<3, 4>>(m, "OrderlyTreeBuilder34")
      .def(py::init<Trie*>())
      .def("build_tree", &OrderlyTreeBuilder<3, 4>::BuildTree, py::return_value_policy::reference)
      .def("get_stats", &OrderlyTreeBuilder<3, 4>::GetStats);

  py::class_<OrderlyTreeBuilder<4, 4>>(m, "OrderlyTreeBuilder44")
      .def(py::init<Trie*>())
      .def("build_tree", &OrderlyTreeBuilder<4, 4>::BuildTree, py::return_value_policy::reference)
      .def("get_stats", &OrderlyTreeBuilder<4, 4>::GetStats);

  py::class_<OrderlyTreeBuilder<4, 5>>(m, "OrderlyTreeBuilder45")
      .def(py::init<Trie*>())
      .def("build_tree", &OrderlyTreeBuilder<4, 5>::BuildTree, py::return_value_policy::reference)
      .def("get_stats", &OrderlyTreeBuilder<4, 5>::GetStats);

  py::class_<OrderlyTreeBuilder<5, 5>>(m, "OrderlyTreeBuilder55")
      .def(py::init<Trie*>())
      .def("build_tree", &OrderlyTreeBuilder<5, 5>::BuildTree, py::return_value_policy::reference)
      .def("get_stats", &OrderlyTreeBuilder<5, 5>::GetStats);
}