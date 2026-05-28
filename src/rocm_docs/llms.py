"""Generate llms-full.txt from documentation source files.

When enabled via ``rocm_docs_generate_llms_full = True`` in conf.py,
this module generates an ``llms-full.txt`` file in the output directory
after each successful build. The file aggregates prose content from all
``.md`` and ``.rst`` source files, suitable for AI agent consumption.

A project-level ``llms.txt`` in the source directory (if present) is used
as the header section; otherwise the Sphinx ``project`` name is used.
"""

from __future__ import annotations

from typing import Any

import re
from pathlib import Path

import sphinx.util.logging
from sphinx.application import Sphinx

logger = sphinx.util.logging.getLogger(__name__)

EXCLUDED_DIRS: set[str] = {
    "_build",
    "_templates",
    "_static",
    ".git",
    ".venv",
}

MARKUP_PREFIXES: tuple[str, ...] = (
    ":::",
    "```{",
    "```",
    ":img-top:",
    ":class",
    ":link:",
    ":link-type:",
    ":shadow:",
    ":columns:",
    ":padding:",
    ":gutter:",
    ":open:",
    ":name:",
    ":header-rows:",
    ":alt:",
    "+++",
    "<",
    "-->",
    "{bdg-",
)

# Matches lines like "align: center", "alt:", "name: foo" (directive options
# not starting with a colon, common in MyST figure/table fences).
_BARE_DIRECTIVE_RE = re.compile(r"^[a-z][a-z_-]*:\s*\S*$")

# Matches MyST/RST anchor labels like "(some-label)=".
_ANCHOR_LABEL_RE = re.compile(r"^\(\w[\w-]*\)=$")

# Matches RST section underlines (e.g. "====", "----", "~~~~").
_RST_UNDERLINE_RE = re.compile(r"^[=\-~^\"\'#*+]{3,}$")

# Matches RST code block directives (e.g. ".. code-block:: cpp", ".. code:: sh").
_RST_CODE_BLOCK_RE = re.compile(r"^\.\.\s+(code-block|code|sourcecode)::")

MIN_PROSE_LINES: int = 10


def _should_skip(path: Path) -> bool:
    """Return True if *path* is inside an excluded directory."""
    return any(part in EXCLUDED_DIRS for part in path.parts)


def _is_prose_line(line: str) -> bool:
    """Return True if *line* is human-readable prose (not markup noise)."""
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith(MARKUP_PREFIXES):
        return False
    # Drop bare directive-option lines (e.g. "align: center", "alt:").
    if _BARE_DIRECTIVE_RE.match(stripped):
        return False
    # Drop MyST/RST anchor labels (e.g. "(some-label)=").
    if _ANCHOR_LABEL_RE.match(stripped):
        return False
    # Drop RST directives, comments, hyperlink targets, and substitution defs.
    if stripped.startswith(".."):
        return False
    # Drop RST field list items (e.g. ":type: int") and MyST directive options
    # without a leading colon (e.g. "align: center").  Excludes inline roles at
    # line start (e.g. ":cpp:func:`hipMalloc` returns..." or
    # ":ref:`foo <bar>` describes...").
    if re.match(r"^:[A-Za-z][A-Za-z0-9_-]*:(\s|$)", stripped):
        return False
    # Drop RST section underlines (e.g. "====", "----", "~~~~").
    return not _RST_UNDERLINE_RE.match(stripped)


def generate_llms_full(app: Sphinx, exception: Any) -> None:
    """Write ``llms-full.txt`` to the output directory after a successful build.

    This function is connected to the ``build-finished`` Sphinx event.  It does
    nothing when *exception* is not ``None`` (i.e. the build failed).
    """
    if exception:
        return

    docs_root = Path(str(app.srcdir))
    output_file = Path(str(app.outdir)) / "llms-full.txt"
    base_file = docs_root / "llms.txt"

    combined: list[str] = []

    if base_file.exists():
        base_text = (
            base_file.read_text(encoding="utf-8").rstrip().rstrip("-").rstrip()
        )
        combined.append(base_text)
    else:
        combined.append(f"# {app.config.project}")

    all_files = sorted(
        list(docs_root.rglob("*.md")) + list(docs_root.rglob("*.rst"))
    )

    for doc_file in all_files:
        if _should_skip(doc_file):
            continue
        if doc_file == base_file:
            continue

        try:
            content = doc_file.read_text(encoding="utf-8")
        except Exception:
            continue

        lines = content.splitlines()
        prose_lines = [line for line in lines if _is_prose_line(line)]

        if len(prose_lines) < MIN_PROSE_LINES:
            continue

        relative = doc_file.relative_to(docs_root)
        in_backtick_fence = False
        in_rst_code_block = False
        kept: list[str] = []
        for line in lines:
            stripped = line.strip()
            # Backtick fences (MyST/Markdown)
            if stripped.startswith("```"):
                in_backtick_fence = not in_backtick_fence
                kept.append(line)
                continue
            if in_backtick_fence:
                kept.append(line)
                continue
            # RST code block: exit when a non-blank, non-indented line appears.
            if in_rst_code_block:
                if not stripped or line[0] in (" ", "\t"):
                    kept.append(line)
                    continue
                in_rst_code_block = False
            # RST code block: enter on directive line (directive itself dropped).
            if _RST_CODE_BLOCK_RE.match(stripped):
                in_rst_code_block = True
                continue
            if not stripped or _is_prose_line(line):
                kept.append(line)
        cleaned = "\n".join(kept)

        combined.append(f"\n\n---\n\n# {relative}\n")
        combined.append(cleaned.strip())

    output_file.write_text(
        "\n".join(combined) + "\n",
        encoding="utf-8",
    )
    logger.info("llms-full.txt written to %s", output_file)
