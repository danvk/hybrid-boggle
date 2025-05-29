# Raw Results

This directory contains the results of hillclimbing runs, as well the results of exhaustive search via Branch & Bound for (size, wordlist) pairs where that's been completed.

All of these boards have been "canonicalized" to account for the various types of symmetry. See `boggle/canonicalize.py` for details.

The [hillclimber] has a few parameters (pool size, excluded letters). The relevant command is included at the top of each file.

The `most-words` directory contains the results of a search for boards with the most words, rather than the most points. This requires a patch to the `SCORES` array. See [`most-words` branch][mw].

[mw]: https://github.com/danvk/hybrid-boggle/tree/most-words
