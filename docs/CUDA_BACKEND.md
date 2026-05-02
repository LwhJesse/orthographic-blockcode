# CUDA Backend

The CUDA backend is a prototype batch evaluator. It evaluates many candidate mappings against the same lexicon and corpus representation.

## CPU side

The CPU prepares integer data structures:

- rule table;
- lexicon;
- segmentation paths;
- article word/delimiter counts;
- mapping batch.

## GPU side

The GPU computes costs for many mappings:

- convert paths to codes;
- estimate candidate rank;
- compute word-plus-delimiter costs;
- reduce corpus cost for each mapping.

The current backend uses brute-force candidate-rank estimation. The scalable design should emit code entries and perform sort/group/reduce.

The corpus-level cost is conceptually:

$$
C(J, x)
=
C_{\mathrm{literal}}(x)
+
\sum_{w,d}
n_x(w,d)c_J(w,d)
$$
