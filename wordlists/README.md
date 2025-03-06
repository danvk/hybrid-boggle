# Wordlists for Boggling

The score of a Boggle board depends on your choice of dictionary. There are a few standard word lists that you can use, and you'll get slightly different results depending on which one you pick.

## Processed word lists

The files in the `raw` subdirectory are the original word lists.
The files in this directory are "bogglified" versions of the same word lists.
This means they've been processed in three ways:

1. Remove words shorter than 3 letters. (Long words are kept to support 5x5 Boggle.)
2. Remove words containing a "q" not followed by a "u", for example "niqab". There's only a "Qu" die in Boggle, so it's not possible to spell these.
3. Replace all occurences of "qu" with "q". This simplifies the code considerably.

To go from a "raw" to a "bogglified" word list, run `make_boggle_dict.py`:

    ./boggle/make_boggle_dict.py wordlists/raw/enable2k.txt > wordlists/enable2k.txt

The processed word lists will have slightly fewer words than the raw versions.

To generate all the wordlists, run `./wordlists/generate.sh`.

## Notes on sources

There are five word lists in this repo:

- [ENABLE2K]: This is the default word lists, compiled in 1997 and 2000 by Alan Beale. Check out [his web site] for more background and a fun trip back to 2000.
- [NASPA23]: aka TWL aka OTCWL aka OWL aka NWL. This is the official word list for competitive Scrabble play in the United States and Canada. This file comes from the [scrabblewords] repo.
- [OSPD]: the Official Scrabble Players Dictionary, this is intended for casual Scrabble play and omits many obscure words. This file comes from the [scrabblewords] repo.
- [YAWL]: Yet Another Word List. Compiled by Mendel Leo Cooper (a.k.a. thegrendel), this is a superset of ENABLE2K and OSW (Official Scrabble Words). This files comes from the yawl repo. Last updated 2008.
- [SOWPODS]: aka CSW (Collins Scrabble Words). This is the union of OSPD and OSW. It includes both American and British spellings of words. This file comes from the [scrabblewords] repo (`British/CSW21.txt`).
- [TWL06]: 2006 Tournament Word List (Official Scrabble Dictionary). This was a popular word list in the 2000s and is helpful for comparing against other Boggle-related content on the web.

Word counts:

|          File |    Raw | Processed |
| ------------- | ------ | --------- |
|  enable2k.txt | 173528 |    173402 |
| naspa2023.txt | 196601 |    196431 |
|     ospd5.txt | 109928 |    109762 |
|   sowpods.txt | 279078 |    278846 |
|     twl06.txt | 178691 |    178549 |
|      yawl.txt | 264097 |    263904 |

There's also `enable2k.jpa14.txt`, which is a filtered version of `enable2k.txt` that only includes the 14 letters approved in [this 2010 blog post]. It has 42,625 words.

[scrabblewords]: https://github.com/scrabblewords/scrabblewords/tree/main/words/North-American
[ENABLE2K]: https://everything2.com/title/ENABLE+word+list
[his web site]: https://web.archive.org/web/20070223061843/http://personal.riverusers.com/%7Ethegrendel/software.html
[NASPA23]: https://www.scrabbleplayers.org/w/NWL2023
[OSPD]: https://en.wikipedia.org/wiki/Official_Scrabble_Players_Dictionary
[YAWL]: https://github.com/elasticdog/yawl
[SOWPODS]: https://en.wikipedia.org/wiki/Collins_Scrabble_Words
[TWL06]: https://www.freescrabbledictionary.com/twl06/
[this 2010 blog post]: https://web.archive.org/web/20101207194405/http://www.pathcom.com/~vadco/deep.html#acknowledgements:~:text=The%20lexicon%20and%20character%20set%20choices
