#!/usr/bin/env bash
set -euo pipefail

if [[ ! -x bin/blockcode_cuda_eval ]]; then
  echo "bin/blockcode_cuda_eval not found. Building with Ninja..."
  scripts/build_cuda_ninja.sh
fi

bin/blockcode_cuda_eval \
  --rules configs/rules_v1.tsv \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/sample_article.txt \
  --out out/cuda_sample

echo
echo "Result:"
cat out/cuda_sample/cuda_summary.csv
