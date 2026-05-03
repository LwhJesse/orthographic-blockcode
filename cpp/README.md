# C++ Engine Plan

This directory is a **plan and placeholder**, not the current runnable reference evaluator.

Current status:

- Python is the working reference evaluator.
- `cpp/evaluator_skeleton.cpp` is only a skeleton.
- The runnable compiled backend in this repository is the CUDA prototype in `cpp_cuda/`.

For actual run commands, see:

- [Repository README](../README.md)
- [Detailed running guide](../docs/RUNNING.md)

The intended C++ engine should eventually reproduce the Python outputs, then become the CPU backend for optimization.

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
