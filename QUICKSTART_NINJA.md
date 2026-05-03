# Quickstart: Ninja CUDA Build

This quickstart is for the **current repository layout**.

It does **not** assume a zip archive. You should run these commands from the repository root.

If you want the full run matrix, Python reference workflow, or troubleshooting, read:

- [Detailed running guide](docs/RUNNING.md)
- [详细运行说明](docs/RUNNING.zh-CN.md)

## 1. What this quickstart is for

Use this file only when you want to:

1. configure CUDA architecture for this repository;
2. build the CUDA evaluator with Ninja;
3. run the bundled CUDA sample or batch example.

If you only want to verify that the project works, start with the Python reference path first:

```bash
bash scripts/run_sample.sh
```

## 2. Prerequisites

You need:

- `nvcc`
- `ninja`
- a working NVIDIA driver
- a CUDA-capable GPU visible to the current shell

Check:

```bash
nvcc --version
ninja --version
nvidia-smi
```

If `nvidia-smi` fails, the CUDA binary may still compile, but it is likely to fail at runtime.

## 3. Configure architecture

Auto-detect:

```bash
bash scripts/configure_ninja.sh
```

Manual override:

```bash
bash scripts/configure_ninja.sh sm_86
```

Examples:

```text
sm_75  RTX 20 series / Turing
sm_86  RTX 30 series / Ampere
sm_89  RTX 40 series / Ada
sm_90  newer datacenter GPUs
```

This writes:

```text
config.ninja
```

## 4. Build

```bash
ninja
```

Expected output:

```text
bin/blockcode_cuda_eval
```

## 5. Run the CUDA sample

Direct command:

```bash
./bin/blockcode_cuda_eval \
  --rules configs/rules_v1.tsv \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/sample_article.txt \
  --out out/cuda_sample
```

Wrapper script:

```bash
bash scripts/run_cuda_sample.sh
```

Expected outputs:

```text
out/cuda_sample/cuda_summary.csv
out/cuda_sample/cuda_summary.json
```

## 6. Run the mapping batch example

Direct command:

```bash
./bin/blockcode_cuda_eval \
  --rules configs/rules_v1.tsv \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/sample_article.txt \
  --mappings data/examples/mappings_example.tsv \
  --out out/cuda_batch
```

Wrapper script:

```bash
bash scripts/run_cuda_batch.sh
```

Expected outputs:

```text
out/cuda_batch/cuda_summary.csv
out/cuda_batch/cuda_summary.json
```

## 7. Generate and evaluate rule-code mutations

Generate a mapping batch:

```bash
python tools/generate_rule_code_batch.py \
  --rules configs/rules_v1.tsv \
  --out out/mutations.tsv \
  --limit-rules 30
```

Evaluate it:

```bash
./bin/blockcode_cuda_eval \
  --rules configs/rules_v1.tsv \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/sample_article.txt \
  --mappings out/mutations.tsv \
  --out out/cuda_mutations
```

Inspect the best rows:

```bash
sort -t, -k2,2n out/cuda_mutations/cuda_summary.csv | head -20
```

## 8. Important current limitation

The CUDA evaluator is a prototype backend, but it is now aligned with the Python reference evaluator on the repository's bundled `sample` and `dirty` comparison checks.

Treat this path as:

- buildable;
- useful for prototype batch evaluation;
- validated on the bundled comparison workflows;
- still worth re-checking when you introduce new corpora or new edge cases.
```
