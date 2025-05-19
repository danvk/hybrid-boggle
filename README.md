# Hybrid Boggle

An attempt to find the highest-scoring [Boggle] board, and prove that it's the best.

## Results

These are the best (and best known) boards with the [ENABLE2K word list].

- ✅ 3x3: `streaedlp` [545 points], [proven optimal][33] in 2009.
- ✅ 3x4: `perslatesind` [1651 points], [proven optimal][34] in 2025.
- ✅ 4x4: `perslatgsineters` [3625 points], [proven optimal][35] in 2025.
- ❓ 5x5: `ligdrmanesietildsracsepes`, [10406 points], found via hill climbing, optimality unknown.

For other wordlists, [see below](#results-for-other-wordlists).

The 3x4 board should be read down columns first:

```
P L S
E A I
R T N
S E D
```

For square boards, you can read them however you like; every way is equivalent.

To get a feel for Boggle, try the [online Boggle Solver][3625 points], which is an interactive WASM build of part of this repo.

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

Here are the blog posts I've written about this project in 2025:

- [Finding the Globally-Optimal 3x4 Boggle Board][post1]: Explanation of the project and the work I did back in 2009.
- [New Ideas in 2025][post2]: Explains Multi-Boggle, the EvalTree structure and the basic operations on it.
- [A Thrilling Insight and the Power of Algorithms][post3]: Explains Orderly Trees, the idea that really broke this problem open.
- [Following up on an insight][post4]: Explains a incremental improvements that brought 4x4 Boggle in range.
- [After 20 Years, the Globally Optimal Boggle Board][35]: Announcement of the big 4x4 Boggle result.

For earlier posts, check out this [2014 compendium].

[post1]: https://www.danvk.org/2025/02/10/boggle34.html
[post2]: https://www.danvk.org/2025/02/13/boggle2025.html
[post3]: https://www.danvk.org/2025/02/21/orderly-boggle.html
[post4]: https://www.danvk.org/2025/04/10/following-insight.html
[2014 compendium]: https://www.danvk.org/wp/category/boggle/

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

To find all the high-scoring 3x4 boards, run:

```
$ time poetry run python -m boggle.break_all 'aeijou bcdfgmpqvwxz hklnrsty, corner:aeiosuy bcdfghjklmnpqrtvwxz' 1500 --size 34 --num_threads 3
Broke 104976 classes in 8273.01s.
Found 36 breaking failure(s):
...
1065762816  maximum resident set size
/usr/bin/time -l poetry run python -m boggle.break_all  1500 --size 34  3  24290.92s user 437.64s system 298% cpu 2:17:53.83 total
```

This takes just north of two hours on three cores on my laptop.

To find high-scoring 4x4 boards via hillclimbing, run:

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

To calculate the upper bound on a board class using the c.2009 [max/no-mark and sum/union bounds][upper bound], use `ibucket_solver`:

```
$ poetry run python -m boggle.ibucket_solver "lnrsy aeiou chkmpt chkmpt aeiou lnrsy lnrsy aeiou bdfgjvwxz"
0.02s 9359 (max=9359, sum=106383) lnrsy aeiou chkmpt chkmpt aeiou lnrsy lnrsy aeiou bdfgjvwxz
```

This also takes a `--print_words` flag that will print all the words that can be found on any board in the board class.

To calculate the upper bound on a board class using 2025's [orderly trees], use `orderly_tree_builder`:

```
$ poetry run python -m boggle.orderly_tree_builder "lnrsy aeiou chkmpt chkmpt aeiou lnrsy lnrsy aeiou bdfgjvwxz"
0.05s OrderlyTreeBuilder: t.bound=1231, 332438 nodes
```

Note that this bound is considerably lower, but computing it requires more time and memory.

The command line tools all take some standard flags like `--dictionary` and `--python`. Run with `--help` to see them.

## Docker image

To build the Docker image for AMD64 on a Mac, run:

    docker buildx build --build-arg GIT_SHA=$(git rev-parse --short HEAD) --platform linux/amd64 .

You can find builds of this image on dockerhub under [danvk/boggle].

The image that was used to exhaustively search for the best 4x4 board was [danvk/boggle:2025-03-13].

## Guide to the Code

If you're trying to follow the code, here are a few pointers that will help:

- The word lists are processed to exclude invalid Boggle words and change "qu" to "q". So "quart" will be inserted in the Trie as "qart". See [wordlists/README.md](wordlists/README.md) for more.
- There is a convention that the "mark" on the root Trie node tracks the largest mark that's been placed on any node in the Trie. This avoids the need for synchronization across all the different classes that make use of Tries and their marks.
- Boggle boards are represented as 1-dimensional arrays. So a 4x4 Boggle board is a 16 character string. For 3x4 boards, which are 12 character strings, you need to read down the columns to get the right board.
- Generally the Python and C++ code match 1-1. I developed code in Python, wrote tests for it, and then translated it to C++ (sometimes with help from GitHub Copilot). The APIs are identical and they pass the same tests. Most CLI tools let you toggle between the C++ and Python implementations with the `--python` flag.
- Most CLI tools require you to set the size of the Boggle board. 3x3 is the default. If you want 4x4, set `--size 44`.

## Results for other wordlists

Here are the results for different wordlists. See [wordlists/README.md](wordlists/README.md) for background. Note that only ENABLE2K and YAWL contain 16+ letter words.

Wordlist | 3x3 | 3x4 | 4x4 | 5x5
--: | -- | -- | -- | --
**ENABLE2K** | ✅ `streaedlp` ([545](https://www.danvk.org/boggle/?board=streaedlp)) | ✅ `perslatesind` ([1651](https://www.danvk.org/boggle/?board=perslatesind&dims=34)) | ✅ `perslatgsineters` ([3625](https://www.danvk.org/boggle/?board=perslatgsineters)) | ❓ `ligdrmanesietildsracsepes` ([10406](https://www.danvk.org/boggle/?board=ligdrmanesietildsracsepes))
**NASPA23**  | ✅ `lepsartes` ([581](https://www.danvk.org/boggle/?board=lepsartes&wordlist=naspa23)) | ✅ `perslatesind` ([1718](https://www.danvk.org/boggle/?board=perslatesind&wordlist=naspa23&dims=34)) | ❓ `perslatgsineters` ([3923](https://www.danvk.org/boggle/?board=perslatgsineters&wordlist=naspa23)) | ❓ `ligdrmanesietildsracsepes` ([11371](https://www.danvk.org/boggle/?board=ligdrmanesietildsracsepes&wordlist=naspa23))
**OSPD5**     | ✅ `lepsartes` ([573](https://www.danvk.org/boggle/?board=lepsartes&wordlist=ospd5)) | ✅ `perslatesind` ([1701](https://www.danvk.org/boggle/?board=perslatesind&wordlist=ospd5&dims=34)) | ❓ `segsrntreiaeslps` ([3827](https://www.danvk.org/boggle/?board=segsrntreiaeslps&wordlist=ospd5)) | ❓ `dlpmeseasicrtndoaiegsplsr` ([10473](https://www.danvk.org/boggle/?board=dlpmeseasicrtndoaiegsplsr&wordlist=ospd5))
**TWL06**     | ✅ `lepsartes` ([555](https://www.danvk.org/boggle/?board=lepsartes&wordlist=twl06)) | ✅ `perslatesind` ([1668](https://www.danvk.org/boggle/?board=perslatesind&wordlist=twl06&dims=34)) | ❓ `aresstapenildres` ([3701](https://www.danvk.org/boggle/?board=aresstapenildres&wordlist=twl06)) | ❓ `rdgassentmliteicarsdseper` ([10769](https://www.danvk.org/boggle/?board=rdgassentmliteicarsdseper&wordlist=twl06))
**YAWL**  | ✅ `stleaeprd` ([659](https://www.danvk.org/boggle/?board=lepsartes&wordlist=yawl)) | ✅ `bindlatesers` ([1959](https://www.danvk.org/boggle/?board=bindlatesers&wordlist=yawl&dims=34)) | ❓ `bestlatepirsseng` ([4540](https://www.danvk.org/boggle/?board=bestlatepirsseng&wordlist=yawl)) | ❓ `dlpmeseasicrtndoaiegpllsr` ([13479](https://www.danvk.org/boggle/?board=dlpmeseasicrtndoaiegpllsr&wordlist=yawl))
**SOWPODS**    | ✅ `streaedlb` ([676](https://www.danvk.org/boggle/?board=lepsartes&wordlist=sowpods)) | ✅ `drpseiaestng` ([2073](https://www.danvk.org/boggle/?board=drpseiaestng&wordlist=sowpods&dims=34)) | ❓ `bestlatepirsseng` ([4808](https://www.danvk.org/boggle/?board=bestlatepirsseng&wordlist=sowpods)) | ❓ `degosrsniceitalstrepuopsd` ([14488](https://www.danvk.org/boggle/?board=degosrsniceitalstrepuopsd&wordlist=sowpods))

- ✅ means this is proven to be the globally optimal board via exhaustive search (`break_all.py`).
- ❓ means that this is the best board found to date using [hill climbing] (`hillclimb.py`), but there may still be a better board out there. (Please send a pull request if you find a better one!)

If you have a few thousand dollars of compute burning a hole in your pocket and you'd like to fill out the global optimum 4x4 column, please let me know!

You can find lists of the highest-scoring boards found via exhaustive search in the [`results`](/results) directory.

## Side Quests

While the goal of this project was to find and prove the highest-scoring Boggle board, the same code can be used to answer many other important Boggle questions.

### Most word-dense boards

Instead of the highest-scoring board, what if we want to find the board with the most words on it? Shifting to this problem just requires making the `SCORES` array contain all `1`s ([5536e2f]). Here are the hill-climbing results.

Wordlist | 4x4 | 5x5
--: | -- | --
**ENABLE2K** | ❓ `gesorntreaieslps` ([1158](https://www.danvk.org/boggle/?board=gesorntreaieslps)) | ❓ `ligdrmanesietildsracsepes` ([10406](https://www.danvk.org/boggle/?board=ligdrmanesietildsracsepes))
**NASPA23**  | ❓ `gesorntreaiespls` ([1229](https://www.danvk.org/boggle/?board=gesorntreaiespls&wordlist=naspa23)) | ❓ `ligdrmanesietildsracsepes` ([11371](https://www.danvk.org/boggle/?board=ligdrmanesietildsracsepes&wordlist=naspa23))
**OSPD5**    | ❓ `gesorntreaiespls` ([1211](https://www.danvk.org/boggle/?board=gesorntreaiespls&wordlist=ospd5)) | ❓ `dlpmeseasicrtndoaiegsplsr` ([10473](https://www.danvk.org/boggle/?board=dlpmeseasicrtndoaiegsplsr&wordlist=ospd5))
**TWL06**    | ❓ `gesorntreaieslps` ([1182](https://www.danvk.org/boggle/?board=gesorntreaieslps&wordlist=twl06)) | ❓ `rdgassentmliteicarsdseper` ([10769](https://www.danvk.org/boggle/?board=rdgassentmliteicarsdseper&wordlist=twl06))
**YAWL**     | ❓ `sdestrnteiaespls` ([1458](https://www.danvk.org/boggle/?board=sdestrnteiaespls&wordlist=yawl)) | ❓ `dlpmeseasicrtndoaiegpllsr` ([13479](https://www.danvk.org/boggle/?board=dlpmeseasicrtndoaiegpllsr&wordlist=yawl))
**SOWPODS**  | ❓ `sdestrnteiaespls` ([1514](https://www.danvk.org/boggle/?board=sdestrnteiaespls&wordlist=sowpods)) | ❓ `degosrsniceitalstrepuopsd` ([14488](https://www.danvk.org/boggle/?board=degosrsniceitalstrepuopsd&wordlist=sowpods))

`gesorntreaieslps` is also in the [top ten] for ENABLE2K for points. I've confirmed that the 3x4 hill-climbing winner for ENABLE2K is also the global optimum, which suggests that these boards are likely to be global optima as well.

### Highest-scoring boards containing a 16- or 17-letter word

While there are 16 cells on a Boggle board, one of the dice has a "Qu" on it, so the longest word you can form has 17 letters. One might ask, what's the highest-scoring board that contains a 16- or 17-letter word?

This can be answered directly and combines two interesting problems: enumerating [Hamiltonian cycles] on a Boggle graph, and quickly scoring Boggle boards. There are only ~68,000 distinct paths through all 16 cells on a Boggle board, and there are only ~2,000 16-letter words. (There are only a handful of 17-letter words containing a "q".) So we can exhaustively search the cross product of these in an hour or two to get the answer (`hamiltonian.py`):

Wordlist | 16 letters | 17 letters
--: | --- | ---
**ENABLE2K** | [hclbaiaertnssese](https://www.danvk.org/boggle/?board=hclbaiaertnssese) (2149) ”charitablenesses” | [qaicdrneetasnnil](https://www.danvk.org/boggle/?board=qaicdrneetasnnil) (1391) ”quadricentennials”
**YAWL** | [usaupltreaiernsd](https://www.danvk.org/boggle/?board=usaupltreaiernsd&wordlist=yawl) (2988) ”supernaturalised” | [qressatstiseremr](https://www.danvk.org/boggle/?board=qressatstiseremr&wordlist=yawl) (1935) ”quartermistresses”

This analysis only works with ENABLE2K and YAWL. It's not possible for the other wordlists (OSPD, NASPA, TWL, SOWPODS) since they don't have words longer than 15 letters. They were created for Scrabble, after all, which is played on a 15x15 grid.

### Fibonacci Scoring

It's surprising that 8+ letter words all net 11 points. It feels like longer words should continue to earn more. What if we used "Fibonacci scoring", with the following score table:

Letters | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17
-- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | --
Points | 1 | 1 | 2 | 3 | 5 | 8 | 13 | 21 | 34 | 55 | 89 | 144 | 233 | 377 | 610

[performance-boggle]: https://github.com/danvk/performance-boggle
[ENABLE2K word list]: https://github.com/danvk/hybrid-boggle/tree/main/wordlists
[33]: https://www.danvk.org/wp/2009-08-08/breaking-3x3-boggle/index.html
[34]: https://www.danvk.org/2025/02/13/boggle2025.html
[35]: https://www.danvk.org/2025/04/23/boggle-solved.html
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
[545 points]: https://www.danvk.org/boggle/?board=streaedlp
[1651 points]: https://www.danvk.org/boggle/?board=perslatesind
[3625 points]: https://www.danvk.org/boggle/?board=perslatgsineters
[10406 points]: https://www.danvk.org/boggle/?board=ligdrmanesietildsracsepes
[orderly trees]: https://www.danvk.org/2025/02/21/orderly-boggle.html#orderly-trees
[Hamiltonian cycles]: https://en.wikipedia.org/wiki/Hamiltonian_path
[5536e2f]: https://github.com/danvk/hybrid-boggle/commit/5536e2fb784435bc2d8af19c8e317ff927c81b23
[top ten]: https://github.com/danvk/hybrid-boggle/blob/main/results/best-boards-4x4.enable2k.txt
