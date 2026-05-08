#!/usr/bin/env python3
"""Analyze HCI paper figures using OpenAI vision (GPT-4o).

Modes:
  understand  -- describe the figure in detail
  review      -- critique as an HCI paper reviewer (IMWUT/CHI)
  caption     -- produce a LaTeX-ready figure caption
  write       -- draft a body paragraph referencing the figure
"""

import argparse
import base64
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------------------------------------------------------
# Environment — load OPENAI_API_KEY with cascading .env lookup
# Priority: shell env var > repo root .env > CWD .env > ~/.env
# ---------------------------------------------------------------------------


def _find_repo_root() -> Path | None:
    """Return the git repository root, or None if not in a repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _load_env() -> Path | None:
    """Try loading .env from multiple locations. Return the repo root (or CWD)."""
    repo_root = _find_repo_root()

    # If OPENAI_API_KEY is already in the shell environment, skip .env loading
    if os.getenv("OPENAI_API_KEY"):
        return repo_root or Path.cwd()

    # Candidate .env paths in priority order
    candidates = []
    if repo_root:
        candidates.append(repo_root / ".env")
    candidates.append(Path.cwd() / ".env")
    candidates.append(Path.home() / ".env")

    for env_path in candidates:
        if env_path.exists():
            load_dotenv(env_path)
            if os.getenv("OPENAI_API_KEY"):
                return repo_root or Path.cwd()

    return repo_root or Path.cwd()


REPO_ROOT = _load_env()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print(
        "ERROR: OPENAI_API_KEY not found.\n"
        "Add the following line to the project root .env file:\n"
        "  OPENAI_API_KEY=sk-...",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# System prompts per mode
# ---------------------------------------------------------------------------

SYSTEM_PROMPTS = {
    "understand": (
        "You are an expert figure analyst for academic research papers. "
        "Describe the provided figure in precise detail: "
        "its overall layout and structure, individual panels or sections, "
        "all labels, legends, axes, color encodings, and annotations present, "
        "what data or content is depicted, and the apparent purpose of the figure "
        "within a research paper. Be thorough and systematic."
    ),
    "review": (
        "You are a senior reviewer for top-tier academic venues. "
        "Critique the provided figure as you would in a peer review. "
        "Evaluate: visual clarity and readability, visual hierarchy and focal point, "
        "label completeness and font legibility, color choices and accessibility "
        "(colorblind-safe?), alignment between the figure and typical paper claims, "
        "any missing annotations or context, whitespace and layout efficiency. "
        "Conclude with a prioritized list of concrete improvement suggestions. "
        "Be direct and constructive."
    ),
    "caption": (
        "You are an academic writing assistant specializing in research paper figures. "
        "Write a single LaTeX-ready figure caption for the provided figure. "
        "Format: one short bold phrase (the figure title), followed by 1-3 sentences "
        "that describe what is shown, highlight key takeaways, and orient the reader. "
        "Output plain text only — no markdown fences, no LaTeX \\caption{} wrapper, "
        "no extra commentary. The caption should stand alone without the surrounding paper text."
    ),
    "write": (
        "You are an academic writing assistant for research papers. "
        "Write a body paragraph (~4-8 sentences) of paper text that references and "
        "introduces the provided figure. The paragraph should: "
        "point the reader to the figure using the exact string Figure~\\ref{{fig:{label}}}, "
        "explain what the figure shows and why it matters, "
        "connect the figure to the surrounding argument, "
        "and use precise, formal academic English appropriate for a top-tier venue. "
        "Output the paragraph text only — no heading, no commentary."
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def encode_image(image_path: str) -> tuple[str, str]:
    """Read an image file and return (base64_data, media_type)."""
    path = Path(image_path).resolve()
    if not path.exists():
        print(f"ERROR: Image file not found: {image_path}", file=sys.stderr)
        sys.exit(1)
    suffix = path.suffix.lower()
    media_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_map.get(suffix, "image/png")
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > 20:
        print(
            f"WARNING: Image {image_path} is {size_mb:.1f} MB. "
            "OpenAI vision works best with images under 20 MB.",
            file=sys.stderr,
        )
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, media_type


def build_image_content_parts(image_paths: list[str]) -> list[dict]:
    """Build the list of image_url content parts for the OpenAI messages API."""
    parts = []
    for img_path in image_paths:
        b64, media_type = encode_image(img_path)
        parts.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{media_type};base64,{b64}", "detail": "high"},
            }
        )
    return parts


def slugify(text: str, max_len: int = 40) -> str:
    """Turn text into a filename-safe slug."""
    slug = text.lower().replace(" ", "_").replace("/", "_").replace("\\", "_")
    slug = "".join(c for c in slug if c.isalnum() or c == "_")
    return slug[:max_len].strip("_")


def read_context(context_path: str) -> str:
    """Read a context file (markdown or tex) as UTF-8."""
    path = Path(context_path).resolve()
    if not path.exists():
        print(f"ERROR: Context file not found: {context_path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Output saving
# ---------------------------------------------------------------------------


def save_output(
    output_dir: Path,
    mode: str,
    image_paths: list[str],
    model: str,
    label: str,
    context_path: str | None,
    result_text: str,
) -> Path:
    """Save the result to a timestamped .md file and update OUTPUT.md."""
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    first_stem = Path(image_paths[0]).stem
    slug = slugify(first_stem)
    out_filename = f"{timestamp}_{mode}_{slug}.md"
    out_path = output_dir / out_filename

    header_lines = [
        f"# SeeFig Output — {mode.upper()}",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Mode:** {mode}",
        f"**Model:** {model}",
        f"**Image(s):** {', '.join(image_paths)}",
    ]
    if label and mode == "write":
        header_lines.append(f"**Label:** fig:{label}")
    if context_path:
        header_lines.append(f"**Context file:** {context_path}")
    header_lines += ["", "---", "", "## Output", "", result_text, ""]

    content = "\n".join(header_lines)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\nOutput saved to: {out_path}")

    index_path = output_dir / "OUTPUT.md"
    index_exists = index_path.exists()
    with open(index_path, "a", encoding="utf-8") as f:
        if not index_exists:
            f.write("# SeeFig Outputs\n\n")
        image_str = ", ".join(f"`{p}`" for p in image_paths)
        f.write(f"### {timestamp} — {mode} — {first_stem}\n\n")
        f.write(f"**Images:** {image_str}  \n")
        f.write(f"**Model:** {model}  \n")
        if label and mode == "write":
            f.write(f"**Label:** `fig:{label}`  \n")
        if context_path:
            f.write(f"**Context:** `{context_path}`  \n")
        f.write(f"**File:** [{out_filename}](./{out_filename})\n\n")
        excerpt = result_text.replace("\n", " ")[:200]
        if len(result_text) > 200:
            excerpt += "..."
        f.write(f"> {excerpt}\n\n---\n\n")

    return out_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Analyze HCI paper figures using OpenAI vision (GPT-4o)."
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=["understand", "review", "caption", "write"],
        help="Analysis mode.",
    )
    parser.add_argument(
        "-i",
        "--image",
        action="append",
        required=True,
        dest="images",
        metavar="IMAGE",
        help="Path to a figure image. Repeat to pass multiple images.",
    )
    parser.add_argument(
        "--context",
        default=None,
        metavar="PATH",
        help="Optional path to a markdown or .tex context file.",
    )
    parser.add_argument(
        "--label",
        default="figure",
        help="LaTeX figure label (without 'fig:' prefix) used in write mode. Default: figure.",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="OpenAI model to use. Default: gpt-4o.",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="Extra instruction appended to the system prompt.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for saved output files. Default: .claude/skills/seefig/outputs/",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=1500,
        help="Maximum tokens in the model response. Default: 1500.",
    )
    args = parser.parse_args()

    # Resolve output directory
    if args.output_dir:
        output_dir = Path(args.output_dir).resolve()
    else:
        output_dir = REPO_ROOT / ".claude" / "skills" / "seefig" / "outputs"

    # Build system prompt
    if args.mode == "write":
        system_prompt = SYSTEM_PROMPTS["write"].format(label=args.label)
    else:
        system_prompt = SYSTEM_PROMPTS[args.mode]

    if args.prompt:
        system_prompt = system_prompt + "\n\n" + args.prompt

    # Build messages
    messages = [{"role": "system", "content": system_prompt}]

    if args.context:
        context_text = read_context(args.context)
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Project context (for grounding your response):\n\n{context_text}"
                ),
            }
        )

    image_parts = build_image_content_parts(args.images)
    image_count = len(args.images)
    if image_count == 1:
        task_text = f"Please analyze the following figure using mode: {args.mode}."
    else:
        task_text = (
            f"Please analyze the following {image_count} figures together using mode: {args.mode}."
        )

    user_content = [{"type": "text", "text": task_text}] + image_parts
    messages.append({"role": "user", "content": user_content})

    # Call OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    print(f"Mode:   {args.mode}")
    print(f"Model:  {args.model}")
    print(f"Images: {', '.join(args.images)}")
    if args.context:
        print(f"Context: {args.context}")
    if args.mode == "write":
        print(f"Label:  fig:{args.label}")
    print("Calling OpenAI vision API...\n")

    try:
        response = client.chat.completions.create(
            model=args.model,
            messages=messages,
            max_tokens=args.max_tokens,
        )
    except Exception as exc:
        print(f"ERROR: OpenAI API call failed: {exc}", file=sys.stderr)
        sys.exit(1)

    result_text = response.choices[0].message.content or ""

    print("=" * 72)
    print(result_text)
    print("=" * 72)

    save_output(
        output_dir=output_dir,
        mode=args.mode,
        image_paths=args.images,
        model=args.model,
        label=args.label,
        context_path=args.context,
        result_text=result_text,
    )


if __name__ == "__main__":
    main()
