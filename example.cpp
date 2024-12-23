#include <pybind11/pybind11.h>
namespace py = pybind11;

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
}
