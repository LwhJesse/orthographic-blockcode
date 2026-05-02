# 路线图

## 短期

- 稳定原型。
- 对齐 Python 和 CUDA 评估器输出。
- 加入 word-level debug。
- 加入更大的公开词典。
- 加入基础语料权重。

## 中期

- 实现 `add_rule`、`remove_rule` 和 `change_scope`。
- 加入 beam search 或 simulated annealing。
- 报告 rank、collision 和 fallback 指标。
- 在固定约束下生成第一版弱解。

## 长期

- 用 sort/group/reduce 替换 brute-force CUDA ranking。
- 生成 theoretical、balanced 和 human-friendly 码表。
- 构建 typing trainer。
- 进行小规模用户实验。
- 测试向其他拉丁字母语言迁移。
