#!/usr/bin/env bash
set -euo pipefail
python -m blockcode.cli evaluate \
  --rules configs/rules_v1.tsv \
  --settings configs/settings_default.json \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/sample_article.txt \
  --outdir out/sample \
  --analyze-lexicon
python -m blockcode.cli mine \
  --corpus data/examples/sample_article.txt \
  --out out/mined_chunks.tsv \
  --top 100
