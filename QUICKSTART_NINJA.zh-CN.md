# 快速开始：Ninja CUDA 构建

本 quickstart 面向**当前仓库目录结构**。

它**不**假设你先解压某个 zip 包。所有命令都应在仓库根目录下执行。

如果你需要完整运行矩阵、Python 参考流程或故障排查，请看：

- [运行说明](docs/RUNNING.zh-CN.md)
- [Detailed running guide](docs/RUNNING.md)

## 1. 这个 quickstart 是干什么的

只在以下场景使用本文档：

1. 为当前仓库配置 CUDA 架构；
2. 使用 Ninja 编译 CUDA evaluator；
3. 运行仓库内置的 CUDA sample 或 mapping batch 示例。

如果你只是想先确认项目能跑，建议先走 Python 参考路径：

```bash
bash scripts/run_sample.sh
```

## 2. 前置条件

你需要：

- `nvcc`
- `ninja`
- 正常工作的 NVIDIA 驱动
- 当前 shell 可见的 CUDA-capable GPU

检查：

```bash
nvcc --version
ninja --version
nvidia-smi
```

如果 `nvidia-smi` 失败，CUDA 二进制仍然可能编译成功，但大概率会在运行时失败。

## 3. 配置架构

自动检测：

```bash
bash scripts/configure_ninja.sh
```

手动指定：

```bash
bash scripts/configure_ninja.sh sm_86
```

常见示例：

```text
sm_75  RTX 20 系 / Turing
sm_86  RTX 30 系 / Ampere
sm_89  RTX 40 系 / Ada
sm_90  新一些的数据中心 GPU
```

这一步会写出：

```text
config.ninja
```

## 4. 编译

```bash
ninja
```

预期输出：

```text
bin/blockcode_cuda_eval
```

## 5. 运行 CUDA sample

直接命令：

```bash
./bin/blockcode_cuda_eval \
  --rules configs/rules_v1.tsv \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/sample_article.txt \
  --out out/cuda_sample
```

包装脚本：

```bash
bash scripts/run_cuda_sample.sh
```

预期输出：

```text
out/cuda_sample/cuda_summary.csv
out/cuda_sample/cuda_summary.json
```

## 6. 运行 mapping batch 示例

直接命令：

```bash
./bin/blockcode_cuda_eval \
  --rules configs/rules_v1.tsv \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/sample_article.txt \
  --mappings data/examples/mappings_example.tsv \
  --out out/cuda_batch
```

包装脚本：

```bash
bash scripts/run_cuda_batch.sh
```

预期输出：

```text
out/cuda_batch/cuda_summary.csv
out/cuda_batch/cuda_summary.json
```

## 7. 生成并评估规则换键 mutations

先生成 mapping batch：

```bash
python tools/generate_rule_code_batch.py \
  --rules configs/rules_v1.tsv \
  --out out/mutations.tsv \
  --limit-rules 30
```

再评估：

```bash
./bin/blockcode_cuda_eval \
  --rules configs/rules_v1.tsv \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/sample_article.txt \
  --mappings out/mutations.tsv \
  --out out/cuda_mutations
```

查看最优若干行：

```bash
sort -t, -k2,2n out/cuda_mutations/cuda_summary.csv | head -20
```

## 8. 当前一个重要限制

CUDA evaluator 目前仍是原型后端，但它现在已经在仓库内置的 `sample` 和 `dirty` 对齐检查上与 Python 参考实现一致。

当前应理解为：

- 可以编译；
- 可以用于原型级批量评估；
- 已通过仓库内置的对齐流程验证；
- 当你引入新的语料或新的边界 case 时，仍应重新做对齐检查。
