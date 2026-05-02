#!/usr/bin/env python3
"""
Greedy optimizer driver for the CUDA backend.

This script is intentionally simple:

1. Start from a rules TSV.
2. Mine or load candidate chunks separately.
3. For every candidate mutation chunk->key, generate a mapping batch TSV.
4. Call the CUDA evaluator.
5. Select the best mutation.
6. Apply it to the rules TSV.
7. Repeat.

This is not the final optimizer. It is the first CPU controller for the
GPU fitness evaluator.

Usage sketch:

python python/optimize_cuda_greedy.py \
  --rules configs/rules_v1.tsv \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/sample_article.txt \
  --chunks out/mined_chunks.tsv \
  --cuda-bin build-cuda/blockcode_cuda_eval \
  --outdir out/cuda_greedy \
  --iterations 3 \
  --candidate-limit 20
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path
from typing import Dict, List


def read_rules(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def write_rules(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["rule_id", "chunk", "code", "scope", "class", "enabled", "group", "note"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def read_chunks(path: Path, limit: int) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    return rows[:limit]


def make_batch(base_rules: list[dict], chunks: list[dict], alphabet: str, path: Path) -> list[tuple[str, str, str, str]]:
    """Generate mapping overrides.

    For the CUDA backend, a mapping batch changes existing rule ids.
    Therefore this prototype only mutates rules whose chunk already exists
    in rules.tsv. For new chunks, add them to rules.tsv first in Python-level
    preprocessing.

    Returns list of (mapping_id, rule_id, code, description).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = [r for r in base_rules if r.get("enabled", "1") == "1" and r.get("chunk")]
    candidates = []
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["mapping_id", "rule_id", "code"])
        mid = 0
        for r in existing:
            old = r["code"]
            for key in alphabet:
                if key == old:
                    continue
                mapping_id = f"m{mid}"
                w.writerow([mapping_id, r["rule_id"], key])
                candidates.append((mapping_id, r["rule_id"], key, f'{r["chunk"]}:{old}->{key}'))
                mid += 1
    return candidates


def run_cuda(cuda_bin: Path, rules: Path, lexicon: Path, article: Path, mappings: Path, out: Path) -> list[dict]:
    out.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(cuda_bin),
        "--rules", str(rules),
        "--lexicon", str(lexicon),
        "--article", str(article),
        "--mappings", str(mappings),
        "--out", str(out),
    ]
    subprocess.run(cmd, check=True)
    with (out / "cuda_summary.csv").open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", required=True, type=Path)
    ap.add_argument("--lexicon", required=True, type=Path)
    ap.add_argument("--article", required=True, type=Path)
    ap.add_argument("--chunks", required=True, type=Path)  # currently only for future extension
    ap.add_argument("--cuda-bin", required=True, type=Path)
    ap.add_argument("--outdir", required=True, type=Path)
    ap.add_argument("--iterations", type=int, default=3)
    ap.add_argument("--candidate-limit", type=int, default=20)
    ap.add_argument("--alphabet", default="abcdefghijklmnopqrstuvwxyz")
    args = ap.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    current_rules_path = args.outdir / "rules_iter0.tsv"
    rules = read_rules(args.rules)
    write_rules(current_rules_path, rules)

    log = []

    for it in range(args.iterations):
        rules = read_rules(current_rules_path)
        batch_path = args.outdir / f"batch_iter{it}.tsv"
        candidates = make_batch(rules, read_chunks(args.chunks, args.candidate_limit), args.alphabet, batch_path)
        if not candidates:
            break

        eval_out = args.outdir / f"eval_iter{it}"
        summaries = run_cuda(args.cuda_bin, current_rules_path, args.lexicon, args.article, batch_path, eval_out)

        best = min(summaries, key=lambda r: int(r["total_cost"]))
        best_idx = int(best["mapping_index"])
        mapping_id, rule_id, key, desc = candidates[best_idx]

        # Apply best mutation.
        for r in rules:
            if r["rule_id"] == rule_id:
                old = r["code"]
                r["code"] = key
                break

        next_rules_path = args.outdir / f"rules_iter{it+1}.tsv"
        write_rules(next_rules_path, rules)

        row = {
            "iteration": it,
            "mapping_index": best_idx,
            "rule_id": rule_id,
            "new_code": key,
            "description": desc,
            **best,
        }
        log.append(row)
        current_rules_path = next_rules_path

        print(json.dumps(row, indent=2))

    if log:
        fields = list(log[0].keys())
        with (args.outdir / "optimizer_log.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(log)

    print(f"Final rules: {current_rules_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
