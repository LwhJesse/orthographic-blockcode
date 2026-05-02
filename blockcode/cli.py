from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .config import load_rules_tsv, load_settings, write_rules_tsv
from .evaluator import Evaluator, write_csv, write_json
from .lexicon import load_lexicon
from .miner import mine_chunks_from_text, write_chunks
from .optimizer import greedy_add_rules, load_candidate_chunks



def _sequence_to_keys(seq: str) -> list[str]:
    """Parse symbolic input_sequence into key labels.

    Special symbols:
      ␠  -> SPACE
      ⎋  -> RAW
      ⇧x -> SHIFT+x
      \n -> ENTER
    Normal ASCII chars are one key each.

    This is a symbolic physical-key log. It is not yet a real OS key-event trace.
    """
    keys: list[str] = []
    i = 0
    while i < len(seq):
        ch = seq[i]
        if ch == "␠":
            keys.append("SPACE")
            i += 1
        elif ch == "⎋":
            keys.append("RAW")
            i += 1
        elif ch == "⇧":
            if i + 1 < len(seq):
                keys.append("SHIFT+" + seq[i + 1])
                i += 2
            else:
                keys.append("SHIFT")
                i += 1
        elif ch == "\\" and i + 1 < len(seq) and seq[i + 1] == "n":
            keys.append("ENTER")
            i += 2
        else:
            keys.append(ch)
            i += 1
    return keys


def write_keylogs(outdir, rows):
    import csv
    from pathlib import Path
    outdir = Path(outdir)
    events = []
    keylog = []
    key_index = 0
    for row in rows:
        seq = row.get("input_sequence", "")
        if not seq:
            continue
        keys = _sequence_to_keys(seq)
        for local_i, key in enumerate(keys):
            events.append({
                "key_index": key_index,
                "token_index": row.get("index", ""),
                "token": row.get("token", ""),
                "token_type": row.get("type", ""),
                "mode": row.get("mode", ""),
                "input_sequence": seq,
                "local_key_index": local_i,
                "key": key,
                "code": row.get("code", ""),
                "rank": row.get("rank", ""),
                "delimiter_kind": row.get("delimiter_kind", ""),
                "delimiter_literal": row.get("delimiter_literal", ""),
                "consumed_next_chars": row.get("consumed_next_chars", ""),
            })
            keylog.append(key)
            key_index += 1
    with (outdir / "key_events.csv").open("w", encoding="utf-8", newline="") as f:
        if events:
            writer = csv.DictWriter(f, fieldnames=list(events[0].keys()))
            writer.writeheader()
            writer.writerows(events)
        else:
            f.write("")
    (outdir / "keylog.txt").write_text(" ".join(keylog) + "\n", encoding="utf-8")


def cmd_evaluate(args: argparse.Namespace) -> int:
    settings = load_settings(args.settings)
    rules = load_rules_tsv(args.rules)
    text = Path(args.article).read_text(encoding="utf-8", errors="replace")
    lexicon = load_lexicon(args.lexicon, fallback_text=text)
    ev = Evaluator(rules, settings, lexicon)
    rows, summary = ev.evaluate_text(text)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    write_csv(outdir / "token_paths.csv", rows)
    write_json(outdir / "summary.json", summary)
    write_keylogs(outdir, rows)

    lex_summary = None
    if args.analyze_lexicon:
        word_rows, lex_summary, collision_rows = ev.analyze_lexicon()
        write_csv(outdir / "lexicon_words.csv", word_rows)
        write_csv(outdir / "collisions.csv", collision_rows)
        write_json(outdir / "lexicon_summary.json", lex_summary)

    report = ["# BlockCode Evaluation Report", "", "## Article summary", ""]
    for k, v in summary.items():
        if isinstance(v, float):
            report.append(f"- {k}: {v:.6f}")
        else:
            report.append(f"- {k}: {v}")
    if lex_summary:
        report += ["", "## Lexicon summary", ""]
        for k, v in lex_summary.items():
            if isinstance(v, float):
                report.append(f"- {k}: {v:.6f}")
            else:
                report.append(f"- {k}: {v}")
    (outdir / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Wrote outputs to {outdir}")
    return 0


def cmd_mine(args: argparse.Namespace) -> int:
    text = Path(args.corpus).read_text(encoding="utf-8", errors="replace")
    rows = mine_chunks_from_text(text, min_len=args.min_len, max_len=args.max_len, top=args.top)
    write_chunks(args.out, rows)
    print(f"Wrote {len(rows)} mined chunks to {args.out}")
    return 0


def cmd_optimize_greedy(args: argparse.Namespace) -> int:
    settings = load_settings(args.settings)
    base_rules = load_rules_tsv(args.rules)
    text = Path(args.article).read_text(encoding="utf-8", errors="replace")
    lexicon = load_lexicon(args.lexicon, fallback_text=text)
    candidates = load_candidate_chunks(args.candidates, limit=args.candidate_limit)

    rules, log = greedy_add_rules(
        base_rules=base_rules,
        settings=settings,
        lexicon=lexicon,
        article_text=text,
        candidates=candidates,
        alphabet=args.alphabet,
        iterations=args.iterations,
        collision_weight=args.collision_weight,
    )

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    write_rules_tsv(outdir / "optimized_rules.tsv", rules)

    if log:
        with (outdir / "greedy_log.csv").open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=sorted({k for row in log for k in row.keys()}))
            writer.writeheader()
            writer.writerows(log)
    print(f"Wrote optimized rules to {outdir / 'optimized_rules.tsv'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="blockcode", description="Orthographic BlockCode research toolkit.")
    sub = p.add_subparsers(dest="cmd", required=True)

    ev = sub.add_parser("evaluate", help="Evaluate a ruleset on an article.")
    ev.add_argument("--rules", required=True, help="Rules TSV.")
    ev.add_argument("--settings", required=True, help="Settings JSON.")
    ev.add_argument("--lexicon", default=None, help="Lexicon TSV/CSV/space: word freq. If omitted, article vocabulary is used.")
    ev.add_argument("--article", required=True, help="Target article text.")
    ev.add_argument("--outdir", required=True, help="Output directory.")
    ev.add_argument("--analyze-lexicon", action="store_true")
    ev.set_defaults(func=cmd_evaluate)

    mine = sub.add_parser("mine", help="Mine candidate chunks from corpus.")
    mine.add_argument("--corpus", required=True)
    mine.add_argument("--out", required=True)
    mine.add_argument("--min-len", type=int, default=2)
    mine.add_argument("--max-len", type=int, default=8)
    mine.add_argument("--top", type=int, default=500)
    mine.set_defaults(func=cmd_mine)

    opt = sub.add_parser("optimize-greedy", help="Prototype greedy rule search.")
    opt.add_argument("--rules", required=True)
    opt.add_argument("--settings", required=True)
    opt.add_argument("--lexicon", default=None)
    opt.add_argument("--article", required=True)
    opt.add_argument("--candidates", required=True)
    opt.add_argument("--outdir", required=True)
    opt.add_argument("--iterations", type=int, default=5)
    opt.add_argument("--candidate-limit", type=int, default=50)
    opt.add_argument("--alphabet", default="abcdefghijklmnopqrstuvwxyz")
    opt.add_argument("--collision-weight", type=float, default=0.0)
    opt.set_defaults(func=cmd_optimize_greedy)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
