#ifndef CONSTANTS_H
#define CONSTANTS_H

// clang-format off

// There's only one "Qu" die, but we allow a board with many of Qus.
// This prevents reading uninitialized memory on words with lots of Qus, which
// can cause spuriously high scores.
const unsigned int kWordScores[] = {
    // 1, 2, 3, 4, 5, 6, 7,  8,  9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25
    // 0, 0, 0, 1, 1, 2, 3, 5, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11};
    0, 0, 0, 1, 1, 1, 1, 1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1,  1};

static_assert(
    sizeof(kWordScores) / sizeof(kWordScores[0]) == 26
);

// 5x5 board, 26 letters.
const int MAX_CELLS = 5 * 5;
const int MAX_STACK_DEPTH = MAX_CELLS * 26;

// clang-format on

#endif  // CONSTANTS_H
