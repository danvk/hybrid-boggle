import pytest
from cpp_boggle import BucketBoggler34, Trie

from boggle.boggler import PyBoggler
from boggle.dimensional_bogglers import cpp_bucket_boggler
from boggle.ibuckets import PyBucketBoggler
from boggle.trie import PyTrie

BIGINT = 1_000_000


PARAMS = [(PyBucketBoggler, PyTrie), (cpp_bucket_boggler, Trie)]


@pytest.mark.parametrize("Boggler, TrieT", PARAMS)
def test_boards(Boggler: type[PyBucketBoggler], TrieT: type[PyTrie]):
    bb = Boggler(None, (3, 3))

    assert not bb.parse_board("")
    assert not bb.parse_board("abc def")
    assert not bb.parse_board("a b c d e f g h i j")
    assert not bb.parse_board("a b c d e  g h i")

    assert bb.parse_board("a b c d e f g h i")
    assert bb.as_string() == "a b c d e f g h i"
    assert bb.num_reps() == 1

    assert bb.parse_board("abc b c d e f g htuv pqrs")
    assert bb.as_string() == "abc b c d e f g htuv pqrs"
    assert 3 * 4 * 4 == bb.num_reps()


@pytest.mark.parametrize("Boggler, TrieT", PARAMS)
def test_bound(Boggler: type[PyBucketBoggler], TrieT: type[PyTrie]):
    t = TrieT()
    t.add_word("sea")
    t.add_word("seat")
    t.add_word("seats")
    t.add_word("tea")
    t.add_word("teas")

    bb = Boggler(t, (3, 3))

    assert bb.parse_board("a b c d e f g h i")
    assert 0 == bb.upper_bound(BIGINT)
    assert 0 == bb.details().sum_union
    assert 0 == bb.details().max_nomark

    # s e h
    # e a t
    # p u c
    assert bb.parse_board("s e p e a u h t c")
    score = bb.upper_bound(BIGINT)
    assert 4 == bb.details().sum_union  # sea(t), tea(s)
    assert 6 == bb.details().max_nomark  # seat*2, sea*2, tea
    assert 1 + 1 + 1 + 1 == score  # all words
    assert 4 == bb.upper_bound(BIGINT)

    # a board where both [st]ea can be found, but not simultaneously
    # st z z
    #  e a s
    assert bb.parse_board("st z z e a s z z z")
    score = bb.upper_bound(BIGINT)
    assert 3 == bb.details().sum_union  # tea(s) + sea
    assert 2 == bb.details().max_nomark  # tea(s)
    assert 2 == score
    assert 2 == bb.upper_bound(BIGINT)

    # Add in a "seat", test its (sum union's) shortcomings. Can't have 'seats'
    # and 'teas' on the board simultaneously, but it still counts both.
    # st z z
    #  e a st
    #  z z s
    assert bb.parse_board("st z z e a st z z s")

    score = bb.upper_bound(BIGINT)
    assert 2 + 4 == bb.details().sum_union  # all but "hiccup"
    assert 4 == bb.details().max_nomark  # sea(t(s))
    assert 4 == score


@pytest.mark.parametrize("Boggler, TrieT", PARAMS)
def test_q(Boggler, TrieT):
    t = TrieT()
    t.add_word("qa")  # qua = 1
    t.add_word("qas")  # qua = 1
    t.add_word("qest")  # quest = 2

    bb = Boggler(t, (3, 3))

    # q a s
    # a e z
    # s t z
    assert bb.parse_board("q a s a e z s t z")
    score = bb.upper_bound(BIGINT)
    assert 4 == bb.details().sum_union
    assert 6 == bb.details().max_nomark  # (qa + qas)*2 + qest
    assert 4 == score

    # Make sure "qu" gets parsed as "either 'qu' or 'u'"
    # qu a s
    # a e z
    # s t z
    assert bb.parse_board("qu a s a e z s t z")
    score = bb.upper_bound(BIGINT)
    assert 4 == bb.details().sum_union
    assert 6 == bb.details().max_nomark  # (qa + qas)*2 + qest
    assert 4 == score


@pytest.mark.parametrize("Boggler, TrieT", PARAMS)
def test_tar_tier(Boggler, TrieT):
    # https://www.danvk.org/wp/2009-08-11/a-few-more-boggle-examples/

    t = TrieT()
    t.add_word("tar")
    t.add_word("tie")
    t.add_word("tier")
    t.add_word("tea")
    t.add_word("the")

    bb = Boggler(t, (3, 3))

    #  t i z
    # ae z z
    #  r z z
    assert bb.parse_board("t i z ae z z r z z")
    assert 3 == bb.upper_bound(BIGINT)
    assert 3 == bb.details().sum_union
    assert 3 == bb.details().max_nomark
    assert 2 == bb.num_reps()

    #  t h .
    #  h e .
    #  . . .
    assert bb.parse_board("t h . h e . . . .")
    assert 1 == bb.upper_bound(BIGINT)
    assert 1 == bb.details().sum_union
    assert 2 == bb.details().max_nomark
    assert bb.as_string() == "t h . h e . . . ."


def test_tar_tier_boggler():
    # Analogous to test_tar_tier(), but try each board.
    t = PyTrie()
    t.add_word("tar")
    t.add_word("tie")
    t.add_word("tier")
    t.add_word("tea")
    t.add_word("the")

    b = PyBoggler(t, (4, 4))
    assert b.score("tizzazzzrzzzzzzz") == 1
    assert b.score("tizzezzzrzzzzzzz") == 2


def test_bucket_boggle34():
    t = Trie.create_from_file("wordlists/enable2k.txt")
    bb = BucketBoggler34(t)
    # s l p i a e n t r d e s
    assert bb.parse_board(
        "lnrsy lnrsy chkmpt aeiou aeiou aeiou lnrsy chkmpt lnrsy bdfgjvwxz aeiou lnrsy"
    )
    assert bb.upper_bound(BIGINT) > 1600
    d = bb.details()
    print(d.max_nomark, d.sum_union)
    assert d.max_nomark == 57_158
    assert d.sum_union == 353_018

    assert bb.parse_board("s i n d l a t e p e r s")
    assert bb.upper_bound(BIGINT) > 1600
    d = bb.details()
    print(d.max_nomark, d.sum_union)
    assert d.max_nomark == 1847
    assert d.sum_union == 1651
