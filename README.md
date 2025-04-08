# Hybrid Boggle

An attempt to find the highest-scoring [Boggle] board, and prove that it's the best.

## Results

These are the best (and best known) boards with the [ENABLE2K word list].

- ✅ 3x3: `streaedlp` [545 points], [proven optimal][33] in 2009.
- ✅ 3x4: `perslatesind` [1651 points], [proven optimal][34] in 2025.
- ✅ 4x4: `perslatgsineters` [3625 points], proven optimal in 2025. (Details coming soon!)
- ❓ 5x5: `sepesdsracietilmanesligdr`, 10406 points, found via hill climbing, optimality unknown.

The 3x4 board should be read down columns first:

```
P L S
E A I
R T N
S E D
```

For square boards, you can read them however you like; every way is equivalent. For other wordlists, [see below](#results-for-other-wordlists).

## Methodology

The general approach is [branch and bound][bnb]:

- Find a very high-scoring board using [simulated annealing] or [hill climbing]. Call its score `S`.
- Carve up the enormous space of all possible MxN Boggle boards into a smaller number of "board classes," where each class contains millions, billions or trillions of individual boards.
- For each board class `C`:
  - Calculate an [upper bound], `B`, on the highest-scoring board in the board class.
  - If `B < S` then we can throw out the whole class. It does not contain the best board.
  - If not, split `C` into smaller classes `C1`, `C2`, …, `Cn` and repeat.
  - If `C` contains a single board, then it is a candidate for the best board.

Calculating a precise upper bound on a class of boards is [believed to be NP-Hard][np-hard], so the most productive path to performing this search quickly is to optimize each of these operations. [This post] describes several of the techniques used to do so in this repo.

## Development and usage

This repo is a mix of Python and C++, with the bridge provided by [pybind11]. The C++ is adapted from the [performance-boggle] repo. Python is used for testing, prototyping, and wrapping the C++ code. All of the C++ code has a matching Python equivalent.

Setup:

```
poetry install
./build.sh
poetry run pytest
```

To find all the high-scoring 3x3 boards, run:

```
$ poetry run python -m boggle.break_all 'bdfgjqvwxz aeiou lnrsy chkmpt' 500 --size 33
Found 262144 total boards in 0.05s.
...
Unable to break board: septalres 503
Unable to break board: niptalser 504
Unable to break board: septarles 528
...
Broke 262144 classes in 725.34s.
Found 56 breaking failure(s):
...
```

This takes ~5 minutes on my M2 MacBook. It prints out 56 boards with >=500 points and records more detailed information about the breaking process in `tasks-01.ndjson`. If you want it to run even faster, set `--num_threads=4` or higher.

To find high-scoring 4x4 boards, run:

```
$ poetry run python -m boggle.hillclimb 20 --size 44 --pool_size 250
num_iter=1: max(scores)=(561, 'irrynsaesesthkyw') min(scores)=(245, 'eiobnsttiamfmwam')
num_iter=2: max(scores)=(790, 'irryntaesesthkyw') min(scores)=(539, 'irrfnseesesthkyw')
num_iter=3: max(scores)=(1172, 'ecolsaizlrtnbese') min(scores)=(821, 'irryntaesesthwyk')
num_iter=4: max(scores)=(1639, 'ecolsnislatnbere') min(scores)=(1191, 'sragetemincrcasf')
...
num_iter=28: max(scores)=(3625, 'tslpeiaerntrsegs') min(scores)=(3420, 'oresstipenaldger')
num_iter=29: max(scores)=(3625, 'tslpeiaerntrsegs') min(scores)=(3420, 'oresstipenaldger')
run=0 3625 tslpeiaerntrsegs (29 iterations)
---
Top ten boards:
tslpeiaerntrsegs 3625
terssinelatgpers 3625
sgesrtnreaieplst 3625
sretenisgtalsrep 3625
```

These are all equivalent to each other, which you can see by piping them through `boggle.canonicalize`:

```
$ echo 'tslpeiaerntrsegs\nterssinelatgpers\nsgesrtnreaieplst\nsretenisgtalsrep' | poetry run python -m boggle.canonicalize
perslatgsineters
perslatgsineters
perslatgsineters
perslatgsineters
```

To calculate the scores of individual boards, use `boggle.score`:

```
$ echo 'dnisetalsrep\ngresenalstip' | poetry run python -m boggle.score --size 34
dnisetalsrep: 1651
gresenalstip: 1563
2 boards in 0.00s = 4704.77 boards/s
```

Pass `--print_words` to print the actual words on each board.

To calculate the upper bound on a board class, use `ibucket_solver`:

```
$ poetry run python -m boggle.ibucket_solver "lnrsy aeiou chkmpt chkmpt aeiou lnrsy lnrsy aeiou bdfgjvwxz"
9359 (max=9359, sum=106383) lnrsy aeiou chkmpt chkmpt aeiou lnrsy lnrsy aeiou bdfgjvwxz
```

This also takes a `--print_words` flag that will print all the words that can be found on any board in the board class.

The command line tools all take some standard flags like `--dictionary` and `--python`. Run with `--help` to see them.

## Docker image

To build the Docker image for AMD64 on a Mac, run:

    docker buildx build --build-arg GIT_SHA=$(git rev-parse --short HEAD) --platform linux/amd64 .

You can find builds of this image on dockerhub under [danvk/boggle].

The image that was used to exhaustively search for the best 4x4 board was [danvk/boggle:2025-03-13].

## Results for other wordlists

Here are the results for different wordlists. See [wordlists/README.md](wordlists/README.md) for background.

  | 3x3 |   | 3x4 |   | 4x4 |   | 5x5
-- | -- | -- | -- | -- | -- | -- | --
             | **hillclimb** | **global** | **hillclimb** | **global** | **hillclimb** | **global** | **hillclimb**
**ENABLE2K** | `streaedlp` | `streaedlp` | `perslatesind` | `perslatesind` | `perslatgsineters` | `perslatgsineters` | `sepesdsracietilmanesligdr`
**NASPA23**  | `lepsartes` | `lepsartes` | `perslatesind` | `perslatesind` | `perslatgsineters` | ? | ?
**OSPD**     | `lepsartes` | `lepsartes` | `perslatesind` | `perslatesind` | `segsrntreiaeslps` | ? | ?
**YAWL**     | `stleaeprd` | `stleaeprd` | `bindlatesers` | `bindlatesers` | `bestlatepirsseng` | ? | ?
**SOWPODS**  | `streaedlb` | `streaedlb` | `drpseiaestng` | `drpseiaestng` | `bestlatepirsseng` | ? | ?
**TWL06**    | `lepsartes` | `lepsartes` | `perslatesind` | `perslatesind` | `aresstapenildres` | ? | `sepesdsracietilmanesligdr`

- "hillclimb" means that this is the best board found using [hill climbing] (`hillclimb.py`).
- "global" means this is the globally optimal board (`break_all.py`).

If you have a few thousand dollars of compute burning a hole in your pocket and you'd like to fill out the global optimum 4x4 column, please let me know!

[performance-boggle]: https://github.com/danvk/performance-boggle
[ENABLE2K word list]: https://github.com/danvk/hybrid-boggle/tree/main/wordlists
[33]: https://www.danvk.org/wp/2009-08-08/breaking-3x3-boggle/index.html
[34]: https://www.danvk.org/2025/02/13/boggle2025.html
[bnb]: https://www.danvk.org/2025/02/10/boggle34.html#how-did-i-find-the-optimal-3x3-board-in-2009
[simulated annealing]: https://github.com/danvk/hybrid-boggle/blob/main/boggle/anneal.py
[hill climbing]: https://github.com/danvk/hybrid-boggle/blob/main/boggle/hillclimb.py
[upper bound]: https://www.danvk.org/wp/2009-08-11/a-few-more-boggle-examples/index.html
[np-hard]: https://stackoverflow.com/questions/79381817/calculate-an-upper-bound-on-a-tree-containing-sum-nodes-choice-nodes-and-requi
[This post]: https://www.danvk.org/2025/02/13/boggle2025.html
[pybind11]: https://pybind11.readthedocs.io/en/stable/index.html
[Boggle]: https://en.wikipedia.org/wiki/Boggle
[danvk/boggle]: https://hub.docker.com/repository/docker/danvk/boggle/general
[danvk/boggle:2025-03-13]: https://hub.docker.com/repository/docker/danvk/boggle/tags/2025-03-13/sha256-e6a23b324af22b077af2b7b79ec31e17e668a5e166156818aedea188e791c1e1
[3625 points]: https://www.danvk.org/boggle/?board=perslatgsineters
[545 points]: https://www.danvk.org/boggle/?board=streaedlp
[1651 points]: https://www.danvk.org/boggle/?board=perslatesind
