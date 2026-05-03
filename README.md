# Orthographic BlockCode

**A research prototype for searching orthographic block-code text-entry tables.**

This project asks a specific question:

> Can Latin-script text entry be shortened by a learnable structural code table, without relying on autocomplete, AI prediction, or chorded stenography?

Orthographic BlockCode treats a text-entry code table as an object that can be **measured**, **compared**, and eventually **searched**. Given a rule table `J` and an article or corpus `x`, the evaluator computes the theoretical input cost:

```text
F(J, x) = y
```

where `y` contains values such as total keystroke cost, baseline cost, saved keystrokes, and reduction ratio.

This repository is a research prototype. It is not a production input method.

---

## 1. What problem is this solving?

Ordinary Latin-script typing enters one visible character at a time. That works well, but many languages contain repeated orthographic structures:

```text
ee, ea, th, sh, ch, tion, sion, ing, ment, able, ough, ight, con, pre, trans
```

This project studies whether recurring blocks like these can be encoded into shorter deterministic input sequences.

The point is not to hand-write one clever abbreviation list. The point is to build a framework that can answer questions like:

- Given this rule table, how many input events are needed to type this corpus?
- Which chunks are worth encoding?
- Which rules cause too many candidate collisions?
- Can a GPU batch evaluator compare thousands of candidate mappings quickly?
- Under fixed constraints, can a search algorithm find a weakly optimal code table?

---

## 2. Worked examples

The `see/sea` example only shows candidate collision and second-candidate selection. The same model also handles suffix blocks, prefix blocks, longer words, and prefix/suffix composition.

### Example 1: long-vowel collision

```text
ee -> u
ea -> u

see = s + ee -> su
sea = s + ea -> su

su -> [see, sea]

see + space -> su<space>
sea + space -> su;
see,        -> su,
sea,        -> su;,
```

### Example 2: suffix compression

```text
tion -> j

section = s + e + c + tion -> secj
action  = a + c + tion     -> acj

section. -> secj.
action,  -> acj,
```

### Example 3: `ing` suffix

```text
ing -> z

typing  = t + y + p + ing     -> typz
running = r + u + n + n + ing -> runnz

typing  + space -> typz<space>
running + space -> runnz<space>
```

### Example 4: prefix and suffix composition

```text
con  -> c    prefix
tion -> j    suffix

contribution
= con + t + r + i + b + u + tion
-> ctribuj

configuration
= con + f + i + g + u + r + a + tion
-> cfiguraj
```

These examples are not final recommended codes. They are small examples showing how the evaluator combines literal letters, encoded chunks, candidate ranks, and delimiters.

---

## 3. Example rules currently included

The current rule table is experimental and intentionally small. It exists to exercise the evaluator, not to define a final input method.

| chunk | code | scope | purpose |
|---|---:|---|---|
| `ee` | `u` | any | long-vowel block |
| `ea` | `u` | any | shares code with `ee` |
| `tion` | `j` | suffix | common suffix |
| `sion` | `j` | suffix | suffix family |
| `ing` | `z` | suffix | common suffix |
| `th` | `q` | any | consonant cluster |
| `sh` | `x` | any | consonant cluster |
| `ch` | `x` | any | consonant cluster |
| `con` | `c` | prefix | prefix block |
| `pre` | `p` | prefix | prefix block |

Rules have the form:

```text
(chunk, code, scope, enabled, group)
```

where `scope` controls where the chunk is allowed to match:

```text
any      anywhere inside the word
prefix   only at the beginning
suffix   only at the end
whole    only as a whole-word rule
```

---

## 4. What exactly is computed?

The baseline cost is the cost of typing the target text literally. The block-code cost is computed by searching legal segmentations of each word and selecting the lowest-cost input path under the current mapping.

For an article or corpus `x`, the CUDA evaluator conceptually computes:

```text
C(J, x) = C_literal(x) + sum_{w,d} n_x(w, d) * c_J(w, d)
```

where:

- `w` is a word;
- `d` is the following delimiter class;
- `n_x(w, d)` is the number of times the word/delimiter pair occurs in the article or corpus;
- `c_J(w, d)` is the minimum input cost for that pair under mapping `J`;
- `C_literal(x)` is the cost of spans that are not handled by the word model.

A larger optimization objective can be written as:

```text
L(J; X) = C_key(J, X)
        + lambda * C_collision(J)
        + mu * C_complexity(J)
        + nu * C_ergonomics(J)
```

The current prototype mainly implements the keystroke-cost part. Collision, complexity, and ergonomics terms are part of the research roadmap.

---

## 5. Why this is not autocomplete, stenography, or compression

| Related idea | Difference |
|---|---|
| Autocomplete | Predicts from context; this project uses fixed code tables and fixed candidate order. |
| Text expansion | Expands memorized abbreviations; this project compresses internal orthographic blocks. |
| Stenography / Plover | Uses chorded input; this project uses ordinary sequential key events. |
| Keyboard layout optimization | Moves characters across physical keys; this project maps orthographic units to input codes. |
| Huffman coding / compression | Optimizes symbol codes; this project adds candidate ranks, delimiters, fallback, and human constraints. |
| Production IME | A usable input engine; this repository is currently an evaluator and search prototype. |

---

## 6. Code-table search as discrete optimization

A mapping table is not treated as a fixed hand-written artifact. It is treated as a search object.

The evaluator computes:

```text
F(J, x) = y
```

where `J` is a rule table, `x` is an article or corpus, and `y` contains cost metrics.

A local modification of the code table can be written as:

```text
J' = J + delta_J
```

where `delta_J` may be one of:

```text
change_code(rule, key)
add_rule(chunk, key, scope)
remove_rule(rule)
change_scope(rule, scope)
merge_group(group_a, group_b)
split_group(group)
```

The measured effect is:

```text
Delta_F = F(J', x) - F(J, x)
```

This gives a discrete search loop:

```text
current rule table J
  ↓
generate candidate variations J'
  ↓
evaluate F(J', x)
  ↓
keep better mappings
  ↓
repeat
```

The current CUDA backend is designed to evaluate many candidate mappings in a batch.

---

## 7. System pipeline

```text
corpus / article
  ↓
tokenizer + delimiter analyzer
  ↓
(word, following_delimiter) counts
  ↓
lexicon + frequency table
  ↓
word segmentation paths
  ↓
rule table J
  ↓
candidate code table
  ↓
F(J, x): theoretical input cost
  ↓
optimizer proposes J'
  ↓
CUDA batch evaluator compares many J'
```

The important object is not one manually chosen mapping. The important object is the loop:

```text
J -> F(J, x) -> J'
```

This loop makes code-table design measurable and searchable.

---

## 8. CPU/GPU architecture

The CPU side handles irregular language and control flow:

- dirty text parsing;
- tokenization;
- lexicon loading;
- rule loading;
- segmentation path enumeration;
- corpus/domain weighting;
- mapping-batch generation;
- optimizer control.

The GPU side handles repeated batch evaluation:

- path-to-code conversion;
- candidate collision and rank estimation;
- word-plus-delimiter cost computation;
- corpus-level reduction across mappings.

The current CUDA backend is correctness-first and uses brute-force candidate-rank estimation. The scalable design should emit code entries and perform sort/group/reduce.

---

## 9. Quickstart

This repository has **two different run paths**:

- the **Python reference evaluator**, which is the current semantic reference;
- the **CUDA batch evaluator**, which is the current compiled prototype backend.

If you want the fastest end-to-end confirmation that the repository works, run the Python sample workflow first:

```bash
bash scripts/run_sample.sh
pytest -q
```

For the full runnable matrix, outputs, and troubleshooting, read:

- [Detailed running guide](docs/RUNNING.md)
- [Ninja CUDA quickstart](QUICKSTART_NINJA.md)
- [Chinese Ninja CUDA quickstart](QUICKSTART_NINJA.zh-CN.md)
- [中文运行说明](docs/RUNNING.zh-CN.md)

### 9.1 Platform status

The CUDA backend targets **NVIDIA CUDA environments**. Python-side tools can run on more platforms, but the C++/CUDA evaluator requires `nvcc` and an NVIDIA GPU/driver stack.

| Platform | Status | Notes |
|---|---|---|
| Debian / Ubuntu | primary target | NVIDIA's official CUDA Toolkit is recommended; distro package `nvidia-cuda-toolkit` may be old. |
| Fedora / RHEL / Rocky / Alma | primary target | NVIDIA's official CUDA repo is recommended. |
| Arch Linux | tested development environment | `cuda`, `ninja`, and `python` are available through `pacman`. |
| Windows via WSL2 | expected path | Requires an NVIDIA Windows driver with WSL CUDA support. |
| Native Windows | not currently supported | Current Ninja/CUDA scripts assume a Linux-like shell; use WSL2. |
| macOS | CUDA backend unsupported | Python-side tools may still be useful, but CUDA evaluation requires NVIDIA CUDA. |

### 9.2 Common requirements

On any Linux distribution, the following commands should be available:

```bash
python3 --version
ninja --version
nvcc --version
nvidia-smi
```

Meaning:

```text
python3      Python utilities and controller scripts
ninja        build system
nvcc         NVIDIA CUDA compiler
nvidia-smi   NVIDIA driver/GPU visibility check
```

If `nvidia-smi` is unavailable, the NVIDIA driver stack is not ready. If `nvcc` is unavailable, the CUDA Toolkit is missing or not in `PATH`.

### 9.3 Debian / Ubuntu

Install basic tools:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ninja-build build-essential
```

For CUDA Toolkit, NVIDIA's official installation method is recommended. After installation, verify:

```bash
nvcc --version
nvidia-smi
```

If your distro repository provides a suitable version, you may also use the distro package, but it may be older:

```bash
sudo apt install -y nvidia-cuda-toolkit
```

Then build:

```bash
bash scripts/configure_ninja.sh sm_89
ninja
```

If you are not using an RTX 40-series GPU, replace `sm_89` with your architecture:

```text
RTX 20 series / Turing: sm_75
RTX 30 series / Ampere: sm_86
RTX 40 series / Ada:    sm_89
```

### 9.4 Fedora / RHEL / Rocky / Alma

Install basic tools:

```bash
sudo dnf install -y python3 python3-pip ninja-build gcc-c++ make
```

For CUDA Toolkit, NVIDIA's official CUDA repo is recommended. After installation, verify:

```bash
nvcc --version
nvidia-smi
```

Then build:

```bash
bash scripts/configure_ninja.sh sm_89
ninja
```

Package names and CUDA repo setup may vary across RHEL-family versions. This repository only assumes that `nvcc`, `ninja`, `python3`, and `nvidia-smi` are available.

### 9.5 Arch Linux

Arch is one of the tested development environments.

```bash
sudo pacman -S --needed python python-pip ninja cuda
```

Verify:

```bash
nvcc --version
ninja --version
nvidia-smi
```

Build:

```bash
bash scripts/configure_ninja.sh sm_89
ninja
```

### 9.6 Windows via WSL2

WSL2 is the recommended Windows path.

Conceptual steps:

```text
1. Install an NVIDIA Windows driver with WSL CUDA support.
2. Install WSL2, for example Ubuntu.
3. Install Python, Ninja, and build-essential inside WSL2.
4. Install CUDA Toolkit inside WSL2 using NVIDIA's WSL CUDA instructions.
5. Verify nvcc and nvidia-smi inside WSL2.
6. Build this project inside WSL2.
```

Inside WSL2 Ubuntu:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ninja-build build-essential
```

Verify:

```bash
nvcc --version
nvidia-smi
```

Build:

```bash
bash scripts/configure_ninja.sh sm_89
ninja
```

### 9.7 Native Windows

Native Windows builds are not currently supported.

Reasons:

```text
1. The current build.ninja and helper scripts assume a Linux-like shell.
2. Paths, shell commands, and CUDA invocation have not been adapted for MSVC / PowerShell / cmd.
3. The current priority is Linux / WSL2 CUDA support.
```

Windows users should use WSL2.

### 9.8 macOS

The CUDA backend is not supported on macOS because modern macOS does not support NVIDIA CUDA.

What may still work:

```text
1. Reading documentation.
2. Running some Python-side tools.
3. Editing rule tables, lexicons, and corpora.
4. Not running the C++/CUDA evaluator.
```

If a CPU-only C++ evaluator or Metal backend is added later, macOS support can be revisited.

### 9.9 Run the CUDA sample

After building:

```bash
bash scripts/run_cuda_sample.sh
```

Outputs:

```text
out/cuda_sample/cuda_summary.csv
out/cuda_sample/cuda_summary.json
```

### 9.10 Run a mapping batch

```bash
bash scripts/run_cuda_batch.sh
```

### 9.11 Generate and evaluate rule-code mutations

```bash
python tools/generate_rule_code_batch.py \
  --rules configs/rules_v1.tsv \
  --out out/mutations.tsv \
  --limit-rules 30

./bin/blockcode_cuda_eval \
  --rules configs/rules_v1.tsv \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/sample_article.txt \
  --mappings out/mutations.tsv \
  --out out/cuda_mutations

sort -t, -k2,2n out/cuda_mutations/cuda_summary.csv | head -20
```

---

## 10. Input files

### Rule table

Rules are TSV rows:

```text
rule_id  chunk  code  scope  class  enabled  group  note
```

### Lexicon

Lexicon format:

```text
word<TAB>frequency
```

Frequency determines candidate order for equal codes.

### Mapping batch

A mapping batch overrides selected rule codes:

```text
mapping_id  rule_id       code
m0          long_e        i
m1          tion_family   x
```

Each `mapping_id` represents one candidate mapping.

---

## 11. Current scope

Implemented:

- Python reference evaluator;
- delimiter-aware keystroke model;
- symbolic keylog output;
- C++/CUDA prototype evaluator;
- direct Ninja build;
- TSV rule table;
- toy lexicon and toy corpora;
- mapping-batch evaluation;
- early mutation-search utility.

Not included yet:

- production input-method engine;
- large public benchmark corpus;
- complete optimizer over add/remove/split/merge operations;
- high-performance sort/reduce CUDA ranking;
- user study;
- validated human-friendly code table.

---

## 12. Documentation

### English

- [Detailed running guide](docs/RUNNING.md)
- [Ninja CUDA quickstart](QUICKSTART_NINJA.md)
- [Python/CUDA sample compare script](scripts/compare_python_cuda_sample.sh)
- [Python/CUDA dirty-text compare script](scripts/compare_python_cuda_dirty.sh)
- [Whitepaper](docs/WHITEPAPER.md)
- [Worked example](docs/WORKED_EXAMPLE.md)
- [Output fields](docs/OUTPUTS.md)
- [Model notes](docs/MODEL.md)
- [CUDA backend](docs/CUDA_BACKEND.md)
- [Benchmarks](docs/BENCHMARKS.md)
- [Optimization](docs/OPTIMIZATION.md)
- [Related work](docs/RELATED_WORK.md)
- [Roadmap](docs/ROADMAP.md)
- [Known limitations](docs/KNOWN_LIMITATIONS.md)

### Chinese

- [中文 README](README.zh-CN.md)
- [运行说明](docs/RUNNING.zh-CN.md)
- [中文 CUDA quickstart](QUICKSTART_NINJA.zh-CN.md)
- [白皮书](docs/WHITEPAPER.zh-CN.md)
- [完整示例](docs/WORKED_EXAMPLE.zh-CN.md)
- [输出字段](docs/OUTPUTS.zh-CN.md)
- [模型说明](docs/MODEL.zh-CN.md)
- [CUDA 后端](docs/CUDA_BACKEND.zh-CN.md)
- [Benchmark](docs/BENCHMARKS.zh-CN.md)
- [优化](docs/OPTIMIZATION.zh-CN.md)
- [相关方向](docs/RELATED_WORK.zh-CN.md)
- [路线图](docs/ROADMAP.zh-CN.md)
- [当前限制](docs/KNOWN_LIMITATIONS.zh-CN.md)

---

## License

This project is licensed under the Apache License 2.0.

SPDX identifier:

```text
Apache-2.0
```

See [LICENSE](LICENSE).
