# CUDA Plan

Do not put raw text parsing on GPU.

GPU stage should receive integerized data:

```text
chunk ids
path ids
word ids
mapping batch
word frequencies
article word counts
```

Suggested CUDA kernels:

1. `encode_paths_kernel`
   - input: mapping batch + path_chunks
   - output: entries `(mapping_id, packed_code, word_id, code_len, path_id)`

2. sort entries using CUB/Thrust.

3. `assign_candidate_rank_kernel`
   - after sorting by `(mapping_id, code, -freq)`

4. `reduce_word_min_cost_kernel`
   - reduce min cost for `(mapping_id, word_id)`

5. `reduce_article_cost_kernel`
   - dot best word costs with article word counts.

CPU remains the search controller.
