# WebAssembly Boggler

The C++ Boggle code can be exported to [WebAssembly] (WASM) for use on web pages.

To build, install [emscripten] and then run:

    ./wasm/build-wasm.sh

Check out [danvk/webboggle] for the web UI and https://www.danvk.org/boggle/ for the live version. This wrapper uses [embind], which is analogous to [pybind11] for WASM.

[danvk/webboggle]: https://github.com/danvk/webboggle
[emscripten]: https://emscripten.org/index.html
[WebAssembly]: https://webassembly.org/
[embind]: https://emscripten.org/docs/porting/connecting_cpp_and_javascript/embind.html
[pybind11]: https://pybind11.readthedocs.io/en/stable/index.html
