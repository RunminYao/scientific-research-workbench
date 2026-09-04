# Minimal LaTeX quick start

Compile the one-file project:

```bash
latexmk -pdf main.tex
```

Then ask Codex: `Use $edit-scientific-manuscripts to review main.tex conservatively and preserve its scientific meaning.`

Accept when `main.pdf` exists and the LaTeX log has no errors. Clean with `latexmk -C`.
