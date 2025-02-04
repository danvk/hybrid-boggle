# Wordlists for Boggling

The score of a Boggle board depends on your choice of dictionary. There are a few standard word lists that you can use, and you'll get slightly different results depending on which one you pick.

## Processed word lists

The files in the `raw` subdirectory are the original word lists.
The files in this directory are "bogglified" versions of the same word lists.
This means they've been processed in three ways:

1. Remove words shorter than 3 letters or longer than 17. (There are 16 dice in Boggle and one of them has a "Qu" on it, so the longest word is 17 letters.)
2. Remove words containing a "q" not followed by a "u", for example "niqab". There's only a "Qu" die in Boggle, so it's not possible to spell these.
3. Replace all occurences of "qu" with "q". This simplifies the code considerably.

To go from a "raw" to a "bogglified" word list, run `make_boggle_dict.py`:

    ./boggle/make_boggle_dict.py wordlists/raw/enable2k.txt > wordlists/enable2k.txt

The processed word lists will have slightly fewer words than the raw versions.

## Notes on sources

There are five word lists in this repo:

- [ENABLE2K]: This is the default word lists, compiled in 1997 and 2000 by Alan Beale. Check out [his web site] for more background and a fun trip back to 2000. It contains 173,528 words raw and 172,203 processed.
- [NASPA23]: aka TWL aka OTCWL aka OWL aka NWL. This is the official word list for competitive Scrabble play in the United States and Canada. It contains 196,601 words raw and 196,431 processed. This file comes from the [scrabblewords] repo.
- [OSPD]: the Official Scrabble Players Dictionary, this is intended for casual Scrabble play and omits many obscure words. It contains 109,928 words raw and 109,762 processed. This file comes from the [scrabblewords] repo.
- [YAWL]: Yet Another Word List. Compiled by Mendel Leo Cooper (a.k.a. thegrendel), this is a superset of ENABLE2K and OSW (Official Scrabble Words). It contains 264,097 words raw and 261,995 processed. This files comes from the yawl repo. Last updated 2008.
- [SOWPODS]: aka CSW (Collins Scrabble Words). This is the union of OSPD and OSW. It includes both American and British spellings of words. It contains 279,078 words raw and 278,846 processed. This file comes from the [scrabblewords] repo (`British/CSW21.txt`).

[scrabblewords]: https://github.com/scrabblewords/scrabblewords/tree/main/words/North-American
[ENABLE2K]: https://everything2.com/title/ENABLE+word+list
[his web site]: https://web.archive.org/web/20070223061843/http://personal.riverusers.com/%7Ethegrendel/software.html
[NASPA23]: https://www.scrabbleplayers.org/w/NWL2023
[OSPD]: https://en.wikipedia.org/wiki/Official_Scrabble_Players_Dictionary
[YAWL]: https://github.com/elasticdog/yawl
[SOWPODS]: https://en.wikipedia.org/wiki/Collins_Scrabble_Words
