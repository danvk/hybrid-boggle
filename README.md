# Hybrid Boggle

This is an adaptation of the pure-C++ Boggle code in [danvk/performance-boggle]
to a hybrid of C++ and Python using pybind11. The idea is to get the fast
iteration speed of Python for experimentation while retaining all the runtime
speed of the C++ solver.

The goal is to find the highest-scoring board for 3x4 and 4x4 Boggle (3x3 is
already [complete]) and prove that it is the best.

Setup:

```
poetry install
./build.sh
poetry run pytest
```

[complete]: https://www.danvk.org/wp/2009-08-08/breaking-3x3-boggle/index.html
[danvk/performance-boggle]: https://github.com/danvk/performance-boggle
