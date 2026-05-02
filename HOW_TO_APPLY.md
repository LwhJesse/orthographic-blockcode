# How to apply this documentation overlay

This archive contains only public documentation files.

Use it to overwrite the documentation in an existing `orthographic-blockcode` repository.

## Apply from inside your repository

```bash
unzip /path/to/orthographic-blockcode_docs_overlay_no_script.zip -d /tmp/obc_docs
cp -r /tmp/obc_docs/orthographic-blockcode_docs_overlay_no_script/* .
git diff -- README.md README.zh-CN.md docs/
```

Then review and commit:

```bash
git add README.md README.zh-CN.md docs/
git commit -m "Rewrite public documentation"
```

## What is included

```text
README.md
README.zh-CN.md
docs/*.md
```

No shell patch script is included in this overlay.
