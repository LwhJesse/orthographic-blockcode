# Benchmark

本仓库当前包含 toy examples，用于 smoke test。这些示例用于验证评估器、CUDA 后端和 mapping-batch 路径是否工作。

完整 benchmark 应包含：

- 公开词典；
- 多领域语料；
- train/validation/test 划分；
- domain weights；
- raw baseline；
- block-code 结果；
- collision 和 fallback 统计。

加权 benchmark 目标可以写成：

$$
C_{\mathrm{weighted}}(J)
=
\sum_{k=1}^{K}
\alpha_k C(J, X_k)
$$

私人聊天、受版权保护文章、付费出版物和原始社交媒体 dump 不应提交到仓库。应使用公开/开放语料，或使用本地聚合统计。
