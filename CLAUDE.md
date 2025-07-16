# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Build
```bash
poetry install          # Install Python dependencies
./build.sh              # Build C++ extension module
poetry run pytest      # Run all tests
./integration-test.sh   # Run integration test
```

### Core Tools
```bash
# Score individual boards
poetry run python -m boggle.score --size 44

# Hill climbing optimization to find high-scoring boards
poetry run python -m boggle.hillclimb 20 --size 44 --pool_size 250

# Exhaustive search (branch and bound) to prove optimal boards
poetry run python -m boggle.break_all 'bdfgjvwxz aeiou lnrsy chkmpt' 500 --size 33

# Calculate upper bounds using 2009 ibucket solver
poetry run python -m boggle.ibucket_solver 'bc ae nr ai hn ai nr bz ry'

# Calculate upper bounds using 2025 orderly trees
poetry run python -m boggle.orderly_tree_builder 'bc ae nr ai hn ai nr bz ry'

# Canonicalize boards (normalize rotations/reflections)
poetry run python -m boggle.canonicalize
```

### Testing
```bash
poetry run pytest boggle/              # Run all tests
poetry run pytest boggle/trie_test.py  # Run specific test
ruff check                             # Lint code (if available)
```

## Architecture Overview

This is a hybrid Python/C++ system for finding optimal Boggle boards through exhaustive search and heuristic optimization.

### Core Components

- **break_all.py**: Main exhaustive search using branch-and-bound with board class partitioning
- **hillclimb.py**: Heuristic search using greedy randomized adaptive search (GRASP)
- **boggler.py**: Core board evaluation engine with depth-first search for word finding
- **breaker.py**: 2025 hybrid breaking strategy using EvalTree structures and tree forcing
- **ibucket_breaker.py**: 2009 breaking strategy using max/no-mark and sum/union bounds
- **trie.py**: Prefix tree for efficient word storage and lookup
- **args.py**: Shared CLI argument handling and Python/C++ bridge utilities

### Key Patterns

- **Dual Implementation**: Most components have identical Python and C++ APIs (use `--python` flag to toggle)
- **Board Representation**: Boards are 1D strings (e.g., 16 chars for 4x4), read column-wise for non-square boards
- **Board Classes**: Search space partitioned into classes with letter constraints (e.g., "aeiou lnrsy chkmpt")
- **Dimensional Dispatch**: Different board sizes have specialized implementations (use `--size` flag: 33, 34, 44, 55)
- **Multi-threading**: Parallel processing with `--num_threads` and per-thread output files

### Word Processing
- Word lists exclude invalid Boggle words and normalize "qu" → "q"
- Root trie node's mark tracks the largest mark placed on any node (avoids synchronization)
- Multi-boggle scoring can count duplicate word paths on same board

### Performance Notes

- C++ implementations are significantly faster for compute-intensive operations
- Use `--switchover_score` in break_all.py to balance memory vs computation
- Hill climbing with large `--pool_size` finds better boards but uses more memory
- Exhaustive search requires substantial compute resources for larger boards (4x4 took ~600 CPU hours)
- Most ChoiceNodes and SumNodes have a small number of children, typically 0, 1 or 2.

## Code style and norms

- Avoid trivial implementation comments ("call the foo function"). Assume that readers can read code.
- Use `poetry run ruff format` to format Python and `clang-format -i cpp/*.{h,cc}` to format C++.
- Use `snake_case` for Python methods and `PascalCase` for C++ methods. Use the pybind11 bridge to make these match.
