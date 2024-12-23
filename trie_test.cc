#include <assert.h>
#include <stdio.h>
#include <unistd.h>
#include <string>
#include <vector>

#include "test.h"
#include "trie.h"

using paper::Trie;

int main(int argc, char** argv) {
  char tmp_file[] = "/tmp/trie-words.XXXXXX";
  mkstemp(tmp_file);

  FILE* f = fopen(tmp_file, "w");
  assert(f);

  fprintf(f, "agriculture\n");
  fprintf(f, "culture\n");
  fprintf(f, "boggle\n");
  fprintf(f, "tea\n");
  fprintf(f, "sea\n");
  fprintf(f, "teapot\n");
  fclose(f);

  for (int i = 0; i < 5; i++) {
    Trie* t = Trie::CreateFromFile(tmp_file);
    CHECK(NULL != t);

    CHECK_EQ(6, t->Size());
    CHECK(NULL != t->FindWord("agriculture"));
    CHECK(NULL != t->FindWord("culture"));
    CHECK(NULL != t->FindWord("boggle"));
    CHECK(NULL != t->FindWord("tea"));
    CHECK(NULL != t->FindWord("teapot"));
    CHECK_EQ((Trie*)NULL, t->FindWord("teap"));
    CHECK_EQ((Trie*)NULL, t->FindWord("random"));
    CHECK_EQ((Trie*)NULL, t->FindWord("cultur"));

    // Get a full word to test marking
    Trie* wd = t->Descend('t' - 'a');
    CHECK(NULL != wd);
    wd = wd->Descend('e' - 'a');
    CHECK(NULL != wd);
    wd = wd->Descend('a' - 'a');
    CHECK(NULL != wd);
    CHECK_EQ(0, wd->Mark());
    wd->Mark(12345);
    CHECK_EQ(12345, wd->Mark());

    Trie* child = t->FindWord("agriculture");
    CHECK(child != NULL);
    CHECK_EQ(Trie::ReverseLookup(t, child), "agriculture");
    delete t;
  }
  int res = remove(tmp_file);
  CHECK_EQ(0,res);
  printf("%s: All tests passed!\n", argv[0]);
}
