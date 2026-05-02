# 模型说明

核心评估单位是 `(word, following_delimiter)` 对。

例如：

```text
ee / ea -> u
su -> [see, sea]

see + 空格 -> su<space>
sea + 空格 -> su;
see + 逗号 -> su,
sea + 逗号 -> su;,
```

一条映射规则形式为：

```text
(chunk, code, scope, enabled, group)
```

评估器会枚举一个词的合法切分路径，把每条路径转换成 code，确定候选 rank，并根据后继 delimiter 计算提交成本。

评估函数是：

$$
F(J, x) = y
$$

语料级成本可以表示为：

$$
C(J, x)
=
C_{\mathrm{literal}}(x)
+
\sum_{w,d}
n_x(w,d)c_J(w,d)
$$

当前候选策略为：

```text
rank 1: 由空格/标点提交
rank 2: 由 ; 选择
rank 3: 由 ' 选择
```
