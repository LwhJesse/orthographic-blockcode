# 输出字段

CUDA 评估器会打印并写入 summary 字段。

## 运行计数

```text
rules
```

后端加载的启用规则数，包括 literal fallback 规则。

```text
words
```

有效词典词数量。

```text
paths
```

所有词枚举出的切分路径总数。

```text
flat path rule ids
```

所有 path 展平为 rule-id 序列后的总长度。

```text
mappings
```

当前运行评估的候选 mapping 数量。

## 成本字段

```text
literal_base_cost
```

不能由词模型处理的片段成本。

```text
baseline_total
```

目标文章或语料的 literal baseline 成本。

```text
total_cost
```

被评估 mapping 下的理论输入成本。

### `saved`

baseline 和块码成本之差：

```text
saved = baseline_total - total_cost
```

### `reduction_ratio`

相对减少比例：

```text
reduction_ratio = (baseline_total - total_cost) / baseline_total
```

## 输出文件

CUDA sample 写入：

```text
out/cuda_sample/cuda_summary.csv
out/cuda_sample/cuda_summary.json
```

Mapping-batch 运行会在指定输出目录下写入同类文件。
