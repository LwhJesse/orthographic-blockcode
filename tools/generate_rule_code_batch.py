#!/usr/bin/env python3
"""
Generate a mapping batch TSV by mutating existing rule codes.

This is a utility for the CUDA evaluator.

Example:
  python tools/generate_rule_code_batch.py \
    --rules configs/rules_v1.tsv \
    --out out/mutations.tsv \
    --limit-rules 20
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--alphabet", default="abcdefghijklmnopqrstuvwxyz")
    ap.add_argument("--limit-rules", type=int, default=0)
    args = ap.parse_args()

    with args.rules.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    rows = [r for r in rows if r.get("enabled", "1") == "1" and r.get("rule_id") and r.get("code")]
    rows = [r for r in rows if not r["rule_id"].startswith("literal_")]
    if args.limit_rules > 0:
        rows = rows[: args.limit_rules]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["mapping_id", "rule_id", "code"])
        mid = 0
        for r in rows:
            old = r["code"]
            for key in args.alphabet:
                if key == old:
                    continue
                w.writerow([f"m{mid}", r["rule_id"], key])
                mid += 1

    print(f"Wrote {mid} mapping mutations to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
