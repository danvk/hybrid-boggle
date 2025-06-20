# Wordlists for Boggling

The score of a Boggle board depends on your choice of dictionary. There are a few standard word lists that you can use, and you'll get slightly different results depending on which one you pick.

## Notes on sources

There are five word lists in this repo:

- [ENABLE2K]: This is the default word lists, compiled in 1997 and 2000 by Alan Beale. Check out [his web site] for more background and a fun trip back to 2000. The longest word is 28 letters ("[ethylenediaminetetraacetates]").
- [NASPA23]: aka TWL aka OTCWL aka OWL aka NWL. This is the official word list for competitive Scrabble play in the United States and Canada. This file comes from the [scrabblewords] repo. Since it's designed for Scrabble, it only contains words up to 15 letters.
- [OSPD]: the Official Scrabble Players Dictionary, this is intended for casual Scrabble play and omits many obscure words. This file comes from the [scrabblewords] repo. Its longest word is 12 letters.
- [SOWPODS]: aka CSW (Collins Scrabble Words). This is the union of OSPD and OSW. It includes both American and British spellings of words. This file comes from the [scrabblewords] repo (`British/CSW21.txt`). Its longest word is 15 letters.
- [TWL06]: 2006 Tournament Word List (Official Scrabble Dictionary). This was a popular word list in the 2000s and is helpful for comparing against other Boggle-related content on the web. Its longest word is 15 letters.
- [YAWL]: Yet Another Word List. Compiled by Mendel Leo Cooper (a.k.a. thegrendel), this is a superset of ENABLE2K and OSW (Official Scrabble Words). This files comes from the yawl repo. Last updated 2008. Its longest word is 45 letters ("[pneumonoultramicroscopicsilicovolcanoconiosis]").

Some words aren't valid in Boggle. Specifically, words must be three letters or longer, and all Qs must be followed by a U. Words longer than 16 letters are kept to support 5x5 Boggle.

You can pass a different word list to most of the CLI tools in this repo with the `--dictionary` flag. Word lists are expected to be all lowercase with one word per line.

Word counts:

|          File |     Raw |  Boggle OK |
| ------------: | ------: | ---------: |
|  enable2k.txt | 173,528 |    173,402 |
| naspa2023.txt | 196,601 |    196,431 |
|     ospd5.txt | 109,928 |    109,762 |
|   sowpods.txt | 279,078 |    278,846 |
|     twl06.txt | 178,691 |    178,549 |
|      yawl.txt | 264,097 |    263,904 |

There's also `enable2k.jpa14.txt`, which is a filtered version of `enable2k.txt` that only includes the 14 "qualified" letters from [this 2010 blog post]. It has 42,625 words.

[scrabblewords]: https://github.com/scrabblewords/scrabblewords/tree/main/words/North-American
[ENABLE2K]: https://everything2.com/title/ENABLE+word+list
[his web site]: https://web.archive.org/web/20070223061843/http://personal.riverusers.com/%7Ethegrendel/software.html
[NASPA23]: https://www.scrabbleplayers.org/w/NWL2023
[OSPD]: https://en.wikipedia.org/wiki/Official_Scrabble_Players_Dictionary
[YAWL]: https://github.com/elasticdog/yawl
[SOWPODS]: https://en.wikipedia.org/wiki/Collins_Scrabble_Words
[TWL06]: https://www.freescrabbledictionary.com/twl06/
[this 2010 blog post]: https://web.archive.org/web/20101207194405/http://www.pathcom.com/~vadco/deep.html#acknowledgements:~:text=The%20lexicon%20and%20character%20set%20choices
[Pneumonoultramicroscopicsilicovolcanoconiosis]: https://en.wikipedia.org/wiki/Pneumonoultramicroscopicsilicovolcanoconiosis
[ethylenediaminetetraacetates]: https://en.wiktionary.org/wiki/ethylenediaminetetraacetate
