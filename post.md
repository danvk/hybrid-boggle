---
layout: post
title: 'Boggle Revisited: Finding the Globally-Optimal 3x4 Boggle Board'
time: 2:15PM EST
datetime: 2025-02-06 2:15PM EST
summary: "After 15 years, a Boggle advance!"
---

Over 15 years ago (!) I wrote a series of [blog posts](https://www.danvk.org/wp/category/boggle/) about the board game Boggle. Boggle is a word search game created by Hasbro. The goal is to find as many words as possible on a 4x4 grid. You may connect letters in any direction (including diagonals) but you may not use the same letter twice in a word (unless that letter appears twice on the board).

(image)

Boggle is a fun game, but it’s also a fun Computer Science problem. There are three stops to make as you go down this rabbit hole:

1. **Write a program to find all the words on a Boggle board[link].** This is a classic data structures and algorithms problem, and sometimes even an interview question. What’s wonderful about this problem is that it’s a perfect use for a Trie[link] (aka Prefix Tree), and a counter to the idea that hash tables are always the best answer. You can find many[link], many[link] Boggle solvers of this sort on the internet. Apparently Jeff Dean is a fan[link] of Boggle, and LLMs can even write these solvers.
2. **Find high scoring Boggle boards.** Once you’ve written a fast solver, a natural question is “what’s the Boggle board with the most points on it?” The usual approach is some variation on simulated annealing[link]. Start with a random board and find all the words on it. Then change a letter or swap two letters and see if it improves things. Repeat until you stall out. This problem is less popular than the first, but you can still find a few blog posts about it.
3. **Prove that a Boggle board is the global optimum.** If you do enough simulated annealing runs, you’ll see the same few boards pop up again and again. A natural next question is “are these truly the highest-scoring boards?” Are there any high-scoring boards that simulated annealing misses? Proving a global optimum is much harder than finding a few high-scoring boards and, so far as I’m aware, I’m the only person who’s spent significant time on this problem.

The crowning achievement of my work in 2009 was proving[link] that this was the highest-scoring 3x3 Boggle board (using the ENABLE2K word list[link]), with 545 points:

```
P E R
L A T
D E S
```

Now, 15 years later, I’ve been able to prove that this is the best 3x4 board, with 1651 points:

```
S L P
I A E
N T R
D E S
```

The rest of this post will describe the proof. Alas, 4x4 Boggle still remains out of reach.

## Why is this a hard/interesting problem?

There are an [enormous number](https://www.danvk.org/wp/2007-08-02/how-many-boggle-boards-are-there/index.html) of possible Boggle boards. Something like 26^16/8, which is around 5 billion trillion (~5*10^21). This is far, far too many to check one by one. I [previously estimated](https://www.danvk.org/wp/2007-08-02/how-many-boggle-boards-are-there/index.html) that it would take around 2 billion years on a single CPU.

And yet… there’s a lot of structure in this problem that might be exploited to make it tractable. The possibility of such an enormous speedup (2 billion years → a few hours) is what makes this problem exciting to me.

## Why pick it back up now?

Fifteen years is a long time! The world has changed a lot since my [last post](https://www.danvk.org/wp/2009-08-11/a-few-more-boggle-examples/index.html). Computers have gotten a lot faster. There have been five new versions of C++. Cloud computing is a thing. Stack Overflow is a thing. So are LLMs. A cool language called TypeScript came out an I [wrote a book on it]. I even have an iPhone now!

I’ve gotten in the habit[link] of doing the Advent of Code[link], a coding competition that’s held every December. It involves lots of data structures and algorithms problems, so it got me in that headspace.

In addition, I’ve long been curious to write code using a mix of C++ and Python. C++ for the performance-critical parts, Python for everything else. Maybe it could be a best-of-both worlds: the speed of C++ with the convenience of Python. I thought Boggle would be a great problem to use as motivation. I wound up using pybind11[link] and I like it a lot. I’ll have some thoughts to share about it at the end of the post.

## How did I find the optimal board in 2009?

There were three key ideas. The first was to reduce the number of boards by considering whole classes of boards at once. Here’s an example of a class of 3x3 boards:

<style>
    td, th {
        border: 1px solid #777;
        padding: 0.25em;
    }
</style>

| c, h, k, m, p, t | a, e, i, o, u  | l, n, r, s, y |
| l, n, r, s, y | a, e, i, o, u  | c, h, k, m, p, t |
| b, d, f, g, j, v, w, x, z | a, e, i, o, u  | l, n, r, s, y |

XXX missing the letter q!

TODO: state clearly that there are four buckets, and what the four buckets are

Instead of having a single letter on each cell, this board has 5-9 possible letters. There are 5,062,500 individual boards in this class. The highest-scoring 3x3 board is one of them, but there are many others.

There are vastly fewer board _classes_ than individual boards. For 3x3 Boggle, using four “buckets” of letters takes us from 26^9/8 = 6x10^11 boards → 32,768 board classes. If we can find the highest-scoring board in each class in a reasonable amount of time, this will make the problem of finding the global optimum tractable.

The second insight is that, rather than finding the highest-scoring board in a class, all we really need to do is establish an upper bound on its score. If that upper bound is less than 545 (the score of the best individual board we found through simulated annealing), then we know there’s no specific board in this class that beats our best board, and we can toss it out.

As it turns out, establishing an upper bound is much, much easier than finding the best board in a class. I came up with [two upper bounds](https://www.danvk.org/wp/2009-08-08/breaking-3x3-boggle/index.html) back in 2009:

- sum/union: the sum of the points for every word that can be found on any board in the class.
- max/nomark: a bound that takes into account that you have to choose one letter for each cell.

Usually neither of those upper bounds is good enough. On this board class, for example, the sum/union bound is 106,383 and the max/nomark bound is 9,359. Those are both much larger than 545!

This brings us to the final insight: if the upper bound is too high, you can split up one of the cells to make several smaller classes. For example, if you split up the middle cell then this single class becomes five classes, one for each choice of vowel in the middle. These are the bounds:

TODO: show one of the boards to make this more concrete

| **Middle Letter** | **Max/No Mark** | **Sum/Union** |
| --- | --- | --- |
| A | 6,034 | 55,146 |
| E | 6,979 | 69,536 |
| I | 6,155 | 58,139 |
| O | 5,487 | 48,315 |
| U | 4,424 | 37,371 |

Those numbers are all still too high (we want them to get below 545), but they have come down considerably. Choosing “U” for the middle cell brings the bound down the most, while choosing "E" brings it down the least.

If you iteratively break cells, your bounds will keep going down. If they drop below 545, you can stop. These recursive breaks form a sort of tree. The branches of the tree with lower scores (the “U”) will require fewer subsequent breaks and will be shallower than the higher-scoring branches (the “E”). The sum/union bound converges on the true score, so if you break all 9 cells and still have more than 545 points, you’ve found a global optimum.

Back in 2009, I reported that I checked all the 3x3 boards this way in around 6 hours. The board you find via simulated annealing is, in fact, the global optimum. In 2025, I’m able to run the same code on a single core on my laptop in around 40 minutes.

## How much harder are 3x4 and 4x4 Boggle?

As you increase the size of the board, the maximization problem gets harder for two reasons:

1. There are exponentially more boards (and board classes) to consider.
2. Each board (and board class) has more words and more points on it.

How bad is this?

- 3x3: each class takes ~80ms to break and there a ~33,000 of them ⇒ ~40 minutes.
- 3x4: each class takes ~1.6s to break and there are ~6.7M of them ⇒ ~78 days.
- 4x4: each class takes ~10m to break and there are ~537M of them ⇒ ~10,000 years.

So with the current algorithms, 3x4 Boggle is ~3000x harder than 3x3 Boggle and 4x4 Boggle is around a million times harder than that.

With the advances in this post, we’ll be able to get a ~10x speedup. Enough that it’s reasonable to solve 3x4 Boggle on a single beefy cloud machine, but not enough to bring 4x4 Boggle within reach.

## New ideas in 2025

I explored many new ideas for speeding up Boggle solving, but there were five that panned out:

1. Play a slightly different version of Boggle where you can find the same word as many times as you like.
2. Build the “evaluation tree” used to calculate the max/no-mark bound explicitly in memory.
3. Implement “pivot” and “lift” operations on this tree to synchronize letter choices across subtrees.
4. Aggressively compress and de-duplicate the evaluation tree.
5. Use three letter classes instead of four.

### Multi-Boggle

Looking at the best 3x3 board:

```
P E R
L A T
D E S
```

There are two different ways to find the word “LATE”:

```
P E R   P E\R
L-A-T   L-A-T
D E/S   D E S
```

In regular Boggle you’d only get points for finding LATE once. But for our purposes, this will wind up being a global constraint that’s hard to enforce. Instead, we just give you two points for it. We’ll call this “Multi-Boggle”. The score of a board in Multi-Boggle is always higher than its score in regular Boggle, so it’s still an upper bound.

If there are no repeat letters on the board, then the score is the same as in regular Boggle. In other words, while you can find LATE twice, you still can’t find LATTE because there’s only one T on the board.

In practical terms, this means that we’re going to focus solely on the max/no-mark bound and forget about the sum/union bound. The max/no-mark bound for a concrete board (one with a single letter on each cell) is its Multi-Boggle score.

TODO: explain later on where this assumption becomes important. Or move this section later.

### The Evaluation Tree

The fundamental flaw in my approach from 2009 (repeatedly splitting up cells in a board class) is that there’s an enormous amount of duplicated work. When you split up the middle cell into each possible vowel, the five board classes you get have a lot in common. Every word that doesn’t go through the middle cell is identical. It would be nice if we could avoid repeating that work.

Back in 2009, I implemented the max/no-mark upper bound by recursively searching over the board and the dictionary Trie. This was a natural generalization of the way you score a concrete Boggle board. It didn’t use much memory, but it also didn’t leave much room for improvement.

You can visualize a series of recursive function calls as a tree. The key advance in 2025 is to form this tree explicitly in memory. This is more expensive, but it gives us a lot of options to speed up subsequent steps.

Here’s an example of what one of these trees looks like:

(image)

This is a small tree, but in practice they can be quite large. The tree for the 3x3 board class we’ve been looking at has 520,947 nodes and the 3x4 and 4x4 trees can be much larger.

I actually [tried this] in 2009, but I [abandoned it] because I wasn’t seeing a big enough speedup in subsequent steps (scoring boards with a split cell) to justify building the tree.

What did I miss in 2009? Sadly, I had a [TODO] that turned out to be critical: rather than pruning out trees that don’t lead to points in a second pass, it’s much faster and results in less memory fragmentation if you do it as you build the tree. A 33% speedup becomes a 2x speedup. Maybe if I’d discovered that in 2009 I would have kept going!

The other discovery was that there was a more important operation to speed up.

[tried this]: https://github.com/danvk/performance-boggle/blob/master/tree_tool.cc
[abandoned it]: Disappointment: https://github.com/danvk/performance-boggle/commit/ec55e1c55cb1e5ad66e0784e3bd318a59c8812af
[TODO]: https://github.com/danvk/performance-boggle/blob/2710062fca308b93a6ee6a19980d6bcb4218b6e8/breaking_tree.cc#L34

### “Pivot” and “Lift” operations

After we found an upper bound on the 3x3 board class, the next operation was to split up the middle cell and consider each of those five (smaller) board classes individually. Now that we have a tree, the question becomes: how do you go from the initial tree to the tree you’d get for each of those five board classes?

There’s another way to think about this problem. Why is the max/no-mark bound imprecise? Why doesn’t it get us the score of the best board in the class? Its flaw is that you don’t have make consistent choices across different subtrees:

(image)

In one subtree you might make a choice for cell 1 and then cell 2, whereas in another subtree you might make a choice for cell 2 and then cell 1. If we adjusted the tree so that the first thing you did was make a choice for cell 1, then the subtrees would all be synchronized and the bound would go down:

(image)

What we need is a “pivot” operation to lift a particular choice node up to the top of the tree. You can work out how to do this for each type of node. It helps a lot to draw the lift operation.

- If a subtree doesn’t involve a choice for cell N, then we don’t have to change it.
- Lifting through a choice node.
- Lifting through a sum node.

If you lift the choice for the middle cell of the 3x3 board to the top of the tree, you wind up with this:

(image)

There’s a choice node with five sum nodes below it, and the bound is lower. Now if you lift another cell to the top, you’ll get two layers of choice nodes with sum nodes below them:

(image)

And again, the bound is lower. If you keep doing this, you build up a “pyramid” of choice nodes at the top of the tree. If the bound on any of these nodes drops below the highest score we know about, we can prune it out. This is equivalent to the “stop” condition from the 2009 algorithm, it’s just that we’re doing it in tree form.

This “lift” operation is not cheap. The cost of making choices in an unnatural order is that the tree gets larger. Here’s the tree size if you lift all nine cells of the 3x3 board:

| Step | Nodes |
| --- | --- |
| (initial) | 520,947 |
| 1 | 702,300 |
| 2 | 1,315,452 |
| 3 | 2,527,251 |
| 4 | 5,158,477 |
| 5 | 8,395,605 |
| 6 | 14,889,665 |
| 7 | 18,719,619 |
| 8 | 11,205,272 |
| 9 | 4,143,221 |

The node count goes up slowly, then more rapidly, and then it comes down again as we’re able to prune more subtrees. At the end of this, there’s only 428 concrete boards (out of 5,625,000 boards in the class) that we need to test.

Does 4 million nodes seem like a lot for only 428 Boggle boards? It is. There are a few important tweaks we can make to keep the tree small as we lift choices.

TODO: could mention that it's storing a trie under each choice node

### Compression and De-duping

Keeping the tree as small as possible is essential for solving Boggle quickly. There are two inefficient patterns we can identify and fix in our trees to keep them compact.

1. Collapse chains of sum nodes into a single sum node.
2. Merge sibling choice nodes.

(example of each)

Here are the node counts when you add compression after each pivot:

| Step | Nodes |
| --- | --- |
| (initial) | 520,947 |
| 1 | 669,156 |
| 2 | 1,054,515 |
| 3 | 1,726,735 |
| 4 | 2,675,250 |
| 5 | 2,620,720 |
| 6 | 1,420,925 |
| 7 | 301,499 |
| 8 | 39,667 |
| 9 | 9,621 |

These are considerably better, particularly after more lift operations. Compression on its own is a 2-3x speedup.

(introduce de-duplication)

| Step | Unique Nodes |
| --- | --- |
| (initial) | 98,453 |
| 1 | 117,602 |
| 2 | 215,121 |
| 3 | 318,088 |
| 4 | 592,339 |
| 5 | 754,947 |
| 6 | 481,449 |
| 7 | 125,277 |
| 8 | 27,125 |
| 9 | 9,613 |

Whereas compression is more effective at reducing node counts after many lifts, de-duplication is better at reducing (unique) node counts initially and after fewer lifts. Only processing each unique node once can potentially save us a lot of time. One way to think about this is that it allows us to [memoize] the pivot operation. Another is that it turns the tree into a [DAG].

[memoize]: https://en.wikipedia.org/wiki/Memoization
[dag]: https://en.wikipedia.org/wiki/Directed_acyclic_graph

### Use three letter classes instead of four

The net effect of all these changes is that we’re able to “break” difficult board classes much more efficiently. (ADD EXAMPLES)

If hard board classes aren’t so bad any more, maybe we should have more of them? If we use use three letter buckets instead of four, it significantly reduces the number of board classes we need to consider:

- Four letter buckets: 4^12/4 ≈ 4.2M boards classes
- Three letter buckets: 3^12/4 ≈ 133k board classes

The board classes with three letter buckets are going to be bigger and harder to break. But with our new tools, these are exactly the sort of boards on which we get the biggest improvement. So long as the average breaking time doesn’t go up by more than a factor of ~32x (4.2M/133k), using three buckets will be a win.

In practice it only takes ~10x longer, so this is around a 3x speedup.

Why not keep going to two classes, or even just one? The cost is memory and reduced parallelism. “Chunkier” board classes require bigger trees, and RAM is a finite resource. Moreover, the fewer letter buckets we use, the more skewed the distribution of breaking times gets. Some board classes remain trivial to break (ones with all consonants, for example), but others are real beasts. On the full 3x4 run, the fastest board was broken in 0.003s whereas the slowest took 2297s. It’s harder to distribute these uneven tasks evenly across many cores or many machines to get the full speedup you expect from distribution.

## Putting it all together

For each board class, the algorithm is:

1. Build the evaluation tree.
2. “Lift” a few choice cells to the top.
3. Continue splitting cells without modifying the tree, ala the 2009 approach.

The right number of “lifts” depends on the board and the amount of memory you have available. Harder boards benefit from more lifts, but this takes more memory.

Using this approach, I was able to evaluate all the 3x4 Boggle board classes on a 192-node C4 cloud instance in 8–9 hours, roughly $100 of compute time. The results? There are exactly five boards that score more than 1600 points with the ENABLE2K word list:

- srepetaldnis (1651)
- srepetaldnic (1614)
- srepetaldnib (1613)
- sresetaldnib (1607)
- sresetaldnip (1607)

The best one is the same one I found through simulated annealing. The others are 1-2 character variations on it. It would have been more exciting if there were a new, never before seen board. But we shouldn’t be too surprised that simulated annealing found the global optimum. After all, it did for 3x3 Boggle, too. And Boggle is “smooth” in the sense that similar boards tend to have similar scores. It would be hard for a great board to “hide” far away from any other good boards.

## Next Steps

This is an exciting result! After 15 years, it is meaningful progress towards the goal of finding the globally-optimal 4x4 Boggle board.

There are still many optimizations that could be made. My 2025 code only wound up being a 3-4x speedup vs. my 2009 code when I ran it on the 192-core machine. This was because I had to dial back a few of the optimizations because I kept running out of memory. So changes that reduce memory usage would likely be the most impactful.

On the other hand, I don’t think there’s simple optimizations to my current approach that will yield more than a 10x performance improvement. So while I might be able to break 3x4 Boggle more efficiently, it’s not going to make a big dent in 4x4 Boggle. Remember that 1,000,000x increase in difficulty from earlier. For 4x4 Boggle, we still need a different approach. (Or $100M of compute time!)

I have a few ideas about what that might be, but they’ll have to wait for another post!

## Appendix

That's it for the post, but I also have some thoughts on [pybind11] and working on optimization problems in general that I wanted to jot down.

### Python and C++ are a great mix! But C++ is still hard.

Before I started making algorithmic improvements, my goal was to run my [2009 C++ Boggle code] from Python. My hope was that this would give me a nice mix of C++’s speed and Python’s developer productivity. Since I already had working C++ code, I didn’t want to adopt a tool like [Cython] that compiled to C.

I wound up using [pybind11], which is derived from [Boost Python]. It simplifies the process of creating a Python extension from your existing C++ code. In addition to providing a convenient syntax for exposing C++ functions and classes to Python, it automatically converts all the STL containers between Python and C++ for you. It’s a really nice piece of software! There’s a newer tool from the same author called [nanobind], but it pushes you to adopt CMake and I didn’t really feel like figuring out how to do that.

So is pybind11 the best of both worlds? Development nirvana? Sort of! It definitely delivers on the promise of making a mixed Python/C++ project manageable. That being said, you’re still using C++, and you still need to think about memory management. pybind11 tries to help with this: if you return a `unique_ptr` or raw pointer from a function that’s called from Python, it will manage that memory for you. But sometimes the memory management situation is more complex, and you still get the joy of debugging memory leaks and segfaults.

Some quick notes:

- I really liked writing tests for my C++ code in Python. Python test runners and debuggers tend to be a lot easier to set up than their C++ equivalents.
- So long as your C++ function calls take >1ms or so, you probably won’t have to worry about pybind11 overhead.
- Almost all my segfaults were because pybind11 [takes ownership] of any pointers you return. If you don’t want this, you need to specify `py::return_value_policy::reference`.

My workflow for exploring an optimization eventually wound up being: develop it in Python (including debug and iterating), then port it to C++ and make sure that the tests match. This meant that I could spend most of my time iterating and exploring in Python-land.

This generally worked pretty well. However, as I learned, optimizations in Python often do not translate to C++.

[Cython]: https://cython.readthedocs.io/en/stable/src/quickstart/build.html
[2009 C++ Boggle code]: https://github.com/danvk/performance-boggle
[pybind11]: https://github.com/pybind/pybind11
[Boost Python]: https://www.boost.org/doc/libs/1_58_0/libs/python/doc/
[nanobind]: https://nanobind.readthedocs.io/en/latest/index.html
[takes ownership]: https://pybind11.readthedocs.io/en/stable/advanced/functions.html#return-value-policies

### Optimization work is intellectually and psychologically hard

Designing and optimizing novel algorithms like this is hard, both intellectually and psychologically. I think the intellectual challenge is clear. These are hard problems to wrap your head around.

It’s hard psychologically because, when you come up with an idea, you invest a lot of time into building it out before you find out whether it’s going to work. If you sink a week into something you think is going to be a 5x speedup, and then it winds up having no effect, it’s incredibly disheartening. I think this is why I stopped working on Boggle in 2009.

It can be very hard to predict whether an optimization will pan out. This was a place where my development process (prototype in Python, then translate to C++) sometimes failed me. For example, de-duplicating nodes in the tree was an enormous win in Python, something like a 4-5x speedup. But when I ported it to C++, it was actually slower! Why? Executing Python code is slow, so anything you can do to move more of your code into C will be a win. Presumably `__hash__` is implemented in C, so relying more on `dict`s to de-dupe nodes was a subtle way to shift work into C code.

It’s likely that there were some C++ wins that I didn’t pursue because they weren’t wins in Python. For example, I [developed] an entirely different tree representation that used fewer nodes, then abandoned it. Now I suspect it would have been a win. You optimize for the environment you develop in.

This also came up when I first ran my code on the cloud machine. I was surprised how much slower it was than on my MacBook. Apple’s M chips are known for having very high memory bandwidth, and one theory is that my algorithm is subtly reliant on that. A different strategy might work better on the C4s.

Optimization work is also hard in that you never know whether you’re one tweak away from a big win. You don’t want to abandon an approach just before you get to the payoff. But at the same time, you don’t want to keep sinking more time into a bad strategy. See my infamous [TODO] from 2009. I was one small tweak away from a big win. But I’d already sunk weeks of development time in by then and decided to cut my losses.

[developed]: https://github.com/danvk/hybrid-boggle/tree/clean-tree
