#!/usr/bin/env bash
set -o errexit

poetry run python -m boggle.break_all \
    'bdfgjvwxz aeiou lnrsy chkmpt' 1400 \
    --size 34 \
    --board_id 2520743 \
    --switchover_level 0 \
    --log_per_board_stats \
    --omit_times \
    > testdata/3x4-2520743-1400.txt

git diff --exit-code testdata
