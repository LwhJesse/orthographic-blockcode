# Orthographic BlockCode

**用于搜索正字法块码文本输入码表的研究原型。**

本项目研究一个具体问题：

> 在不依赖自动补全、AI 预测或和弦速记的情况下，拉丁字母文本输入能否通过可学习的结构码表减少击键？

Orthographic BlockCode 把文本输入码表视为一个可以**测量**、**比较**并最终**搜索**的对象。给定规则表 $J$ 和文章或语料 $x$，评估器计算理论输入成本：

$$
F(J, x) = y
$$

其中 $y$ 包含总输入成本、基准成本、节省击键数、压缩比例等评价值。

本仓库是研究原型，不是生产级输入法。

---

## 1. 它在解决什么问题？

普通拉丁字母输入通常逐个输入可见字符。这种方式可靠有效，但许多语言包含重复出现的正字法结构：

```text
ee, ea, th, sh, ch, tion, sion, ing, ment, able, ough, ight, con, pre, trans
```

本项目研究这些重复块能否被编码为更短的确定性输入序列。

重点不是手写一张聪明的缩写表，而是构建一个能够回答下列问题的框架：

- 给定这张规则表，输入该语料需要多少输入事件？
- 哪些块值得编码？
- 哪些规则会造成过多候选冲突？
- GPU batch evaluator 能否快速比较数千个候选 mapping？
- 在固定约束下，搜索算法能否找到弱最优码表？

---

## 2. 完整示例

`see/sea` 例子只展示同码候选和第二候选选择。同一模型也可以处理后缀块、前缀块、更长单词，以及前缀/后缀组合。

### 例子 1：长元音同码

```text
ee -> u
ea -> u

see = s + ee -> su
sea = s + ea -> su

su -> [see, sea]

see + 空格 -> su<space>
sea + 空格 -> su;
see,        -> su,
sea,        -> su;,
```

### 例子 2：后缀压缩

```text
tion -> j

section = s + e + c + tion -> secj
action  = a + c + tion     -> acj

section. -> secj.
action,  -> acj,
```

### 例子 3：`ing` 后缀

```text
ing -> z

typing  = t + y + p + ing     -> typz
running = r + u + n + n + ing -> runnz

typing  + 空格 -> typz<space>
running + 空格 -> runnz<space>
```

### 例子 4：前缀和后缀组合

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

这些例子不是最终推荐码表，而是用于说明评估器如何组合字面量字母、编码块、候选 rank 和 delimiter。

## 3. 当前包含的映射规则示例

当前规则表是实验性的，并且故意保持较小。它用于测试评估器，而不是定义最终输入法。

| 块 chunk | 码 code | 作用域 scope | 用途 |
|---|---:|---|---|
| `ee` | `u` | any | 长元音块 |
| `ea` | `u` | any | 与 `ee` 共码 |
| `tion` | `j` | suffix | 高频后缀 |
| `sion` | `j` | suffix | 后缀族 |
| `ing` | `z` | suffix | 高频后缀 |
| `th` | `q` | any | 辅音簇 |
| `sh` | `x` | any | 辅音簇 |
| `ch` | `x` | any | 辅音簇 |
| `con` | `c` | prefix | 前缀块 |
| `pre` | `p` | prefix | 前缀块 |

规则形式为：

```text
(chunk, code, scope, enabled, group)
```

其中 `scope` 控制 chunk 允许匹配的位置：

```text
any      词中任意位置
prefix   仅词首
suffix   仅词尾
whole    仅整词规则
```

## 4. 到底在计算什么？

baseline cost 是逐字符输入目标文本的成本。block-code cost 通过搜索每个词的合法切分，并在当前 mapping 下选择最低成本输入路径来计算。

对文章 $x$，CUDA 评估器概念上计算：

$$
C(J, x)
=
C_{\mathrm{literal}}(x)
+
\sum_{w,d}
n_x(w,d)\,c_J(w,d)
$$

其中：

- $w$ 是一个词；
- $d$ 是后继 delimiter 类别；
- $n_x(w,d)$ 是该 word/delimiter 对在文章或语料中的出现次数；
- $c_J(w,d)$ 是 mapping $J$ 下该对的最小输入成本；
- $C_{\mathrm{literal}}(x)$ 是不能由词模型处理的片段成本。

更大的优化目标可以写成：

$$
L(J; X)
=
C_{\mathrm{key}}(J, X)
+
\lambda C_{\mathrm{collision}}(J)
+
\mu C_{\mathrm{complexity}}(J)
+
\nu C_{\mathrm{ergonomics}}(J)
$$

当前原型主要实现击键成本部分。冲突、复杂度和人机工程项属于后续研究路线。

---

## 5. 为什么它不是自动补全、速记或普通压缩

| 相邻概念 | 区别 |
|---|---|
| Autocomplete | 根据上下文预测；本项目使用固定码表和固定候选顺序 |
| Text expansion | 扩展记忆缩写；本项目压缩词内部正字法块 |
| Stenography / Plover | 使用和弦输入；本项目使用普通顺序按键事件 |
| Keyboard layout optimization | 调整字符在物理键上的位置；本项目把正字法单位映射到输入码 |
| Huffman coding / compression | 优化符号码；本项目加入候选 rank、delimiter、fallback 和人类约束 |
| Production IME | 可用输入引擎；本仓库目前是评估器和搜索原型 |

---

## 6. 码表搜索作为离散优化问题

码表不是固定的手写产物，而是一个可以搜索的对象。

评估器计算：

$$
F(J, x) = y
$$

其中 $J$ 是规则表，$x$ 是文章或语料，$y$ 包含成本指标。

码表的局部修改可以写成：

$$
J' = J + \delta J
$$

其中 $\delta J$ 可以是：

```text
change_code(rule, key)
add_rule(chunk, key, scope)
remove_rule(rule)
change_scope(rule, scope)
merge_group(group_a, group_b)
split_group(group)
```

测得的效果是：

$$
\Delta F = F(J', x) - F(J, x)
$$

这形成一个离散搜索循环：

```text
当前规则表 J
  ↓
生成候选变分 J'
  ↓
评估 F(J', x)
  ↓
保留更好的 mapping
  ↓
重复
```

当前 CUDA 后端的目标就是批量评估大量候选 mapping。

## 7. 系统流水线

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

重要对象不是某一张人工选择的 mapping，而是这个循环：

$$
J \rightarrow F(J, x) \rightarrow J'
$$

这个循环让码表设计变得可测量、可搜索。

---

## 8. CPU/GPU 架构

CPU 侧处理语言不规则性和控制流：

- 脏文本解析；
- tokenization；
- 词典加载；
- 规则加载；
- 切分路径枚举；
- 语料/domain 权重；
- mapping batch 生成；
- 优化器控制。

GPU 侧处理重复批量评估：

- path-to-code 转换；
- 候选冲突和 rank 估计；
- word-plus-delimiter 成本计算；
- 多 mapping 的语料级 reduction。

当前 CUDA 后端以正确性优先，使用 brute-force candidate-rank 估计。可扩展设计应发射 code entries 并执行 sort/group/reduce。

---

## 9. 快速开始

### 8.1 平台支持状态

CUDA 后端面向 **NVIDIA CUDA 环境**。Python 侧工具可以在更多平台运行，但 C++/CUDA evaluator 需要 `nvcc` 和 NVIDIA GPU/驱动支持。

| 平台 | 状态 | 说明 |
|---|---|---|
| Debian / Ubuntu | 主要支持目标 | 推荐使用 NVIDIA 官方 CUDA Toolkit；系统包 `nvidia-cuda-toolkit` 可能版本较旧 |
| Fedora / RHEL / Rocky / Alma | 主要支持目标 | 推荐使用 NVIDIA 官方 CUDA repo 安装 CUDA Toolkit |
| Arch Linux | 已测试环境 | 可直接使用 `pacman` 安装 `cuda`、`ninja`、`python` |
| Windows via WSL2 | 预期可用 | 推荐路径；需要 Windows 侧 NVIDIA 驱动支持 WSL CUDA |
| Native Windows | 暂不支持 | 当前 Ninja/CUDA 构建脚本按 Linux-like shell 编写；建议用 WSL2 |
| macOS | 不支持 CUDA 后端 | Apple Silicon/AMD/Intel Mac 没有 NVIDIA CUDA；可运行部分 Python 工具，但不能运行 CUDA evaluator |

### 8.2 通用依赖

无论使用哪个 Linux 发行版，最终都需要这些命令可用：

```bash
python3 --version
ninja --version
nvcc --version
nvidia-smi
```

其中：

```text
python3      Python 工具和控制脚本
ninja        构建系统
nvcc         NVIDIA CUDA 编译器
nvidia-smi   检查 NVIDIA 驱动和 GPU
```

如果 `nvidia-smi` 不可用，说明驱动侧还没配置好。  
如果 `nvcc` 不可用，说明 CUDA Toolkit 没装好，或者 PATH 没配置好。

### 8.3 Debian / Ubuntu

安装基础工具：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ninja-build build-essential
```

CUDA Toolkit 建议使用 NVIDIA 官方安装方式，而不是盲目依赖发行版旧包。安装完成后检查：

```bash
nvcc --version
nvidia-smi
```

如果你的系统包源里有合适版本，也可以用发行版包，但版本可能偏旧：

```bash
sudo apt install -y nvidia-cuda-toolkit
```

然后构建：

```bash
scripts/configure_ninja.sh sm_89
ninja
```

如果不是 RTX 40 系，把 `sm_89` 换成你的架构，例如：

```text
RTX 20 series / Turing: sm_75
RTX 30 series / Ampere: sm_86
RTX 40 series / Ada:    sm_89
```

### 8.4 Fedora / RHEL / Rocky / Alma

安装基础工具：

```bash
sudo dnf install -y python3 python3-pip ninja-build gcc-c++ make
```

CUDA Toolkit 建议使用 NVIDIA 官方 CUDA repo。安装完成后检查：

```bash
nvcc --version
nvidia-smi
```

然后构建：

```bash
scripts/configure_ninja.sh sm_89
ninja
```

如果使用 RHEL 系衍生发行版，包名和 CUDA repo 配置可能随版本变化。本文档只要求最终 `nvcc`、`ninja`、`python3`、`nvidia-smi` 可用。

### 8.5 Arch Linux

Arch 是当前开发测试环境之一。安装：

```bash
sudo pacman -S --needed python python-pip ninja cuda
```

检查：

```bash
nvcc --version
ninja --version
nvidia-smi
```

构建：

```bash
scripts/configure_ninja.sh sm_89
ninja
```

### 8.6 Windows via WSL2

推荐 Windows 用户使用 WSL2，而不是 Native Windows。

步骤概念上是：

```text
1. 在 Windows 安装支持 WSL CUDA 的 NVIDIA 驱动；
2. 安装 WSL2，例如 Ubuntu；
3. 在 WSL2 里安装 Python、Ninja、build-essential；
4. 按 NVIDIA 官方 WSL CUDA 文档安装 CUDA Toolkit；
5. 在 WSL2 里确认 nvcc 和 nvidia-smi 可用；
6. 在 WSL2 里运行本项目的 Ninja 构建。
```

WSL2 Ubuntu 内的基础工具：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ninja-build build-essential
```

确认：

```bash
nvcc --version
nvidia-smi
```

构建：

```bash
scripts/configure_ninja.sh sm_89
ninja
```

### 8.7 Native Windows

当前不支持 Native Windows 直接构建。

原因：

```text
1. 当前 build.ninja 和脚本按 Linux-like shell 编写；
2. 路径、shell、CUDA 编译命令没有为 MSVC / PowerShell / cmd 做适配；
3. 项目现阶段优先保证 Linux / WSL2 CUDA 路径。
```

Windows 用户建议使用 WSL2。

### 8.8 macOS

macOS 不支持 CUDA 后端，因为现代 macOS 没有 NVIDIA CUDA 支持。

可以做的事情：

```text
1. 阅读文档；
2. 运行部分 Python 侧工具；
3. 修改规则表、词典、语料；
4. 不运行 C++/CUDA evaluator。
```

如果未来加入 CPU-only C++ evaluator 或 Metal backend，macOS 支持可以重新评估。

### 8.9 运行 sample

构建完成后运行：

```bash
scripts/run_cuda_sample.sh
```

输出会写入：

```text
out/cuda_sample/cuda_summary.csv
out/cuda_sample/cuda_summary.json
```

### 8.10 运行 mapping batch

```bash
scripts/run_cuda_batch.sh
```

### 8.11 生成并评估规则换键 mutations

```bash
python tools/generate_rule_code_batch.py \
  --rules configs/rules_v1.tsv \
  --out out/mutations.tsv \
  --limit-rules 30

bin/blockcode_cuda_eval \
  --rules configs/rules_v1.tsv \
  --lexicon data/examples/mini_lexicon.tsv \
  --article data/examples/sample_article.txt \
  --mappings out/mutations.tsv \
  --out out/cuda_mutations

sort -t, -k2,2n out/cuda_mutations/cuda_summary.csv | head -20
```

## 10. 输入文件

### 规则表

规则是 TSV 行：

```text
rule_id  chunk  code  scope  class  enabled  group  note
```

### 词典

词典格式：

```text
word<TAB>frequency
```

词频决定同码候选顺序。

### Mapping batch

Mapping batch 覆盖部分规则的 code：

```text
mapping_id  rule_id       code
m0          long_e        i
m1          tion_family   x
```

每个 `mapping_id` 代表一个候选 mapping。

---

## 11. 当前范围

已经实现：

- Python 参考评估器；
- delimiter-aware 击键模型；
- symbolic keylog 输出；
- C++/CUDA 原型评估器；
- 直接 Ninja 构建；
- TSV 规则表；
- toy 词典和 toy 语料；
- mapping-batch 评估；
- 初期 mutation-search 工具。

尚未包含：

- 生产级输入法引擎；
- 大规模公开 benchmark 语料；
- 覆盖 add/remove/split/merge 操作的完整优化器；
- 高性能 sort/reduce CUDA ranking；
- 用户实验；
- 已验证的人类友好码表。

---

## 12. 文档

## Documentation

### English

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
## License

本项目使用 Apache License 2.0 开源。

SPDX 标识符：

```text
Apache-2.0
```

详见 [`LICENSE`](LICENSE)。
