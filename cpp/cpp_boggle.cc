#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "arena.h"
#include "boggler.h"
#include "ibucket_breaker.h"
#include "ibuckets.h"
#include "orderly_tree_builder.h"
#include "trie.h"

namespace py = pybind11;

// Forward declaration to avoid pulling in the full header if not needed
// But we need definitions for bindings.

PYBIND11_MODULE(cpp_boggle, m) {
  m.doc() = "C++ Boggle solver";

  py::class_<Trie>(m, "Trie")
      .def(py::init<const std::string&>())
      .def("starts_word", &Trie::StartsWord)
      .def("is_word", &Trie::IsWord)
      .def("word_id", &Trie::WordId)
      .def("descend", &Trie::Descend, py::return_value_policy::reference);

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
      .def("node_count", [](const SumNode& n, const EvalNodeArena& arena) { return n.NodeCount(arena.Base()); })
      .def("word_count", [](const SumNode& n, const EvalNodeArena& arena) { return n.WordCount(arena.Base()); })
      .def("set_bounds_for_testing", [](SumNode& n, const EvalNodeArena& arena) { n.SetBoundsForTesting(arena.Base()); })
      .def(
          "orderly_force_cell",
          &SumNode::OrderlyForceCell,
          py::return_value_policy::reference,
          py::arg("cell"),
          py::arg("num_lets"),
          py::arg("arena")
      )
      .def("get_children_map", [](SumNode& n, const EvalNodeArena& arena) {
          return n.GetChildrenMap(arena.Base());
      }, py::return_value_policy::reference)
      .def_property_readonly("children", [](SumNode& n) {
          throw std::runtime_error("SumNode.children property requires arena context. Use get_children_map(arena).");
           return std::map<int, ChoiceNode*>();
      })
      .def("score_with_forces", [](SumNode& n, const vector<int>& forces, EvalNodeArena& arena) {
          return n.ScoreWithForces(forces, arena.Base());
      })
      .def("orderly_bound", [](SumNode& n, int cutoff, const vector<string>& cells, const vector<int>& split_order, const vector<pair<int, int>>& preset_cells, EvalNodeArena& arena, int max_visits) {
          return n.OrderlyBound(cutoff, cells, split_order, preset_cells, arena.Base());
      }, py::arg("cutoff"), py::arg("cells"), py::arg("split_order"), py::arg("preset_cells"), py::arg("arena"), py::arg("max_visits") = -1);

  py::class_<ChoiceNode>(m, "ChoiceNode")
      .def_property_readonly("bound", &ChoiceNode::Bound)
      .def_property_readonly("child_letters", &ChoiceNode::ChildLetters)
      .def("node_count", [](const ChoiceNode& n, const EvalNodeArena& arena) { return n.NodeCount(arena.Base()); })
      .def(
          "get_child_for_letter",
          [](const ChoiceNode& n, int letter, const EvalNodeArena& arena) {
              return n.GetChildForLetter(letter, arena.Base());
          },
          py::return_value_policy::reference
      )
      .def(
          "get_children",
          [](ChoiceNode& n, const EvalNodeArena& arena) {
              return n.GetChildren(arena.Base());
          },
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