# seefig

**A figure assistant for researchers.** A Claude Code skill that understands, reviews, captions, and writes about your paper figures — powered by OpenAI Vision (GPT-4o).

Works anywhere Claude Code runs — macOS, Windows, and Linux.

## Why?

You're writing a paper. You have figures — charts, diagrams, photos, study results. You need a caption, a second pair of eyes, or a paragraph that ties the figure into your narrative.

Instead of switching to another tool or staring at a blank line, just ask Claude.

| Mode | What you get |
|------|-------------|
| `understand` | Detailed breakdown — layout, panels, labels, data, purpose |
| `review` | Peer-review critique — clarity, accessibility, concrete suggestions |
| `caption` | LaTeX-ready caption — bold title + 1-3 descriptive sentences |
| `write` | Body paragraph — 4-8 sentences referencing `Figure~\ref{fig:...}` |

## Setup

Ask Claude:

```
Setup this skill: https://github.com/sangwonme/ClaudeCode-SeeFig.git
```

That's it. Claude handles the rest.

### API Key

The skill needs an `OPENAI_API_KEY`. Place it in **any** of these locations (checked in order):

1. Shell environment variable (`export OPENAI_API_KEY=sk-...`)
2. `.env` in your git repo root
3. `.env` in your current working directory
4. `~/.env` in your home directory

## Usage

Say any of these to Claude:

- `/seefig` — invoke the skill directly
- *"Understand this figure"*
- *"Review my figure"*
- *"Caption this figure"*
- *"Write a paragraph about this figure"*

Claude will ask for the image path, pick the right mode, and run the analysis.

### Quick Test

A sample image is included so you can verify everything works right away:

```
Understand .claude/skills/seefig/sample.jpg
```

### Use It In Your Paper Workflow

```
# Get a reviewer's perspective before submission
Review figs/results.png

# Generate a caption while writing
Caption figs/system-overview.png

# Draft a paragraph grounded in your paper
Write a paragraph for figs/pipeline.png with context from sections/method.tex
```

## How It Works

```
User asks about a figure
        |
        v
Claude picks a mode (understand / review / caption / write)
        |
        v
seefig.py encodes the image as base64
        |
        v
Sends to OpenAI Vision API (GPT-4o)
        |
        v
Returns analysis + saves to outputs/
```

## File Structure

```
.claude/skills/seefig/
    scripts/
        seefig.py            # Main script — calls OpenAI Vision API
    outputs/
        OUTPUT.md            # Index of all past runs
        *.md                 # Individual run outputs
    sample.jpg               # Sample image for testing
    SKILL.md                 # Skill definition for Claude Code
```

## Requirements

- Python 3.10+
- [`openai`](https://pypi.org/project/openai/) and [`python-dotenv`](https://pypi.org/project/python-dotenv/)
- An OpenAI API key with access to `gpt-4o`

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `OPENAI_API_KEY not found` | Add your key to `.env` or export it in your shell |
| `401 Incorrect API key` | Your key is invalid or expired — regenerate at [platform.openai.com](https://platform.openai.com/api-keys) |
| `ModuleNotFoundError: openai` | Run `pip install openai python-dotenv` |
| Output is too short | Increase `--max-tokens` (default 1500) |

## Customization

### Change the model

```bash
# Cheaper & faster
--model gpt-4o-mini

# Latest model
--model gpt-4.1
```

### Add context for grounded output

```bash
# Feed your paper draft so the output matches your narrative
--context path/to/paper.tex
```

### Extra instructions

```bash
# Append custom instructions to the system prompt
--prompt "Focus on statistical clarity and axis labeling"
```

## License

MIT
