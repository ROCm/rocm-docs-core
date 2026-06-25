"""Generate ``llms.txt`` and ``llms-full.txt`` from the resolved doctree.

These files follow the `llms.txt standard <https://llmstxt.org/>`_ and make the
documentation accessible to large language models and AI assistants.

When enabled via ``rocm_docs_generate_llms_full = True`` in ``conf.py``, this
module runs on the Sphinx ``build-finished`` event and writes two files to the
output directory:

* ``llms.txt`` -- a curated, link-only index of the documentation. Its structure
  follows the project's table of contents, and each entry's description comes
  from that page's ``description`` metadata (set via MyST ``html_meta`` or an
  RST ``.. meta::`` directive), falling back to the page title.
* ``llms-full.txt`` -- the prose documentation inlined into a single file.

Unlike a text-level filter, the content is produced from Sphinx's *resolved*
doctree using ``sphinx-markdown-builder``'s translator, so RST and Markdown
sources are handled identically and constructs like tables, code blocks,
math, footnotes, and cross-references survive conversion intact.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

import sphinx.util.logging
from docutils import nodes
from docutils.io import StringOutput
from sphinx.application import Sphinx
from sphinx_design.tabs import sd_tab_input, sd_tab_label
from sphinx_external_toc.api import FileItem, SiteMap, UrlItem
from sphinx_external_toc.parsing import parse_toc_yaml
from sphinx_markdown_builder.builder import (  # type: ignore[import-untyped]
    MarkdownBuilder,
)
from sphinx_markdown_builder.writer import (  # type: ignore[import-untyped]
    MarkdownWriter,
)

logger = sphinx.util.logging.getLogger(__name__)

INDEX_FILENAME = "llms.txt"
FULL_FILENAME = "llms-full.txt"

# Generated API-reference pages (doxygen/autodoc dumps) are noisy as prose and
# are linked rather than inlined. Doxysphinx emits pages under a ``doxygen/html``
# path segment, which may be nested under a project-specific root (for example
# ``demo/doxygen/html/...``), so this segment is matched anywhere in the docname.
EXCLUDED_DOC_PREFIXES: tuple[str, ...] = ("doxygen/", "_doxygen/")
EXCLUDED_DOC_SEGMENTS: tuple[str, ...] = ("doxygen/html/",)


class _DowngradeUnknownNodeFilter(logging.Filter):
    """Lower "unknown node type" warnings to INFO during Markdown rendering.

    Converting the resolved doctree to Markdown runs the sphinx-markdown-builder
    translator, which warns once per node type it has no visitor for (e.g.
    mermaid diagrams or custom directives). These warnings only appear because
    of this feature, never in a normal HTML build, and are not actionable by doc
    authors, so they are demoted to INFO to avoid build-warning noise.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno == logging.WARNING and record.getMessage().startswith(
            "unknown node type:"
        ):
            record.levelno = logging.INFO
            record.levelname = "INFO"
        return True


@dataclass
class _TocEntry:
    """A single navigable entry discovered from the table of contents."""

    docname: str | None
    url: str | None
    title: str | None
    depth: int


def generate_llms_full(app: Sphinx, exception: object) -> None:
    """Write ``llms.txt`` and ``llms-full.txt`` to the output directory.

    Connected to the ``build-finished`` event. Does nothing if the build failed
    (*exception* is not ``None``) or if the active builder does not produce HTML
    (e.g. linkcheck, doctest, latex, gettext). The generated links use ``.html``
    URLs, so they are only meaningful for HTML output.
    """
    if exception is not None:
        return
    if getattr(app.builder, "format", "") != "html":
        return

    base_url = _resolve_base_url(app)
    builder, writer = _build_markdown_renderer(app)

    # Rewrite internal links to absolute published URLs for the duration of the
    # render loop, then restore the original value so nothing else is affected.
    saved_http_base = app.config.markdown_http_base
    app.config.markdown_http_base = base_url
    # The "unknown node type" warning is emitted by SphinxTranslator via
    # ``sphinx.util.logging.getLogger(__name__)``, which prefixes the logger
    # name with "sphinx." -> "sphinx.sphinx.util.docutils".
    docutils_logger = logging.getLogger("sphinx.sphinx.util.docutils")
    downgrade_filter = _DowngradeUnknownNodeFilter()
    docutils_logger.addFilter(downgrade_filter)
    try:
        entries = list(_iter_toc_pages(app))
        rendered: dict[str, str] = {}
        descriptions: dict[str, str] = {}
        titles: dict[str, str] = {}
        for entry in entries:
            docname = entry.docname
            if docname is None:
                continue
            doctree = app.env.get_and_resolve_doctree(docname, app.builder)
            titles[docname] = entry.title or _page_title(doctree, docname)
            descriptions[docname] = _extract_description(app, docname, doctree)
            # Pages excluded from the full text are still listed in the index,
            # but their body is not inlined. This covers generated/doxygen pages
            # and very large pages that would otherwise dominate llms-full.txt.
            if _is_excluded_from_fulltext(app, docname):
                continue
            rendered[docname] = _render_page_markdown(
                builder, writer, doctree, docname
            )
    finally:
        docutils_logger.removeFilter(downgrade_filter)
        app.config.markdown_http_base = saved_http_base

    index = _assemble_index(app, base_url, entries, titles, descriptions)
    full = _assemble_full(index, entries, base_url, rendered)

    out_dir = Path(app.outdir)
    (out_dir / INDEX_FILENAME).write_text(index, encoding="utf-8")
    (out_dir / FULL_FILENAME).write_text(full, encoding="utf-8")
    logger.info("Wrote %s and %s", INDEX_FILENAME, FULL_FILENAME)


def _build_markdown_renderer(
    app: Sphinx,
) -> tuple[MarkdownBuilder, MarkdownWriter]:
    """Create a Markdown builder/writer pair for rendering single doctrees.

    The builder is initialized but never run as a full build; only its
    translator (via the writer) is used, page by page.
    """
    # Link to published HTML pages rather than to ``.md`` files.
    app.config.markdown_uri_doc_suffix = ".html"
    builder = MarkdownBuilder(app, app.env)
    builder.init()
    writer = MarkdownWriter(builder)
    return builder, writer


def _render_page_markdown(
    builder: MarkdownBuilder,
    writer: MarkdownWriter,
    doctree: nodes.document,
    docname: str,
) -> str:
    """Render one resolved doctree to a Markdown string (mirrors write_doc)."""
    clean = _strip_unsupported_nodes(doctree)
    builder.current_doc_name = docname
    builder.sec_numbers = builder.env.toc_secnumbers.get(docname, {})
    destination = StringOutput(encoding="utf-8")
    writer.write(clean, destination)
    return str(writer.output).strip()


# Admonition node types sphinx-markdown-builder has a visitor for. Other
# admonitions (e.g. ``tip``, ``caution``, generic ``admonition``) have no
# visitor and would be dropped entirely, so they are converted to ``note`` to
# preserve their content.
_SUPPORTED_ADMONITIONS: tuple[type[nodes.Element], ...] = (
    nodes.note,
    nodes.warning,
    nodes.important,
    nodes.attention,
    nodes.hint,
)


def _strip_unsupported_nodes(doctree: nodes.document) -> nodes.document:
    """Return a copy of *doctree* normalized for the Markdown translator.

    sphinx-markdown-builder has no visitor for several node types that would
    otherwise be dropped silently. To keep the output faithful:

    * ``meta`` nodes are removed (they carry no prose).
    * Admonitions the translator cannot render are converted to ``note`` so
      their content is preserved.
    * ``sphinx-design`` tab labels are converted to a bold paragraph so the tab
      identity (e.g. "AMD" vs "NVIDIA", "Linux" vs "Windows") is not lost, which
      otherwise risks conflating platform-specific instructions. The associated
      radio-button ``sd_tab_input`` nodes carry no text and are removed.
    """
    clean = doctree.deepcopy()
    for meta in list(clean.findall(nodes.meta)):
        meta.parent.remove(meta)
    for element in list(clean.findall(nodes.Element)):
        if not isinstance(element, nodes.Admonition):
            continue
        if isinstance(element, _SUPPORTED_ADMONITIONS):
            continue
        element.replace_self(nodes.note("", *element.children))
    for tab_input in list(clean.findall(sd_tab_input)):
        tab_input.parent.remove(tab_input)
    for label in list(clean.findall(sd_tab_label)):
        para = nodes.paragraph()
        para += nodes.strong(text=label.astext())
        label.replace_self(para)
    return clean


def _extract_description(
    app: Sphinx, docname: str, doctree: nodes.document
) -> str:
    """Find a one-line description for a page.

    Order: a ``meta`` node named ``description`` (MyST ``html_meta`` or RST
    ``.. meta::``) in the doctree, then Sphinx's collected page metadata, then
    an empty string.
    """
    for meta in doctree.findall(nodes.meta):
        name = meta.get("name", "")
        if name == "description" or name.startswith("description"):
            content = str(meta.get("content", "")).strip()
            if content:
                return content

    metadata = app.env.metadata.get(docname, {})
    for key, value in metadata.items():
        is_description = key == "description" or key.startswith("description")
        if is_description and isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def _page_title(doctree: nodes.document, docname: str) -> str:
    """Return the first section title of a page, falling back to its docname."""
    section = doctree.next_node(nodes.section)
    if section is not None:
        title = section.next_node(nodes.title)
        if title is not None:
            return str(title.astext()).strip()
    return docname


def _iter_toc_pages(app: Sphinx) -> Iterator[_TocEntry]:
    """Yield ``_TocEntry`` items in table-of-contents order.

    Falls back to all project documents (sorted) if the external TOC is missing
    or cannot be parsed, so projects without ``sphinx_external_toc`` still work.
    """
    toc_path = _toc_path(app)
    if toc_path is None or not toc_path.is_file():
        logger.info(
            "llms: no external TOC found, falling back to all documents"
        )
        yield from _fallback_entries(app)
        return

    try:
        site_map = parse_toc_yaml(toc_path)
    except Exception as err:  # degrade gracefully on a malformed TOC
        logger.warning("llms: could not parse TOC (%s); using all docs", err)
        yield from _fallback_entries(app)
        return

    root = site_map.root.docname
    root_norm = _normalize_docname(app, root)
    yield _TocEntry(docname=root_norm, url=None, title=None, depth=0)
    yield from _walk_sitemap(app, site_map, root, depth=1, seen={root_norm})


def _walk_sitemap(
    app: Sphinx, site_map: SiteMap, docname: str, depth: int, seen: set[str]
) -> Iterator[_TocEntry]:
    document = site_map[docname]
    for subtree in document.subtrees:
        for item in subtree.items:
            if isinstance(item, UrlItem):
                yield _TocEntry(
                    docname=None, url=item.url, title=item.title, depth=depth
                )
                continue
            if not isinstance(item, FileItem):
                # Glob items are expanded by Sphinx, not resolvable here.
                continue
            # TOC entries may carry the source suffix (e.g. "page.md"); Sphinx
            # docnames are suffix-less. De-duplicate on the normalized name so a
            # page referenced as both "page" and "page.md" is visited only once,
            # but keep the raw string for SiteMap lookups and recursion.
            child = str(item)
            norm = _normalize_docname(app, child)
            if norm in seen:
                continue
            seen.add(norm)
            try:
                child_doc = site_map[child]
            except KeyError:
                # Terminal page not registered as its own document.
                yield _TocEntry(docname=norm, url=None, title=None, depth=depth)
                continue
            yield _TocEntry(
                docname=norm, url=None, title=child_doc.title, depth=depth
            )
            yield from _walk_sitemap(app, site_map, child, depth + 1, seen)


def _normalize_docname(app: Sphinx, toc_docname: str) -> str:
    """Convert a TOC entry name to a Sphinx docname (without source suffix)."""
    return app.project.path2doc(toc_docname) or toc_docname


def _fallback_entries(app: Sphinx) -> Iterator[_TocEntry]:
    root = app.config.root_doc
    if root in app.project.docnames:
        yield _TocEntry(docname=root, url=None, title=None, depth=0)
    for docname in sorted(app.project.docnames):
        if docname != root:
            yield _TocEntry(docname=docname, url=None, title=None, depth=1)


def _toc_path(app: Sphinx) -> Path | None:
    toc = getattr(app.config, "external_toc_path", "")
    if not toc:
        return None
    return Path(app.srcdir) / toc


def _resolve_base_url(app: Sphinx) -> str:
    """Determine the published base URL for rewriting internal links."""
    for candidate in (
        app.config.rocm_docs_llms_base_url,
        getattr(app.config, "html_baseurl", ""),
        os.environ.get("READTHEDOCS_CANONICAL_URL", ""),
    ):
        if candidate:
            return candidate.rstrip("/")
    logger.info("llms: no base URL configured; internal links will be relative")
    return ""


def _is_excluded_docname(app: Sphinx, docname: str) -> bool:
    if docname.startswith(EXCLUDED_DOC_PREFIXES):
        return True
    if any(segment in docname for segment in EXCLUDED_DOC_SEGMENTS):
        return True
    doxygen_html = getattr(app.config, "doxygen_html", None)
    return bool(
        doxygen_html and docname.startswith(str(doxygen_html).strip("/") + "/")
    )


def _is_excluded_from_fulltext(app: Sphinx, docname: str) -> bool:
    """Return True if a page should be indexed but not inlined into the full text.

    Generated/doxygen pages (see :func:`_is_excluded_docname`) are always
    treated this way: they are noisy as prose but still useful as index links.
    Projects can exclude additional pages via ``rocm_docs_llms_full_exclude``, a
    list of docnames or glob patterns (matched against the suffix-less docname),
    to keep very large pages out of ``llms-full.txt`` while still listing them
    in ``llms.txt``.
    """
    if _is_excluded_docname(app, docname):
        return True
    patterns = getattr(app.config, "rocm_docs_llms_full_exclude", []) or []
    return any(fnmatch(docname, pattern) for pattern in patterns)


def _page_url(base_url: str, docname: str) -> str:
    if base_url:
        return f"{base_url}/{docname}.html"
    return f"{docname}.html"


def _llms_files_note() -> str:
    """A note that each ROCm project publishes its own llms files.

    ROCm documentation is split across multiple sites and projects, each served
    under ``https://<base_url>/projects/<project_name>/en/latest/``. This note
    tells an LLM consumer that ``llms.txt`` and ``llms-full.txt`` exist not only
    at the documentation root but also under each project's path, so other
    projects' files can be discovered too.
    """
    return (
        "> Note: ROCm documentation is split across multiple projects. In "
        "addition to this file, each project publishes its own `llms.txt` and "
        "`llms-full.txt` under "
        "`https://<base_url>/projects/<project_name>/en/latest/`."
    )


def _assemble_index(
    app: Sphinx,
    base_url: str,
    entries: list[_TocEntry],
    titles: dict[str, str],
    descriptions: dict[str, str],
) -> str:
    project_title = app.config.project or "Documentation"
    lines = [f"# {project_title}", ""]

    root = next((e for e in entries if e.depth == 0 and e.docname), None)
    if root is not None and root.docname is not None:
        root_description = descriptions.get(root.docname, "")
        if root_description:
            lines += [f"> {root_description}", ""]

    lines += [_llms_files_note(), ""]

    lines += ["## Docs", ""]
    for entry in entries:
        if entry.depth == 0:
            continue
        indent = "  " * (entry.depth - 1)
        if entry.url is not None:
            title = entry.title or entry.url
            lines.append(f"{indent}- [{title}]({entry.url})")
            continue
        docname = entry.docname
        if docname is None:
            continue
        title = titles.get(docname, docname)
        url = _page_url(base_url, docname)
        bullet = f"{indent}- [{title}]({url})"
        description = descriptions.get(docname, "")
        if description:
            bullet += f": {description}"
        lines.append(bullet)

    return "\n".join(lines) + "\n"


def _assemble_full(
    index: str,
    entries: list[_TocEntry],
    base_url: str,
    rendered: dict[str, str],
) -> str:
    parts = [index.rstrip()]
    for entry in entries:
        docname = entry.docname
        if docname is None or docname not in rendered:
            continue
        url = _page_url(base_url, docname)
        body = rendered[docname]
        # The rendered body already begins with the page's own title heading,
        # so only a separator and source attribution are prepended here.
        parts.append(f"---\n\nSource: {url}\n\n{body}")
    return "\n\n".join(parts) + "\n"
