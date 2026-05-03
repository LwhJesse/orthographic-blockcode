#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root_dir"

python_out="out/compare_python_sample"
cuda_out="out/compare_cuda_sample"

python -m blockcode.cli evaluate \
  --rules configs/rules_v1.tsv \
  --settings configs/settings_default.json \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/sample_article.txt \
  --outdir "$python_out" >/dev/null

if [[ ! -x bin/blockcode_cuda_eval ]]; then
  echo "bin/blockcode_cuda_eval not found. Building with Ninja..."
  ninja
fi

./bin/blockcode_cuda_eval \
  --rules configs/rules_v1.tsv \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/sample_article.txt \
  --out "$cuda_out" >/dev/null

python - <<'PY'
import csv
import json
from pathlib import Path

python_summary = json.loads(Path("out/compare_python_sample/summary.json").read_text(encoding="utf-8"))
with Path("out/compare_cuda_sample/cuda_summary.csv").open(newline="", encoding="utf-8") as f:
    cuda_row = next(csv.DictReader(f))

keys = [
    ("baseline_total", int),
    ("total_cost", int),
    ("saved", int),
    ("reduction_ratio", float),
]

print("field\tpython\tcuda\tdelta")
for key, caster in keys:
    pv = caster(python_summary[key])
    cv = caster(cuda_row[key])
    delta = pv - cv
    print(f"{key}\t{pv}\t{cv}\t{delta}")
PY
