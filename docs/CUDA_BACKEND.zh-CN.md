# CUDA 后端

CUDA 后端是一个原型 batch evaluator。它在相同词典和语料表示下评估大量候选 mapping。

## CPU 侧

CPU 准备整数化数据结构：

- 规则表；
- 词典；
- 切分路径；
- 文章 word/delimiter 计数；
- mapping batch。

## GPU 侧

GPU 为大量 mapping 计算成本：

- 将 path 转换成 code；
- 估计候选 rank；
- 计算 word-plus-delimiter 成本；
- 为每个 mapping 做语料级 cost reduction。

当前后端使用 brute-force candidate-rank 估计。可扩展设计应发射 code entries，然后执行 sort/group/reduce。

语料级成本概念上为：

$$
C(J, x)
=
C_{\mathrm{literal}}(x)
+
\sum_{w,d}
n_x(w,d)c_J(w,d)
$$
