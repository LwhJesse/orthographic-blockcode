# Running the Prototype

This document explains how to run the repository in its current state.

The short version is:

- The **Python evaluator** is the current reference implementation.
- The **CUDA evaluator** is a prototype batch backend.
- The **`cpp/` directory is not a finished CPU evaluator**. It currently contains a skeleton only.

If you only want to confirm that the repository works, start with the Python sample workflow first. It runs on a normal Python installation and does not require CUDA.

## 1. What is runnable today?

There are three practical entry points:

1. Python reference evaluator:

   ```bash
   python -m blockcode.cli evaluate ...
   ```

2. Python helper workflows:

   ```bash
   bash scripts/run_sample.sh
   bash scripts/run_dirty.sh
   python -m blockcode.cli mine ...
   python -m blockcode.cli optimize-greedy ...
   ```

3. CUDA prototype evaluator:

   ```bash
   ninja
   ./bin/blockcode_cuda_eval ...
   ```

There is also a script in `python/optimize_cuda_greedy.py`, but it is a controller around the CUDA evaluator, not the primary reference implementation.

Repository-provided Python/CUDA comparison helpers:

- `scripts/compare_python_cuda_sample.sh`
- `scripts/compare_python_cuda_dirty.sh`

## 2. Repository roles

Use the repository with this mental model:

- `blockcode/`
  Python reference implementation. This is the main place to study semantics and current behavior.
- `tests/`
  Smoke tests for the Python path.
- `scripts/`
  Reproducible helper commands for sample and dirty-text runs.
- `cpp_cuda/`
  CUDA batch evaluator prototype.
- `cpp/`
  Placeholder CPU evaluator skeleton, not a finished backend.
- `configs/`
  Rule table and settings.
- `data/examples/`
  Small sample article, dirty article, toy lexicon, and mapping-batch examples.

## 3. Python prerequisites

The Python path has no external runtime dependencies beyond Python itself.

Minimum expectation:

```bash
python --version
pytest --version
```

The repository currently targets Python 3.10+ in `pyproject.toml`.

## 4. Fastest smoke test

Run the bundled Python sample workflow:

```bash
bash scripts/run_sample.sh
```

This does two things:

1. Evaluates the sample article with the Python reference evaluator.
2. Mines candidate chunks from the same sample article.

Expected output directory:

```text
out/sample/
```

Expected output files:

```text
out/sample/token_paths.csv
out/sample/summary.json
out/sample/report.md
out/sample/key_events.csv
out/sample/keylog.txt
out/sample/lexicon_words.csv
out/sample/lexicon_summary.json
out/sample/collisions.csv
out/mined_chunks.tsv
```

## 5. Python reference evaluator

### 5.1 Minimal command

```bash
python -m blockcode.cli evaluate \
  --rules configs/rules_v1.tsv \
  --settings configs/settings_default.json \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/sample_article.txt \
  --outdir out/sample_manual
```

### 5.2 What it writes

The evaluator writes:

- `token_paths.csv`
  One row per emitted token path or literal token.
- `summary.json`
  Aggregate corpus-level metrics.
- `report.md`
  A human-readable report assembled from the summary.
- `key_events.csv`
  Symbolic per-key event log.
- `keylog.txt`
  Space-separated symbolic key sequence.

### 5.3 What the summary means

Important summary fields:

- `baseline_total`
  Literal baseline cost of the target text under the current Python cost model.
- `total_cost`
  Best cost found under the current block-code rules and delimiter-aware commit model.
- `saved`
  `baseline_total - total_cost`
- `reduction_ratio`
  Relative savings ratio.
- `encoded_word_count`
  Number of words encoded through the rule system.
- `raw_word_count`
  Number of words forced into raw fallback mode.

## 6. Dirty-text workflow

The repository intentionally includes a harder sample with punctuation, URLs, mixed language, symbols, numbers, and unknown words.

Run:

```bash
bash scripts/run_dirty.sh
```

This is useful for understanding what the current prototype does **not** normalize away. The dirty sample is expected to exercise raw fallback heavily.

Typical result:

- many words stay raw;
- punctuation is partly consumed by the delimiter-aware model;
- non-ASCII and code-like spans remain mostly literal.

## 7. Python tests

Run:

```bash
pytest -q
```

Current test scope:

- smoke test only;
- validates that the sample evaluation path runs and produces non-empty results.

This is not a correctness proof. It is only a basic run check.

## 8. Mining candidate chunks

The chunk miner scans words and ranks repeated substrings by a simple frequency times saved-length heuristic.

Run:

```bash
python -m blockcode.cli mine \
  --corpus data/examples/sample_article.txt \
  --out out/mined_chunks.tsv \
  --top 100
```

Output format is TSV with columns such as:

```text
chunk  length  freq  prefix_freq  suffix_freq  score  suggested_scope
```

This output is intended as optimizer input, not as a final recommended rule table.

## 9. Python greedy optimizer

The Python greedy optimizer is still a prototype controller. It tries adding one chunk-to-key rule at a time and keeps only improvements.

Run:

```bash
python -m blockcode.cli optimize-greedy \
  --rules configs/rules_v1.tsv \
  --settings configs/settings_default.json \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/sample_article.txt \
  --candidates out/mined_chunks.tsv \
  --outdir out/greedy \
  --iterations 3 \
  --candidate-limit 20
```

Outputs:

- `optimized_rules.tsv`
- `greedy_log.csv`

This is CPU-bound and intentionally simple. The point is to validate the search loop shape before pushing more work into CUDA.

## 10. CUDA prerequisites

The CUDA path needs more than `nvcc`.

You need all of the following:

1. A working NVIDIA driver.
2. A CUDA-capable GPU visible to the current shell or session.
3. `nvcc` in `PATH`.
4. `nvidia-smi` able to communicate with the driver.

Check:

```bash
nvcc --version
nvidia-smi
```

If `nvidia-smi` fails, the repository may still compile the CUDA binary, but the evaluator will fail at runtime when it tries to allocate CUDA device memory.

## 11. CUDA build in the current repository

This repository already contains `build.ninja` and `config.ninja`.

### 11.1 Configure architecture

If auto-detection works:

```bash
bash scripts/configure_ninja.sh
```

If you want to set it manually:

```bash
bash scripts/configure_ninja.sh sm_86
```

Common architecture examples:

```text
sm_75  RTX 20 series / Turing
sm_86  RTX 30 series / Ampere
sm_89  RTX 40 series / Ada
sm_90  newer datacenter parts
```

### 11.2 Build

```bash
ninja
```

Expected output:

```text
bin/blockcode_cuda_eval
```

## 12. CUDA run commands

### 12.1 Single mapping

```bash
./bin/blockcode_cuda_eval \
  --rules configs/rules_v1.tsv \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/sample_article.txt \
  --out out/cuda_sample
```

### 12.2 Mapping batch

```bash
./bin/blockcode_cuda_eval \
  --rules configs/rules_v1.tsv \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/sample_article.txt \
  --mappings data/examples/mappings_example.tsv \
  --out out/cuda_batch
```

### 12.3 Helper scripts

If you prefer the bundled wrappers:

```bash
bash scripts/run_cuda_sample.sh
bash scripts/run_cuda_batch.sh
```

## 13. Important Python/CUDA status note

The Python and CUDA evaluators are aligned on the repository's bundled comparison checks:

- `sample_article.txt`
- `dirty_article.txt`

This matters. Today:

- Python remains the semantic reference.
- CUDA remains the batch-evaluation prototype backend.

That is a much stronger state than an unchecked prototype, but it is still not a formal proof that every future corpus or edge case will match on every field. Any serious optimization or paper-facing claim should continue to include an explicit alignment pass between the two implementations.

The repository now includes two small comparison scripts for that purpose:

```bash
./scripts/compare_python_cuda_sample.sh
./scripts/compare_python_cuda_dirty.sh
```

## 14. Why the CUDA result may differ or fail

Typical failure modes:

### 14.1 `nvidia-smi` fails

Meaning:

- driver stack is not active in the current session; or
- the current environment cannot access the host GPU.

### 14.2 `no CUDA-capable device is detected`

Meaning:

- the binary compiled successfully;
- the runtime did not find a usable GPU device.

This is a runtime environment failure, not necessarily a compiler failure.

### 14.3 `nvcc` exists, but running still fails

Meaning:

- compile-time tooling is present;
- runtime GPU access is still broken or unavailable.

## 15. Primary troubleshooting checklist

If the repository does not appear to work, check in this order:

1. Does `pytest -q` pass?
2. Does `bash scripts/run_sample.sh` produce `out/sample/summary.json`?
3. Does `bash scripts/run_dirty.sh` complete?
4. Does `nvcc --version` work?
5. Does `nvidia-smi` work in the same shell?
6. Does `ninja` produce `bin/blockcode_cuda_eval`?
7. Does the CUDA binary fail at compile time or only at runtime?

That sequence separates Python/package issues from CUDA environment issues very quickly.
