# Optimization

The code-table search problem is a constrained discrete optimization problem.

A mapping table is modified by operators such as:

```text
change_code(rule, key)
add_rule(chunk, key, scope)
remove_rule(rule)
change_scope(rule, scope)
merge_group(group_a, group_b)
split_group(group)
```

A local variation is:

```text
J' = J + delta_J
```

and the measured improvement is:

```text
Delta_F = F(J', x) - F(J, x)
```

The current mutation utility mainly explores `change_code`. Future optimizers should add rule discovery, scope changes, group operations, beam search, and simulated annealing.
