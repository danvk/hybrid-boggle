#!/usr/bin/env python

import example
# print(example.add(1, 2))
# print(example.add(i=1, j=2))

# print(example.fib(100000))

# Constructing the Trie in Python causes a malloc error & does not work.
# t = example.Trie()
# print(t)
# t.AddWord("hello")
# t.AddWord("goodbye")
# print(t.FindWord("hello"))
# print(t.FindWord("farewell"))

t = example.Trie.CreateFromFile("words")
print("num words:", t.Size())
print("num nodes:", t.NumNodes())
print("hello:", t.FindWord("hello"))
print("heloo:", t.FindWord("heloo"))
t.SetMark(1)
print("root mark:", t.Mark())

child = t.FindWord("python")
print(child)
print("reverse:", example.Trie.ReverseLookup(t, child))
