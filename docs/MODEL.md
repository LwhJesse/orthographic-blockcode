# Model Notes

The central evaluation unit is a `(word, following_delimiter)` pair.

Example:

```text
ee / ea -> u
su -> [see, sea]

see + space -> su<space>
sea + space -> su;
see + comma -> su,
sea + comma -> su;,
```

A mapping rule has the form:

```text
(chunk, code, scope, enabled, group)
```

The evaluator enumerates legal segmentations of a word, converts each segmentation path to a code, determines the candidate rank, and computes commit cost under the following delimiter.

The evaluation function is:

$$
F(J, x) = y
$$

A corpus-level cost can be represented as:

$$
C(J, x)
=
C_{\mathrm{literal}}(x)
+
\sum_{w,d}
n_x(w,d)c_J(w,d)
$$

The current candidate policy is:

```text
rank 1: committed by space/punctuation
rank 2: selected by ;
rank 3: selected by '
```
