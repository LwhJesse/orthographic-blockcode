# Quickstart: Ninja CUDA Build

```bash
unzip blockcode_cuda_v07_ninja.zip
cd blockcode_cuda_v07_ninja

scripts/configure_ninja.sh
ninja

scripts/run_cuda_sample.sh
scripts/run_cuda_batch.sh
```

If architecture detection fails:

```bash
scripts/configure_ninja.sh sm_86
ninja
```

For RTX 40 series:

```bash
scripts/configure_ninja.sh sm_89
ninja
```

The executable is:

```text
bin/blockcode_cuda_eval
```
