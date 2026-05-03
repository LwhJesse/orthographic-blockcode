# Orthographic BlockCode：文本输入码表搜索框架

## 摘要

Orthographic BlockCode 是一个用于评估和搜索正字法块码文本输入映射的实验性框架。它把码表设计视为受约束的离散优化问题。给定映射规则集合和语料，评估器计算 delimiter-aware 文本输入模型下的理论击键成本。当前系统结合了语料驱动的正字法块切分、固定候选解码、symbolic keylog 生成和 C++/CUDA batch evaluator。

## 1. 动机

普通拉丁字母输入简单可靠，因为可见字母直接对应键盘按键。但许多语言存在高频重复的正字法结构。以英语为例：

```text
ee, ea, th, sh, ch, tion, sion, ing, ment, able, ough, ight
```

研究问题是：这些结构能否被编码进一个确定性的文本输入系统，从而在不依赖动态预测的情况下减少击键？

## 2. 正字法块码模型

码表由规则组成：

```text
(chunk, code, scope, enabled, group)
```

一个词可能有多条切分路径。每条路径生成一个 code。词典把 code 映射到按词频排序的固定候选列表。

## 3. 目标函数

评估器计算：

```math
F(J, x) = y
```

标量目标可以组合：

```math
L(J; X) = C_{\mathrm{key}}(J, X)
        + \lambda C_{\mathrm{collision}}(J)
        + \mu C_{\mathrm{complexity}}(J)
        + \nu C_{\mathrm{ergonomics}}(J)
```

## 4. 搜索循环

搜索循环是：

```math
J \rightarrow F(J, x) \rightarrow J'
```

这让码表设计变成可测量、可搜索的过程。

## 5. 结论

Orthographic BlockCode 是一个早期研究框架，用于评估和搜索结构化文本输入码表。当前原型说明该问题可以被形式化，并可以通过 CUDA batch backend 实现。
