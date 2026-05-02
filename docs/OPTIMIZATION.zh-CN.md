# 优化

码表搜索问题是受约束的离散优化问题。

映射表可以由以下算子修改：

```text
change_code(rule, key)
add_rule(chunk, key, scope)
remove_rule(rule)
change_scope(rule, scope)
merge_group(group_a, group_b)
split_group(group)
```

局部变分为：

$$
J' = J + \delta J
$$

测得的改进为：

$$
\Delta F = F(J', x) - F(J, x)
$$

当前 mutation 工具主要探索 `change_code`。后续优化器应加入规则发现、scope 变化、group 操作、beam search 和 simulated annealing。
