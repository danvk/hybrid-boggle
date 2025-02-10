#!/bin/bash
# Generate the "bogglified" wordlists from the raw wordlists.
# See make_boggle_dict.py.

for raw in wordlists/raw/*.txt; do
    filename=$(basename $raw)
    out=wordlists/$filename
    poetry run python -m boggle.make_boggle_dict $raw > $out
    before=$(wc -l $raw)
    after=$(wc -l $out)

    echo "$filename: $before -> $after words"
done
