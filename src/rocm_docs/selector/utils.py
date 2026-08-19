"""Shared utilities for the selector directive package."""

import html
import json

from docutils import nodes
from sphinx.util import logging


def normalize_key(key):
    """Normalize a selector key to lowercase with underscores."""
    return key.replace(" ", "_").lower().strip()


def register_output_flags(app):
    """Register the shared output-generation toggles (idempotently).

    Both the matrix and selector extensions read these flags, and either may be
    loaded first, so registration must not fail if the value already exists:

    - ``rocm_docs_pdf_mock_selector_state``: controls PDF (LaTeX) selector expansion.
        * ``False`` — omit selector content from the PDF entirely (default).
        * ``True``  — expand all selector combinations for every page.
        * ``dict``  — page-scoped mock state: maps each docname (source-file
          path without extension) to a list of spec dicts representing simulated
          selector selections.  Only combos matching at least one spec are
          included.  Pages not listed in the dict are skipped.
          Example: ``{"install/rocm": [{"os": "ubuntu", "ver": "24.04"}]}``
    - ``rocm_selector_markdown_generation``: when False, custom matrix/selector
      content is dropped from Markdown (llms-full.txt) output.
    """
    if "rocm_docs_pdf_mock_selector_state" not in app.config:
        # Accept either a bool (all/none) or a dict (page-scoped mock states).
        app.add_config_value(
            "rocm_docs_pdf_mock_selector_state",
            False,
            "env",
            types=(bool, dict),
        )
    if "rocm_selector_markdown_generation" not in app.config:
        app.add_config_value("rocm_selector_markdown_generation", True, "env")


def noop(translator, node):
    """No-op visit/depart handler for builders that render nothing."""
    pass


def skip_node(_translator, _node):
    """Visit handler that skips a node and its children entirely."""
    raise nodes.SkipNode


def make_unique_id(document, base, node=None):
    """Return an ID derived from *base* that is unique within *document*.

    ``nodes.make_id`` alone can collide when the same heading (e.g.
    "Prerequisites") appears in several conditional blocks. This appends a
    numeric suffix on collision and registers the chosen ID in
    ``document.ids`` so subsequent calls (and Sphinx's own reference
    resolution) see it as taken. Falls back to a slug for bases that
    ``make_id`` reduces to empty (e.g. starting with a digit).

    Pass *node* to register the owning element; otherwise the ID maps to the
    document, which is enough to reserve it against future collisions.
    """
    base_id = (
        nodes.make_id(base)
        or "id-" + base.replace(".", "-").replace(" ", "-").lower()
    )
    candidate = base_id
    counter = 1
    existing = document.ids
    while candidate in existing:
        counter += 1
        candidate = f"{base_id}-{counter}"
    existing[candidate] = node if node is not None else document
    return candidate


def kv_to_data_attr(name, kv_str, separator="="):
    """Convert key=value pairs delimited by spaces to stringified JSON.

    Format it as an HTML data attribute.

    Args:
        name: Name of the data attribute; it will be prefixed with "data-" for conventional HTML.
        kv_str: String in format "key=value os=ubuntu".

    Example output:
        'data-show-cond="{"os": "ubuntu"}"'
    """
    pairs: dict[str, list[str]] = {}
    for token in kv_str.split():
        token = token.strip()
        if not token or separator not in token:
            continue

        key, value = token.split(separator, 1)
        if key and value:
            pairs.setdefault(key, []).append(value.strip())

    return f'data-{name}="{html.escape(json.dumps(pairs))}"' if pairs else ""


logger = logging.getLogger(__name__)
