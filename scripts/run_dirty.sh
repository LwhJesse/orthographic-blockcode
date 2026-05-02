#!/usr/bin/env bash
set -euo pipefail

python -m blockcode.cli evaluate \
  --rules configs/rules_v1.tsv \
  --settings configs/settings_default.json \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/dirty_article.txt \
  --outdir out/dirty \
  --analyze-lexicon

echo
echo "Summary:"
cat out/dirty/summary.json

echo
echo "First 30 token paths:"
python - <<'PY'
import csv
from pathlib import Path
p = Path("out/dirty/token_paths.csv")
with p.open(newline='', encoding='utf-8') as f:
    for i, row in enumerate(csv.DictReader(f)):
        if i >= 30:
            break
        print(row["index"], row["type"], repr(row["token"]), row["mode"], row["cost"], row["code"], row["input_sequence"], row["delimiter_kind"], repr(row["delimiter_literal"]), row["consumed_next_chars"])
PY

echo
echo "First 80 symbolic keys:"
python - <<'PY'
from pathlib import Path
keys = Path("out/dirty/keylog.txt").read_text(encoding="utf-8").split()
print(" ".join(keys[:80]))
PY
