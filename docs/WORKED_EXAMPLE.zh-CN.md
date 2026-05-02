# 完整示例

本文档从规则、候选到输入事件和成本，完整走一遍 toy example。

## 1. 规则表

假设有以下规则：

```text
ee   -> u
ea   -> u
tion -> j
```

逐字母输入始终作为 fallback 路径存在。

## 2. 词典

假设词典包含：

```text
see      50000
sea      20000
section  10000
```

词频决定同码候选顺序。

## 3. 目标文本

```text
see sea section.
```

tokenizer 将其转为 word/delimiter 对：

```text
(see, space)
(sea, space)
(section, period)
```

## 4. 候选 code

对 `see`：

```text
s + ee -> su
s + e + e -> see
```

对 `sea`：

```text
s + ea -> su
s + e + a -> sea
```

对 `section`：

```text
s + e + c + tion -> secj
s + e + c + t + i + o + n -> section
```

关键候选表为：

```text
su -> [see, sea]
secj -> [section]
```

## 5. 输入事件

输入事件为：

```text
see + space      -> su<space>
sea + space      -> su;
section + period -> secj.
```

分号选择第二候选，并消费词边界。

## 6. 成本

简单 literal baseline 是：

```text
see sea section.
```

在 raw baseline 中，每个可见字符对应一个输入事件。

块码输入概念上是：

```text
su<space> su; secj.
```

评估器通过切分路径、候选 rank 和 delimiter commit cost 来计算该成本。具体成本取决于配置的成本模型，但关键点是：`sea` 的第二候选路径不需要额外空格键。

## 7. 为什么 delimiter 重要

如果评估器把 `sea` 和后面的空格分开算，就会多算：

```text
错误模型：sea + space -> su; + space
正确模型：sea + space -> su;
```

因此评估单位必须是 `(word, following_delimiter)`。
