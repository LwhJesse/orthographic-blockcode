# Orthographic BlockCode: A Framework for Searching Text-Entry Code Tables

## Abstract

Orthographic BlockCode is an experimental framework for evaluating and searching orthographic block-code mappings for text entry. It treats code-table design as a constrained discrete optimization problem. Given a mapping rule set and a corpus, the evaluator computes theoretical keystroke cost under a delimiter-aware text-entry model. The current system combines corpus-driven orthographic chunking, fixed-candidate decoding, symbolic keylog generation, and a C++/CUDA batch evaluator.

## 1. Motivation

Ordinary Latin-script typing is simple and robust because visible letters map directly to keys. However, many languages contain recurring orthographic structures. In English, examples include:

```text
ee, ea, th, sh, ch, tion, sion, ing, ment, able, ough, ight
```

The research question is whether these structures can be encoded in a deterministic text-entry system that reduces keystrokes without depending on dynamic prediction.

## 2. Orthographic block-code model

A code table is a set of rules:

```text
(chunk, code, scope, enabled, group)
```

A word may have multiple segmentation paths. Each path generates a code. The lexicon maps codes to fixed candidate lists ordered by frequency.

## 3. Objective

The evaluator computes:

```text
F(J, x) = y
```

A scalar objective may combine:

```text
L(J; X) = C_key(J, X)
        + lambda * C_collision(J)
        + mu * C_complexity(J)
        + nu * C_ergonomics(J)
```

## 4. Search loop

The search loop is:

```text
J -> F(J, x) -> J'
```

This turns code-table design into a measurable and searchable process.

## 5. Conclusion

Orthographic BlockCode is an early research framework for evaluating and searching structural text-entry code tables. The current prototype demonstrates that the problem can be formalized and implemented with a CUDA batch backend.
