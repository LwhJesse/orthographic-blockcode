# C++ Engine Plan

The current working evaluator is Python.

The intended C++ engine should reproduce the same outputs, then become the CPU backend for optimization.

Target CLI:

```bash
blockcode_eval \
  --rules configs/rules_v1.tsv \
  --settings configs/settings_default.json \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/sample_article.txt \
  --outdir out/cpp_sample
```

Implementation priorities:

1. TSV/JSON loading.
2. Tokenization.
3. Rule trie.
4. Word-level DP.
5. Candidate index.
6. Per-token path CSV.
7. Multi-threaded batch evaluation.

CUDA should come after the C++ evaluator is correct.
