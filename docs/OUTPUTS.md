# Output Fields

The CUDA evaluator prints and writes summary fields.

## Runtime counters

```text
rules
```

Number of enabled rules loaded by the backend, including literal fallback rules.

```text
words
```

Number of valid lexicon words.

```text
paths
```

Total number of segmentation paths enumerated across lexicon words.

```text
flat path rule ids
```

Total length of all flattened path rule-id sequences.

```text
mappings
```

Number of candidate mappings evaluated in the current run.

## Cost fields

```text
literal_base_cost
```

Cost of spans that are not handled by the word model.

```text
baseline_total
```

Literal baseline cost of the target article or corpus.

```text
total_cost
```

Theoretical input cost under the evaluated mapping.

### `$saved$`

Difference between baseline and block-code cost:

$$
saved = baseline\_total - total\_cost
$$

### `$reduction\_ratio$`

Relative reduction:

$$
reduction\_ratio
=
\frac{baseline\_total - total\_cost}{baseline\_total}
$$

## Output files

The CUDA sample writes:

```text
out/cuda_sample/cuda_summary.csv
out/cuda_sample/cuda_summary.json
```

Mapping-batch runs write the same files under the chosen output directory.
