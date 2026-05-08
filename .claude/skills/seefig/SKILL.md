---
name: seefig
description: Analyze, review, caption, or draft body text for a paper figure using OpenAI vision (GPT-4o). Use when the user says /seefig, "understand this figure", "explain this figure", "review the figure", "critique the figure", "caption this figure", "write a caption", "write paragraph for figure", "write body text for figure", or asks anything about a paper figure image.
---

# SeeFig — Figure Analyst

Analyze, review, caption, or draft body text for research paper figures using OpenAI's vision-capable chat completions (GPT-4o).

## Scripts

| Script | Description |
|---|---|
| `scripts/seefig.py` | Sends figure image(s) to OpenAI vision API and returns analysis |

All paths are relative to `.claude/skills/seefig/`.

## Dependencies

```
pip install openai python-dotenv
```

Requires `OPENAI_API_KEY`. The script loads it in priority order:
1. Shell environment variable (already exported)
2. Git repo root `.env`
3. Current working directory `.env`
4. Home directory `~/.env`

If the key is not found in any location the script exits with a clear error message.

## Default Model

`gpt-4o` (vision-capable). Override with `--model`:
- `gpt-4o-mini` — cheaper, faster, lower quality
- `gpt-4.1` — if available in the API

## Modes

| Mode | What it produces |
|---|---|
| `understand` | Detailed description of the figure: layout, panels, labels, what data is shown, what is depicted |
| `review` | Peer-review critique — clarity, visual hierarchy, missing labels, accessibility, alignment with claims, concrete improvement suggestions |
| `caption` | A single LaTeX-ready caption: one short bold phrase summarizing the figure, then 1-3 sentences of detail. Output is plain text, no markdown fences. |
| `write` | A body paragraph (~4-8 sentences) referencing the figure as `Figure~\ref{fig:<label>}`. Grounded in project context when provided. |

## Steps

1. **Identify inputs** from `$ARGUMENTS` or conversation context:
   - Which figure image file(s) to analyze (required)
   - Which mode to use: `understand`, `review`, `caption`, or `write`
   - Whether a context file is needed (`--context`)
   - The `--label` for `write` mode (e.g. `fig:system`)

2. **Show the user** the planned mode, image path(s), model, and any flags before running — get confirmation or edits if the mode is non-obvious.

3. **Run the script**:
   ```bash
   python -u .claude/skills/seefig/scripts/seefig.py \
       --mode <mode> \
       -i <path/to/figure.png> \
       [--context <path/to/context.md>] \
       [--label fig:<label>] \
       [--model gpt-4o] \
       [--prompt "<extra instruction>"]
   ```

4. **Surface the output**: Print the model's response to the user and note the saved output file path.

5. **Iterate**: Ask the user if they want a different mode, additional context, or a refined prompt.

## Quick Test

A sample image (`sample.jpg`) is included for testing. Try it out:

```bash
python -u .claude/skills/seefig/scripts/seefig.py \
    --mode understand \
    -i .claude/skills/seefig/sample.jpg
```

## Workflow — Typical Invocations

```bash
# 1) Understand a figure
python -u .claude/skills/seefig/scripts/seefig.py \
    --mode understand \
    -i path/to/figure.png

# 2) Review a figure with paper context
python -u .claude/skills/seefig/scripts/seefig.py \
    --mode review \
    -i path/to/figure.png \
    --context Dump.md

# 3) Generate a LaTeX caption
python -u .claude/skills/seefig/scripts/seefig.py \
    --mode caption \
    -i path/to/figure.png

# 4) Draft a body paragraph linked to the figure
python -u .claude/skills/seefig/scripts/seefig.py \
    --mode write \
    -i path/to/figure.png \
    --label fig:system \
    --context sections/system.tex

# 5) Compare two figures side by side
python -u .claude/skills/seefig/scripts/seefig.py \
    --mode review \
    -i path/to/fig_v1.png \
    -i path/to/fig_v2.png \
    --prompt "Compare the two versions and recommend which is clearer for the paper"
```

## CLI Flags Reference

| Flag | Required | Default | Description |
|---|---|---|---|
| `--mode` | Yes | — | `understand`, `review`, `caption`, or `write` |
| `-i, --image` | Yes (repeatable) | — | Path to figure image(s); pass multiple `-i` flags for multi-image |
| `--context` | No | — | Path to a markdown or .tex file to inject as project context |
| `--label` | No | `fig:figure` | LaTeX label used in `write` mode (`Figure~\ref{fig:<label>}`) |
| `--model` | No | `gpt-4o` | OpenAI model to use |
| `--prompt` | No | — | Extra instruction appended to the system prompt |
| `--output-dir` | No | `.claude/skills/seefig/outputs/` | Directory for saved output files |
| `--max-tokens` | No | `1500` | Maximum tokens in the model response |

## Output

- Model response is printed to stdout.
- A `.md` file is saved to `outputs/YYYYMMDD_HHMMSS_<mode>_<slug>.md` with a header recording: figure path(s), mode, model, label (if any), context file (if any), and the generated text.
- Each run is appended to `outputs/OUTPUT.md` as a new entry.

## Rules

- Always show the planned mode and image path(s) to the user before invoking the script.
- Never hardcode `OPENAI_API_KEY` — read only from `.env`.
- Outputs go to `.claude/skills/seefig/outputs/` — do not scatter files elsewhere.
- Update `outputs/OUTPUT.md` after each successful run.
- The `write` mode paragraph should reference the correct `fig:` label and fit the paper's narrative when context is provided.
