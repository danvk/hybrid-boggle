# A Computational Proof of the Highest-Scoring Boggle Board

⚠️ ⚠️ ⚠️

_This is an in-progress draft of a paper explaining the methodology used by this repo. For a very high-level explanation and links to blog posts, see [Methodology] on the GitHub repo._

⚠️ ⚠️ ⚠️

[Methodology]: https://github.com/danvk/hybrid-boggle?tab=readme-ov-file#methodology

## Abstract

- TODO

## Introduction

- What is Boggle? How do you play?
- Prior art
- Preview of our results

## Terminology

The words that can be found on a Boggle board are determined by the letters on the board and by the choice of dictionary. In this paper, we’ll use the ENABLE2K word list, which was developed by Alan Beale in 1997 and 2000. This word list contains 173,528 entries.

We adopt the following terminology:

- `B` refers to a Boggle board. To refer to a specific Boggle board, we write the out the letters of the board in column-major order. (This distinction is only important for non-square dimensions such as 2x3 and 3x4 Boggle, which lack reflectional symmetry.)
- Because one of the Boggle dice contains a “Qu” (two letters), we adopt the convention that `q` indicates a Qu cell. So `qaicdrneetasnnil` refers to the board in Figure N.
- The cells on an MxN board are numbered `0…M*N-1` in column-major order, as shown in Figure N. We refer to the letter on cell `i` of board `B` as `B_i`.
- `Words(B)` is the set of all words that can be found on the board `B`.
- `Score(B)` is the sum of the point value of these words, `\sum_{w \in Words(B)} Points(Length(w))`. We refer to this as the score of the board.

## Heuristics to find high-scoring boards

Finding all the words on a Boggle board is a popular programming puzzle. This is done by performing a depth-first search over the board’s adjacency graph starting at each cell. The key to making this efficient is to prune out prefixes such as “bnj” that don’t begin any words in the dictionary. This is typically done using a Trie (Prefix Tree) data structure.

*TODO: make this use trie_node.IsVisited() and trie_node.SetVisited() and return a score for clearer contrast w/ Max.*

```
# Listing 0: Scoring a Boggle Board
def score(board, trie):
  words = set()
  for i = 0..m*n-1:
    score_dfs(board, idx, trie, {}, words)
  return sum(SCORE[word.length()] for word in words)

 def score_dfs(board, idx, parent_node, used, words):
   used[idx] = True
   if trie_node.has_child(board[idx]):
	   trie_node = parent_node.child(board[idx])
	   if trie_node.is_word():
	     words.add(trie_node)
	   for n_idx in NEIGHBORS[idx]:
	     if not used[n_idx]:
	  	   score_dfs(board, n_idx, trie_node, used, words)
   used[idx] = False
```

With some care, it is possible to find the score of individual boards extremely rapidly on modern hardware. For example, the author’s laptop is able to score random 4x4 Boggle boards at a rate of around 200,000 boards per second.

This speed can be used to attack a new problem: finding high-scoring boards. This is typically done via local search heuristics such as hillclimbing, simulated annealing, or genetic algorithms. A particularly effective approach for Boggle is to iteratively explore around a pool of high-scoring boards, as shown in Listing 1.

```
# Listing 1: Hillclimbing Algorithm
N = 250  # pool size
Pool <- N random Boggle Boards
Repeat until convergence:
  Neighborhood <- Pool + Boards within edit distance 1 of a board in Pool
  Pool <- N highest-scoring boards in Neighborhood
```

We take an “edit” to mean changing one letter or swapping two letters. With a pool size of N=250, this consistently (X/Y times) converges with the highest-scoring board as `perslatgsineters`, which contains 1,045 words and scores 3,625 points using ENABLE2K.

This makes one wonder whether this board is, in fact, the global optimum. The principal result of this paper is to show that it is.

## Proof of Maximality

The most straightforward way to prove that a board is the highest-scoring is by exhaustive search. Unfortunately, the combinatorial explosion of possible boards renders this infeasible for all but the smallest sizes:

| **Dimensions** | **Number of Boards (approx)** | **Evaluate Rate** | **Total Time** |
| --- | --- | --- | --- |
| 3x3 | 26^9/8 ≈ 6.8e11 | 600k bd/s | ~12 days |
| 3x4 | 26^12/4 ≈ 2.4e16 | 400k bd/s | ~2000 years |
| 4x4 | 26^16/8 ≈ 5.5e21 | 200k bd/s | ~900M years |

An objection is that not all 26^16 combinations of letters can be rolled with the standard 16 Boggle dice. Determining whether a particular letter combination can be rolled is a Set-Cover problem, which is NP-Complete. A greedy approach works well for this small problem, however, and we can estimate that approximately 1 in 12 combinations of letters can be rolled. While this reduces the search space, it’s not enough to make exhaustive search feasible.

Two observations suggest a path towards a solution:

1. Similar boards have similar sets of words on them. Finding the score of a board and that of its neighbors involves large amounts of duplicated work.
2. Most boards have scores that are significantly lower than the best one. The average score of a random board is about 42, nearly 100x less than 3625. (The average score of a board rolled with Boggle dice is closer to 120.)

The former observation suggests that we should group boards together to reduce repeated work. The latter indicates that we have considerable “wiggle room” to upper bound the score rather than calculate it precisely.

### Branch and Bound

Rather than exhaustive search, we use Branch and Bound to find the globally optimal board. Branch and Bound is an algorithm design paradigm dating back to the 1960s that narrows in on the global optimum by recursively subdividing the search space.

To apply it, we need to define two operations on sets of Boggle boards:

- bound(S): an upper bound on the score of any board in a set of boards S
- branch(S): a way to split the set S into smaller sets S_1, S_2, …, S_m.

With these operations in place, the Branch and Bound algorithm to find all boards with a score greater than S_high is given in Listing 2:

```
# Listing 2 - Branch and Bound Algorithm
Queue <- {Universal Set of MxN Boggle Boards}
while Queue is non-empty:
  S <- Pop(Queue)
  if |S| == 1:
    S is a candidate solution; score its lone board to check
  else if bound(S) < S_high:
    S cannot contain a high-scoring board; it can be dropped.
  else:
    for S_i in branch(S):
      Queue <- S_i
```

The appeal of this approach is that, when `bound(S)` is low, we can discard the entire set `S` without having to evaluate every board in that set. Now we need to define the branch and bound operations.

### Board classes and the branch operation

Rather than allowing arbitrary sets of Boggle boards, we restrict ourselves to “board classes.” These require each cell of a board in the set to come from a particular set of letters:

- C(L1, L2, …, L_mxn) = { B | B_i \in L_i \forall i }

For example, here’s a 3x3 board class where each cell can be one of two letters:

TODO: image of board class

This board class contains 2^9 = 512 possible boards. Here are a few of them:

TODO: examples of boards in board class

Analogous to the `B_i` notation for boards, we can indicate the possible letters on a cell in a board class as `C_i`. On this board class, for example, `C_0 = {A, B}`.

We can carve the 26 letters of the alphabet up into distinct “buckets” to reduce the combinatorial explosion of possible boards into a much smaller number of board classes.

The following bucketings were found via a heuristic search:

| **Number of Buckets** | **Buckets** |
| --- | --- |
| 2 | {aeiosuy, bcdfghjklmnpqrtvwxz} |
| 3 | {aeijou, bcdfgmpqvwxz, hklnrsty} |
| 4 | {aeiou, bdfgjqvwxz, lnrsy, chkmpt} |

Using three buckets with 4x4 Boggle, for example, we have only 3^16 / 8 ≈ 5.4e6 board classes to consider, a dramatic reduction from the 5.5e21 individual boards. Of course, this will be in vain if operations on board classes are proportionally slower. Fortunately, this will not prove to be the case.

To “branch” from a board class, we split one of its cells into the individual possibilities:

TODO: image of splitting a board class into smaller board classes

Since the center and edge cells have the greatest connectivity, we split these first before splitting the corners.

### The sum bound

Next we need to construct an upper bound. One possible bound is the score of every word that can appear on any board in the board class.

- Bound_Sum(C) = \sum_{unique words on any board B \in C} Score(length(word))

This can be calculated in a similar manner to an ordinary Boggle solver, except that we need an additional loop over each possible letter on each cell:

*TODO: make this use trie_node.IsVisited() and trie_node.SetVisited() and return a score for clearer contrast w/ Max.*

```
# Listing N: Calcluating sum bound on a Boggle board class
def sum_bound(board_class, trie):
  words = set()
  for i = 0..m*n-1:
    sum_bound_dfs(board_class, idx, trie, {}, words)
  return sum(SCORE[word.length()] for word in words)

 def sum_bound_dfs(board_class, idx, parent_node, used, words):
   used[idx] = True
   letters = board_class[idx]
   for letter in letters:
     if parent_node.has_child(letter):
		   trie_node = parent_node.child(letter)
		   if trie_node.is_word():
		     words.add(trie_node)
		   for n_idx in NEIGHBORS[idx]:
		     if not used[n_idx]:
		  	   sum_bound_dfs(board_class, n_idx, trie_node, used, words)
   used[idx] = False
```

Clearly we have `Bound_Sum(C) >= Score(B) \forall B \in C` because every word on every possible board contributes to the bound.

A nice property of this bound is that, if `|C| = 1`, then `Bound_Sum(C) = max(Score(B) \forall B in C)`, that is to say, it converges on the true Boggle score.

Unfortunately, this bound is imprecise because it doesn’t take into account that some letter choices are mutually exclusive. For example:

TODO: example of why sum bound is loose

### The max bound

To get a concrete board, we must make a specific choice of letter for each cell. We can model this by taking the the max across the letter possibilities on a cell instead of the union. In doing so, we dispense with any attempt to enforce the constraint that a word can only be found once.

```
# Listing N: Calcluating max bound on a Boggle board class
def max_bound(board_class, trie):
  bound = 0
  for i = 0..m*n-1:
    bound += max_bound_dfs(board_class, idx, trie, {})
  return bound

 def max_bound_dfs(board_class, idx, parent_node, used):
   used[idx] = True
   letters = board_class[idx]
   max_score = 0
   for letter in letters:
     if parent_node.has_child(letter):
       this_score = 0
		   trie_node = parent_node.child(letter)
		   if trie_node.is_word():
		     this_score += SCORE[trie_node.length()]
		   for n_idx in NEIGHBORS[idx]:
		     if not used[n_idx]:
		  	   this_score += max_bound_dfs(board_class, n_idx, trie_node, used)
		   max_score = max(max_score, this_score)
   used[idx] = False
   return max_score
```

We can see that this is a valid bound because, for any particular board `B` in a class `C`:

1. It produces the full set of recursive calls for `B` from Listing 0, as well as many other calls.
2. For each of these matching calls, `max_bound_dfs` returns a score greater than or equal to `score_dfs`. This could be either because there’s another letter choice that produces a higher score, or because `max_bound_dfs` double-counts a word that `score_dfs` does not.

So `max_bound(C) >= score(B) \forall B \in C`. In practice, this bound is considerably tighter than the sum bound (see Table N). However, because it double-counts words, the max bound for a board class containing a single board may be greater than the score of that board.

TODO: Table N containing bounds for sum and max

TODO: Example of why max_bound is imprecise

The minimum of two upper bounds is also an upper bound, so we can also use:

```
max_sum_bound(C) = min(max_bound(C), sum_bound(C))
```

as an upper bound that combines the strengths of both. These bounds can be calculated simultaneously in a single DFS.

### Initial Results with Branch and Bound

Using the Branch and Bound algorithm with board classes and `max_sum_bound` results in a dramatic speedup over exhaustive search. For 3x3 Boggle using three buckets on the author’s laptop, the search completes in about an hour on a single CPU core. This represents roughly a 300x speedup.

This speedup makes 3x3 Boggle maximization easy on a laptop and 3x4 maximization possible in a data center. But it offers little hope for 4x4 Boggle.

Despite the speedup, there remains an enormous amount of repeated work. Each evaluation of `max_sum_bound` is performed independently, but the computation for `max_sum_bound(C)` and its children after the “branch” operation (`max_sum_bound(C_1)`, `max_sum_bound(C_2)`, …) is nearly identical. To achieve a greater speedup, we’ll need to eliminate this repetition.

## Sum/Choice trees

Our goal is to speed up repeated branch and bound calculations. To do so, we’ll forget about `sum_bound`, whose global uniqueness will be difficult to maintain. Instead, we’ll focus solely on `max_bound`, which can be be more easily calculated using local information.

Previously `max_bound` was calculated using recursive function calls. Our next step is to convert these function calls into a tree structure in memory. This will allow us to implement branch and bound as operations on the tree.

First, we refactor `max_bound` to use two functions. These will become two types of nodes in our tree:

```
# Listing N: Calcluating max bound with two mutally recursive functions
def max_bound(board_class, trie):
  bound = 0
  for i = 0..m*n-1:
    bound += choice_step(board_class, idx, trie, {})
  return bound

def choice_step(board_class, idx, parent_node, used):
  used[idx] = True
  letters = board_class[idx]
  max_score = 0
  # TODO: rewrite as comprehension?
  for letter in letters:
    if parent_node.has_child(letter):
      max_score = max(
        max_score,
        max_bound_dfs(board_class, idx, parent_node.child(letter), used)
      )
  used[idx] = False
  return max_score

def sum_step(board_class, idx, trie_node, used):
  score = 0
  if trie_node.is_word():
	  score += SCORE[trie_node.length()]
  # TODO: rewrite as comprehension?
	for n_idx in NEIGHBORS[idx]:
	  if not used[n_idx]:
		  score += choice_step(board_class, n_idx, trie_node, used)
  return score
```

This is a simple transformation of the previous `max_bound` and it produces the same values as before. With this new formulation, we construct a tree where each node corresponds to one of the function calls and its return value:

```
Node := SumNode | ChoiceNode

ChoiceNode:
  cell: int
  bound: int
  choices: SumNode[]

SumNode:
	points: int
	bound: int
	neighbors: ChoiceNode[]
```

The top-level call to `max_bound` can be modeled as a `SumNode` with each cell as a “neighbor:”

```
BuildTree(C) -> SumNode
```

The bound for each node can be computed as:

```
Bound(n: SumNode) = n.point + sum(c.bound for c in n.children)
Bound(n: ChoiceNode) = max(c.bound for c in n.children)
```

It will prove convenient to store this explicitly on each node, however. Here’s what one of these trees looks like:

TODO: tree for some simple board class

We pause to make a few observations about these Sum/Choice trees:

- By construction, `BuildTree(C).bound = max_bound(C)`.
- The wordlist and geometry of the Boggle board are encoded in the tree. Once the tree is constructed, we no longer need to reference the Trie or the `NEIGHBORS` array.
- Words correspond to `SumNode`s with points on them.
- Given the board class, individual words can be read off by descending the tree.
- `ChoiceNode`s for the same cell may appear multiple times in the tree. The bound is imprecise because the `max` operation may not make the same choice on each `ChoiceNode`.

### Multiboggle and the Invariant

We’ve seen that the root bound on the tree is an alternate way to calculate the `max_bound` for a board class. Now we want to perform operations on these trees, and these operations may affect the bound. To prove that the bound remains valid, we’ll establish an invariant and show that each operation maintains this invariant.

- The “force” operation: `F(Tree, B)`
- Lemma: `F(BuildTree(C), B) >= Bound(BuildTree(C)) \forall B \in C`
- What does this converge to? Not necessarily `Score(B)`.
- Definition of Multiboggle.
    - TODO: Program listing; like `Score(B)` but remove the duplicate check.
    - Lemma: `Multi(B) >= Score(B)`
    - Lemma: `Multi(B) = Score(B)` if B has no repeats
    - Example of pathology: B=[eeesrvrreeesrsrs](https://www.danvk.org/boggle/?board=eeesrvrreeesrsrs&multiboggle=1), S(B) = 189 but Multi(B) = 21953.
- Proof: `F(Root, B) = Multi(B) \forall B \in C`
    - Structural induction should precisely match the definition of Multiboggle.
- This gives a critical invariant that we’ll seek to maintain.
- Since `Multi(B) >= Score(B)`, and `Bound(Tree) >= Multi(B) \forall B \in Tree`, this provides an alternate proof that `Bound(Tree)` is an upper bound.
- Our Branch & Bound algorithm will find boards `B` with `Multi(B) >= S_high`.
For each such board, we’ll need to check whether `Score(B) >= S_high` as well.

### Sum/Choice maximization is NP-Hard

- Our goal is to find choices B such that `Force(Root, B) >= S_high`.
- Proof: Sum/choice satisfiability is NP-Hard.
    - Copy [D.W.’s mapping](https://stackoverflow.com/a/79413715/388951) from 3-CNF → Sum/Choice Sat from Stack Overflow.
- Therefore, we should not expect to find an efficient solution to this problem.

## Orderly Trees

- Before defining operations on general Sum/Choice trees, it will be helpful to shift our perspective.
- We’ve viewed them as an in-memory representation of the DFS to calculate `max_bound`.
- An alternative is to view them as a structure containing every path to every possible word. Instead of forming them via DFS, we can form them by adding one path to a word at a time.
- Define `AddWord`
- Definition of `BuildTree` using `AddWord` (maybe not worth including?)
- Proof: This produces an identical tree.
- Proof: anagramming words preserves the invariant
- Observation: adding words in the order they’re spelled is a choice. To get more consistent ordering and lower bounds, we can define a canonical order for the cells.
- Definition of `BuildOrderlyTree`
- Examples of orderly trees. Intuition that the top-level choice nodes represent how many cells you skip in the canonical order.
- Definition of `Orderly(N)`.

### OrderlyMerge

- Our goal is to speed up the “branch” operation and calculation of the subsequent bound.
- Definition of `merge(O1, O2, ..., O_n)`.
- Proof: branching on the top cell is equivalent to merge.
    - or: preserves the invariant?

### OrderlyBound

- Merging allocates additional nodes. We may wish to save RAM by not doing that close to the leaves.
- Definition of `OrderlyBound` algorithm
- Proof: `OrderlyBound` preserves the invariant.
    - or: is equivalent to merge
    - or: is equivalent to partial forcing

### De-duplicated Multiboggle

- Motivating example:

    ```
    E B E
    E . E
    ```

- The `max_bound` counts BEE four times, but that’s not necessary.
- Counting BEE twice, once for each distinct set of cells, is sufficient.
- Proof: De-duped multiboggle score B ≥ Score(B)
- Proof: Adjusted invariant with de-duped multiboggle score
- Examples of the impact that this has

### Final Branch and Bound Algorithm

- Partition the space into board classes, filtering for symmetry.
- For each board class `C`, build an OrderlyTree
- Perform Branch & Bound using OrderlyForce and OrderlyBound to find all `B \in C s.t. MultiDedupe(B) >= S_high`.
- For each such board `B`, check whether `Score(B) >= S_high`.

This will produce a list of all boards `B` (up to symmetry) with `Score(B) >= S_high`. If two congruent boards fall in the same board class, it will produce both of them.

## Results

### Complete results for 3x4, 3x4

- The speedup vs. brute force search is enormous.
- Hillclimbing works very well for finding `argmax(Score)` for each of these.

### Result for one dictionary for 4x4

- Was able to verify that hillclimbing produces the global max board (B=perslatgsineters) with Score(B)=3625.
- The process took ~23,000 CPU hours on GCP.
- Assuming $0.05/core/hr, this is around $1,000 of compute.

### Extension to maximizing word count

- Everything works as before, just use `SCORES = [1, 1, 1, ...]`.
- Hillclimbing is similarly effective for this problem.

### Variation: Powers of Two Boggle

- Set `SCORES=[1, 2, 4, 8, 16, ...]`.
- Now hillclimbing does not work. The fitness landscape is too spiky.

## Future Work

- Small optimizations: limited-depth merge, in-place merge might make 4x4 solvable using less compute.
- 5x5 seems impossible with this approach
- GPU acceleration, ILP solvers would be interesting avenues to explore

## Conclusions

- Hillclimbing works well for Boggle. This is likely because the score function is relatively smooth. High-scoring boards are surrounded by other high-scoring boards.
- Branch and Bound can be greatly accelerated by using a tailor-made tree structure and algorithms.
- 4x4 Boggle Maximization has been solved, but 5x5 maximization remains well out of reach.