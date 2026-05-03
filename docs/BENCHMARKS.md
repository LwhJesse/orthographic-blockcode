# Benchmarks

The repository currently includes toy examples for smoke testing. These examples verify that the evaluator, CUDA backend, and mapping-batch path work.

A full benchmark should contain:

- a public lexicon;
- multiple domain corpora;
- train/validation/test split;
- domain weights;
- raw baseline;
- block-code results;
- collision and fallback statistics.

A weighted benchmark objective can be written as:

```text
C_weighted(J) = sum_{k=1..K} alpha_k * C(J, X_k)
```

Private chats, copyrighted articles, paid publications, and raw social-media dumps should not be committed to the repository. Use public/open corpora or local aggregate statistics.
