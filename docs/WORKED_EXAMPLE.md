# Worked Example

This document walks through a complete toy example from rules to input events and cost.

## 1. Rule table

Assume the following rules:

```text
ee   -> u
ea   -> u
tion -> j
```

Literal letters are always available as fallback paths.

## 2. Lexicon

Assume the lexicon contains:

```text
see      50000
sea      20000
section  10000
```

The frequency values define candidate order for equal codes.

## 3. Target text

```text
see sea section.
```

The tokenizer turns this into word/delimiter pairs:

```text
(see, space)
(sea, space)
(section, period)
```

## 4. Candidate codes

For `see`:

```text
s + ee -> su
s + e + e -> see
```

For `sea`:

```text
s + ea -> su
s + e + a -> sea
```

For `section`:

```text
s + e + c + tion -> secj
s + e + c + t + i + o + n -> section
```

The important candidate table is:

```text
su -> [see, sea]
secj -> [section]
```

## 5. Input events

The input events are:

```text
see + space     -> su<space>
sea + space     -> su;
section + period -> secj.
```

The semicolon selects the second candidate and consumes the word boundary.

## 6. Cost

A simple literal baseline is:

```text
see sea section.
```

which has one visible character per input event under the raw baseline.

The block-code input is conceptually:

```text
su<space> su; secj.
```

The evaluator computes this through segmentation paths, candidate rank, and delimiter commit cost. The exact cost depends on the configured cost model, but the important point is that the second candidate path for `sea` does not require a separate space key.

## 7. Why delimiter matters

If the evaluator treated `sea` and the following space separately, it would overcount:

```text
wrong model: sea + space -> su; + space
correct model: sea + space -> su;
```

That is why the evaluation unit is `(word, following_delimiter)`.
