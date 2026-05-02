# Roadmap

## Short term

- Stabilize the prototype.
- Align Python and CUDA evaluator outputs.
- Add word-level debugging.
- Add larger public lexicons.
- Add basic corpus weighting.

## Medium term

- Implement `add_rule`, `remove_rule`, and `change_scope`.
- Add beam search or simulated annealing.
- Report rank, collision, and fallback metrics.
- Generate a first weak solution under fixed constraints.

## Long term

- Replace brute-force CUDA ranking with sort/group/reduce.
- Generate theoretical, balanced, and human-friendly code tables.
- Build a typing trainer.
- Run small user studies.
- Test transfer to other Latin-script languages.
