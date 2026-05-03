# 运行说明

本文档说明当前仓库在实际状态下应该如何运行。

先说结论：

- **Python 评估器**是当前参考实现。
- **CUDA 评估器**是原型批量后端。
- **`cpp/` 目录不是完整 CPU 评估器**，目前只有 skeleton。

如果你只是想确认仓库“能跑”，请先跑 Python 样例流程，不要先从 CUDA 开始。

## 1. 现在到底哪些东西能跑？

当前有三类可实际使用的入口：

1. Python 参考评估器：

   ```bash
   python -m blockcode.cli evaluate ...
   ```

2. Python 辅助流程：

   ```bash
   bash scripts/run_sample.sh
   bash scripts/run_dirty.sh
   python -m blockcode.cli mine ...
   python -m blockcode.cli optimize-greedy ...
   ```

3. CUDA 原型评估器：

   ```bash
   ninja
   ./bin/blockcode_cuda_eval ...
   ```

`python/optimize_cuda_greedy.py` 也是可运行脚本，但它是围绕 CUDA evaluator 的控制器，不是主参考实现。

仓库内置了两份 Python/CUDA 对齐辅助脚本：

- `scripts/compare_python_cuda_sample.sh`
- `scripts/compare_python_cuda_dirty.sh`

## 2. 仓库各目录分别负责什么

建议用下面这个心智模型理解仓库：

- `blockcode/`
  Python 参考实现。当前语义和行为应以这里为准。
- `tests/`
  Python 路径的 smoke tests。
- `scripts/`
  样例、脏文本和 CUDA 运行辅助脚本。
- `cpp_cuda/`
  CUDA batch evaluator 原型。
- `cpp/`
  CPU evaluator 占位骨架，不是完成版后端。
- `configs/`
  规则表和配置。
- `data/examples/`
  toy lexicon、sample article、dirty article、mapping batch 示例。

## 3. Python 运行前提

Python 路径本身不依赖额外第三方运行库，正常 Python 环境即可。

至少确认：

```bash
python --version
pytest --version
```

`pyproject.toml` 当前声明目标 Python 版本为 3.10+。

## 4. 最快的 smoke test

直接运行仓库内置的 Python 样例脚本：

```bash
bash scripts/run_sample.sh
```

这个脚本会做两件事：

1. 用 Python 参考评估器评估 sample article。
2. 从同一份 sample article 中挖掘候选 chunk。

预期输出目录：

```text
out/sample/
```

预期输出文件：

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

## 5. Python 参考评估器

### 5.1 最小可运行命令

```bash
python -m blockcode.cli evaluate \
  --rules configs/rules_v1.tsv \
  --settings configs/settings_default.json \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/sample_article.txt \
  --outdir out/sample_manual
```

### 5.2 它会写出什么

评估器会写出：

- `token_paths.csv`
  每个 token 的路径、编码、rank、delimiter 信息。
- `summary.json`
  文章级汇总指标。
- `report.md`
  由 summary 组装出的可读报告。
- `key_events.csv`
  符号化逐键事件日志。
- `keylog.txt`
  空格分隔的符号化击键序列。

### 5.3 关键 summary 字段是什么意思

常用字段：

- `baseline_total`
  当前 Python 成本模型下，目标文本按 baseline 输入时的理论成本。
- `total_cost`
  当前规则表和 delimiter-aware commit model 下的最优输入成本。
- `saved`
  `baseline_total - total_cost`
- `reduction_ratio`
  相对节省比例。
- `encoded_word_count`
  通过块码规则编码的单词数。
- `raw_word_count`
  被迫走 raw fallback 的单词数。

## 6. Dirty-text 流程

仓库特意带了一份更脏的样例，里面包含：

- 标点；
- URL 和 email；
- 混合语言；
- 代码式字符串；
- 数字；
- 未知词和拼写错误。

运行：

```bash
bash scripts/run_dirty.sh
```

这个流程很适合看清楚当前原型的边界。你应该预期：

- 大量词会落回 raw fallback；
- 部分标点会被 delimiter-aware 提交动作消费；
- 非 ASCII 和代码样文本大多按 literal/raw 处理。

## 7. Python 测试

运行：

```bash
pytest -q
```

当前测试范围很小：

- 只是 smoke test；
- 只是验证 sample evaluation 路径能跑并产出非空结果。

它不是正确性证明，也不是 Python/CUDA 对齐证明。

## 8. 候选 chunk 挖掘

chunk miner 会扫描语料中的词，并用一个简单启发式给重复子串打分：

```text
score = freq * (len(chunk) - 1)
```

运行：

```bash
python -m blockcode.cli mine \
  --corpus data/examples/sample_article.txt \
  --out out/mined_chunks.tsv \
  --top 100
```

输出是 TSV，列类似：

```text
chunk  length  freq  prefix_freq  suffix_freq  score  suggested_scope
```

这个输出是优化器输入，不是最终推荐码表。

## 9. Python 贪心优化器

Python 贪心优化器目前只是原型控制器。它会尝试逐步加入一条 `chunk -> key` 规则，并只保留带来改进的候选。

运行：

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

输出：

- `optimized_rules.tsv`
- `greedy_log.csv`

它是刻意保持简单、CPU-bound 的，目的是先验证搜索循环形状，再把批量 fitness evaluation 推给 CUDA。

## 10. CUDA 运行前提

CUDA 路径需要的不只是 `nvcc`。

必须同时满足：

1. NVIDIA 驱动正常工作。
2. 当前 shell / session 能看到 CUDA-capable GPU。
3. `nvcc` 在 `PATH` 中。
4. `nvidia-smi` 能正常和驱动通信。

检查：

```bash
nvcc --version
nvidia-smi
```

如果 `nvidia-smi` 失败，仓库仍然可能编译出 CUDA 二进制，但运行时在尝试申请设备内存时会失败。

## 11. 当前仓库里的 CUDA 构建方式

本仓库已经带有 `build.ninja` 和 `config.ninja`。

### 11.1 配置架构

如果自动检测可用：

```bash
bash scripts/configure_ninja.sh
```

如果你想手动指定：

```bash
bash scripts/configure_ninja.sh sm_86
```

常见示例：

```text
sm_75  RTX 20 系 / Turing
sm_86  RTX 30 系 / Ampere
sm_89  RTX 40 系 / Ada
sm_90  新一些的数据中心卡
```

### 11.2 编译

```bash
ninja
```

预期输出：

```text
bin/blockcode_cuda_eval
```

## 12. CUDA 运行命令

### 12.1 单一映射

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

### 12.3 使用仓库自带脚本

如果你更想直接跑包装脚本：

```bash
bash scripts/run_cuda_sample.sh
bash scripts/run_cuda_batch.sh
```

## 13. Python/CUDA 当前状态的重要说明

Python 和 CUDA 评估器现在已经在仓库内置的两条对齐检查上完成一致：

- `sample_article.txt`
- `dirty_article.txt`

这点非常重要。当前应当这样理解：

- Python 仍然是语义参考实现；
- CUDA 仍然是批量评估原型后端。

这已经比“未经验证的原型”强得多，但仍然不等于“对未来所有语料和所有边界 case 都已形式化证明一致”。任何严肃的优化结论、对外报告或论文级结论，仍然应该保留显式的 Python/CUDA 对齐检查。

仓库现在提供两份小的对齐脚本：

```bash
./scripts/compare_python_cuda_sample.sh
./scripts/compare_python_cuda_dirty.sh
```

## 14. 为什么 CUDA 可能“能编译但跑不动”

典型情况有几种：

### 14.1 `nvidia-smi` 失败

这通常意味着：

- 当前 session 里驱动栈不可用；或
- 当前环境拿不到宿主机 GPU。

### 14.2 `no CUDA-capable device is detected`

这意味着：

- 二进制编译成功了；
- 但运行时没有找到可用 GPU 设备。

这是运行环境失败，不一定是编译失败。

### 14.3 `nvcc` 在，但运行还是失败

这意味着：

- 编译工具链存在；
- 但运行时 GPU 访问仍然不通。

## 15. 最实用的排查顺序

如果你觉得仓库“不能跑”，建议按这个顺序排查：

1. `pytest -q` 能不能过？
2. `bash scripts/run_sample.sh` 能不能产出 `out/sample/summary.json`？
3. `bash scripts/run_dirty.sh` 能不能跑完？
4. `nvcc --version` 能不能用？
5. `nvidia-smi` 在同一个 shell 里能不能用？
6. `ninja` 能不能产出 `bin/blockcode_cuda_eval`？
7. CUDA 是编译失败，还是只在运行时报错？

这个顺序能很快把 Python/package 问题和 CUDA 环境问题分开。
