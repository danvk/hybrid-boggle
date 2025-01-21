#ifndef CONSTANTS_H
#define CONSTANTS_H

// There's only one "Qu" die, but we allow a board with many of Qus.
// This prevents reading uninitialized memory on words with lots of Qus, which
// can cause spuriously high scores.
const unsigned int kWordScores[] =
      //0, 1, 2, 3, 4, 5, 6, 7,  8,  9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20
      { 0, 0, 0, 1, 1, 2, 3, 5, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11, 11 };

#endif  // CONSTANTS_H
