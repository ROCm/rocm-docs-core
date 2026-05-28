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

# Matches markdown table separator rows (e.g. "|---|---|", "| :--- | ---: |").
_MD_TABLE_SEP_RE = re.compile(r"^\|[\s|:\-]+\|$")

# Matches RST directives whose indented body should be discarded (e.g. raw HTML).
_RST_SKIP_BLOCK_RE = re.compile(r"^\.\.\s+raw::")

# Matches HTML tags (e.g. "<div>", "</p>", "<!--") but NOT RST hyperlink URL
# continuation lines (e.g. "<https://...>`_").  The negative lookahead excludes
# URL schemes so that multi-line RST inline hyperlinks are preserved.
_HTML_TAG_RE = re.compile(r"^<(?!https?://|ftp://|mailto:)[a-zA-Z/!]")

# Matches trailing HTML close tags at the end of a prose line
# (e.g. "Browse blogs.</p>", "See the guide.</li></ul>").
_TRAILING_HTML_CLOSE_RE = re.compile(r"(</[a-zA-Z]+>)+\s*$")

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
    # Drop markdown table separator rows (e.g. "|---|---|", "| :--- | ---: |").
    if _MD_TABLE_SEP_RE.match(stripped):
        return False
    # Drop HTML tags (e.g. "<div>", "</p>") but keep RST hyperlink URL
    # continuation lines (e.g. "<https://rocm.docs.amd.com/...>`_").
    if _HTML_TAG_RE.match(stripped):
        return False
    # Drop RST directives, comments, hyperlink targets, and substitution defs.
    if stripped.startswith(".."):
        return False
    # Drop YAML frontmatter key-value pairs (e.g. "description lang=en": "text").
    if stripped.startswith('"') and re.match(r'^"[^"]+"\s*:', stripped):
        return False
    # Drop RST field list items (e.g. ":type: int") and extended RST meta
    # options (e.g. ":description lang=en: text").  Excludes inline roles at
    # line start (e.g. ":cpp:func:`hipMalloc` returns..." or
    # ":ref:`foo <bar>` describes...") because those are followed by a backtick,
    # not a space or end-of-line.
    if re.match(r"^:[A-Za-z][A-Za-z0-9_ =-]*:(\s|$)", stripped):
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
        base_text = base_file.read_text(encoding="utf-8").rstrip()
        # Drop a trailing "---" separator line so it doesn't double up with
        # the one prepended to each appended section below.
        if base_text.endswith("\n---"):
            base_text = base_text[:-4].rstrip()
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
        except Exception as e:
            logger.warning("Failed to read %s: %s", doc_file, e)
            continue

        lines = content.splitlines()
        prose_lines = [line for line in lines if _is_prose_line(line)]

        if len(prose_lines) < MIN_PROSE_LINES:
            continue

        relative = doc_file.relative_to(docs_root)
        in_backtick_fence = False
        in_rst_code_block = False
        in_rst_skip_block = False
        in_html_comment = False  # inside <!-- ... --> block
        in_html_open_tag = False  # inside a multi-line HTML opening tag
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
            # HTML comment block (<!-- ... -->): discard all content until -->.
            if in_html_comment:
                if "-->" in stripped:
                    in_html_comment = False
                continue
            # RST skip block (e.g. .. raw::): discard all indented content.
            if in_rst_skip_block:
                if not stripped or line[0] in (" ", "\t"):
                    continue
                in_rst_skip_block = False
            # RST code block: exit when a non-blank, non-indented line appears.
            if in_rst_code_block:
                if not stripped or line[0] in (" ", "\t"):
                    kept.append(line)
                    continue
                in_rst_code_block = False
            # RST raw block: enter and discard both the directive and its body.
            if _RST_SKIP_BLOCK_RE.match(stripped):
                in_rst_skip_block = True
                continue
            # RST code block: enter on directive line (directive itself dropped).
            if _RST_CODE_BLOCK_RE.match(stripped):
                in_rst_code_block = True
                continue
            # HTML comment open (<!-- ... -->): discard opener and enter state.
            if stripped.startswith("<!--"):
                if "-->" not in stripped:
                    in_html_comment = True
                continue
            # Multi-line HTML opening tag: skip continuation lines until >.
            if in_html_open_tag:
                if ">" in stripped:
                    in_html_open_tag = False
                continue
            # Detect HTML opening tags that wrap across lines (no > on this line).
            if _HTML_TAG_RE.match(stripped) and ">" not in stripped:
                in_html_open_tag = True
                continue
            if not stripped:
                kept.append(line)
            elif _is_prose_line(line):
                # Strip trailing HTML close tags (e.g. "See the guide.</p>").
                cleaned = _TRAILING_HTML_CLOSE_RE.sub("", line).rstrip()
                cleaned_stripped = cleaned.strip()
                if not cleaned_stripped:
                    # Entire line was HTML close tags — keep original (shouldn't
                    # normally reach here since _is_prose_line filters HTML).
                    kept.append(line)
                elif re.search(r"\w", cleaned_stripped):
                    # Line has real word content after stripping close tags.
                    kept.append(cleaned)
                # else: only punctuation remains (e.g. bare ".") — discard.
        cleaned = "\n".join(kept)

        combined.append(f"\n\n---\n\n# {relative}\n")
        combined.append(cleaned.strip())

    output_file.write_text(
        "\n".join(combined) + "\n",
        encoding="utf-8",
    )
    logger.info("llms-full.txt written to %s", output_file)
