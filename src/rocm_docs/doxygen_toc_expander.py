"""
Expand _toc.yml.in with Doxygen children after Doxygen runs.

This module should be called from doxygen.py immediately after Doxygen completes.
It modifies _toc.yml.in (the template) so that when projects.py generates _toc.yml,
it includes all the Doxygen child pages.
"""

from __future__ import annotations

from pathlib import Path
import re

from sphinx.application import Sphinx
from sphinx.util import logging

logger = logging.getLogger(__name__)

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger.warning("pyyaml not found. Install with: pip install pyyaml")


# ============================================================
# Entry point
# ============================================================

def expand_toc_template(app: Sphinx, doxygen_root: Path) -> None:
    """Expand _toc.yml.in with Doxygen children."""

    if not getattr(app.config, "doxygen_toc_auto_expand", False):
        logger.debug("doxygen_toc_auto_expand is False, skipping")
        return

    if not YAML_AVAILABLE:
        return

    # ----------------------------------
    # locate template
    # ----------------------------------
    if hasattr(app.config, "external_toc_template_path"):
        toc_template = Path(app.confdir) / app.config.external_toc_template_path
    else:
        toc_template = Path(app.confdir) / ".sphinx" / "_toc.yml.in"

    if not toc_template.exists():
        logger.debug(f"TOC template not found: {toc_template}")
        return

    # ----------------------------------
    # locate doxygen html directory
    # ----------------------------------
    doxygen_html = None

    candidates = [
        doxygen_root / "docBin" / "html",
        Path(app.outdir) / getattr(app.config, "doxygen_html", ""),
        Path(app.srcdir) / getattr(app.config, "doxygen_html", ""),
        doxygen_root / "html",
    ]

    for c in candidates:
        if c and c.exists():
            doxygen_html = c
            logger.debug(f"Found Doxygen HTML at: {c}")
            break

    if not doxygen_html:
        logger.warning("Doxygen HTML not found. Cannot expand TOC.")
        return

    logger.info(f"Expanding {toc_template.name} with Doxygen children from {doxygen_html}")

    _do_expansion(toc_template, doxygen_html, app.config)


# ============================================================
# Main expansion
# ============================================================

def _do_expansion(toc_template: Path, doxygen_html: Path, config) -> None:
    """Perform the actual TOC expansion with correct root traversal."""

    logger.info(f"Reading TOC template: {toc_template}")

    toc_text = toc_template.read_text(encoding="utf-8")

    header_lines = []
    content_lines = []

    for line in toc_text.split("\n"):
        if line.strip().startswith("#"):
            header_lines.append(line)
        else:
            content_lines.append(line)

    toc_data = yaml.safe_load("\n".join(content_lines))

    logger.info(f"Parsed TOC type: {type(toc_data).__name__}")

    if not toc_data:
        logger.warning("Empty TOC template")
        return

    # --------------------------------------------------------
    # Normalize root into a list for uniform traversal
    # --------------------------------------------------------
    if isinstance(toc_data, list):
        root_nodes = toc_data
        logger.info(f"Root contains {len(root_nodes)} items (list mode)")
    else:
        root_nodes = [toc_data]
        logger.info("Root is dict → wrapping into list for traversal")

    max_children = getattr(config, "doxygen_toc_max_children", 50)

    logger.info(f"Max children per group: {max_children}")

    expanded_count, total_children = _expand_entries(
        root_nodes,
        doxygen_html,
        max_children,
    )

    if expanded_count == 0:
        logger.info("No Doxygen entries needed expansion")
        return

    with open(toc_template, "w", encoding="utf-8") as f:
        for line in header_lines:
            f.write(line + "\n")

        yaml.dump(
            toc_data,
            f,
            default_flow_style=False,
            indent=2,
            sort_keys=False,
            allow_unicode=True,
        )

    logger.info(f"Expanded {expanded_count} entries with {total_children} children")

# ============================================================
# Regex-only expansion (NO BeautifulSoup)
# ============================================================

_HREF_RE = re.compile(r'href="([^"]+\.html)"')


def _expand_entries(nodes: list, doxygen_html: Path, max_children: int):
    """
    Fully recursive walker that traverses the entire _toc.yml tree
    structure to find and expand doxygen/html/group__* entries at
    any nesting depth.

    The _toc.yml.in structure is:

        root (dict):
          subtrees:                     # list of subtree dicts
            - entries:                  # list of entry dicts
                - file: some/path
                  subtrees:             # entry can have its own subtrees
                    - entries:          # which contain more entries
                        - file: doxygen/html/group__X   ← TARGET

    The key insight is that BOTH subtree dicts AND entry dicts can
    contain "subtrees", so we must recurse into both.
    """

    expanded_count = 0
    total_children = 0

    logger.info(f"Scanning TOC using HTML root: {doxygen_html}")

    # High-level Doxygen index pages that should never appear as children
    _SKIP_STEMS = {"annotated", "files", "classes", "namespaces",
                    "namespacemembers", "functions", "globals", "pages",
                    "modules", "hierarchy", "inherits", "graph"}

    # --------------------------------------------------------
    def _extract_children(html_file: Path):
        """
        Extract child references from a Doxygen HTML page.

        Returns a dict with categorized children:
          {
            "structs": [{"file": "doxygen/html/structX"}, ...],
            "files":   [{"file": "doxygen/html/some__file_8h"}, ...],
            "groups":  [{"file": "doxygen/html/group__Y"}, ...],
            "other":   [{"file": "doxygen/html/namespaceZ"}, ...],
          }
        """
        logger.info(f"Opening HTML: {html_file}")

        if not html_file.exists():
            logger.warning(f"Missing HTML: {html_file}")
            return {"structs": [], "files": [], "groups": [], "other": []}

        text = html_file.read_text(encoding="utf-8", errors="ignore")

        seen = set()
        result = {"structs": [], "files": [], "groups": [], "other": []}

        for href in _HREF_RE.findall(text):
            name = Path(href).name

            if not name.endswith(".html"):
                continue

            stem = name[:-5]

            # Only process known Doxygen entity prefixes
            if not stem.startswith(("struct", "union", "class", "group",
                                     "namespace", "file", "_")):
                # Also match Doxygen file pages like "some__thing_8h"
                if "_8" not in stem:
                    continue

            # Skip high-level Doxygen index pages
            if stem in _SKIP_STEMS:
                continue

            # Skip source-view and directory pages
            if stem.endswith("_source") or stem.startswith("dir_"):
                continue

            # Skip self-references
            if stem == html_file.stem:
                continue

            if stem in seen:
                continue

            seen.add(stem)

            child = {"file": f"doxygen/html/{stem}"}

            # Categorize by prefix
            if stem.startswith(("struct", "class", "union")):
                result["structs"].append(child)
            elif stem.startswith("group"):
                # Skip group cross-references — these are high-level
                # pages that should only appear where manually placed
                continue
            elif re.search(r"_8(h|hpp|c|cpp|cu|cuh|inl)$", stem):
                result["files"].append(child)
            elif stem.startswith(("file", "namespace")):
                result["other"].append(child)
            else:
                # Unknown type — skip to avoid polluting categories
                continue

        total = sum(len(v) for v in result.values())
        logger.info(
            f"Extracted {total} children from {html_file.name} "
            f"(structs={len(result['structs'])}, files={len(result['files'])}, "
            f"groups={len(result['groups'])}, other={len(result['other'])})"
        )

        return result

    # --------------------------------------------------------
    def _collect_existing_files(entries: list) -> set:
        """Collect all file values already present in a list of entries."""
        existing = set()
        for entry in entries:
            if isinstance(entry, dict) and "file" in entry:
                existing.add(entry["file"])
        return existing

    # --------------------------------------------------------
    def _try_expand_entry(entry: dict, level: int, sibling_entries: list):
        """
        Expand a doxygen/html/ entry with children from its HTML page.

        Three types of expandable entries:
          1. group__*   → extract structs/files, route to annotated/files siblings
          2. annotated  → self-expand: scan annotated.html for struct/class/union
          3. files      → self-expand: scan files.html for _8h file pages

        All other doxygen/html/ entries are leaves (no expansion).
        Always overwrites existing subtrees.
        """
        nonlocal expanded_count, total_children

        indent = "  " * level
        file_value = entry.get("file", "")

        logger.info(f"{indent}Checking entry: {file_value}")

        if not file_value.startswith("doxygen/html/"):
            return

        stem = Path(file_value).name

        # ==== ANNOTATED: self-expand with structs/classes from its HTML ====
        if stem == "annotated":
            html_file = doxygen_html / "annotated.html"
            categorized = _extract_children(html_file)
            # Merge with any children already routed from groups
            existing = _collect_existing_files(
                entry.get("subtrees", [{}])[0].get("entries", [])
                if entry.get("subtrees") else []
            )
            new_children = [{"file": c["file"]} for c in categorized["structs"][:max_children]
                           if c["file"] not in existing]
            if new_children:
                if "subtrees" not in entry:
                    entry["subtrees"] = [{"entries": []}]
                entry["subtrees"][0].setdefault("entries", []).extend(new_children)
            all_count = len(entry.get("subtrees", [{}])[0].get("entries", [])
                           if entry.get("subtrees") else [])
            if all_count > 0:
                expanded_count += 1
                total_children += all_count
                logger.info(f"{indent}  → annotated: {all_count} total structs ({len(new_children)} from HTML)")
            return

        # ==== FILES: self-expand with file pages from its HTML ====
        if stem == "files":
            html_file = doxygen_html / "files.html"
            categorized = _extract_children(html_file)
            # Merge with any children already routed from groups
            existing = _collect_existing_files(
                entry.get("subtrees", [{}])[0].get("entries", [])
                if entry.get("subtrees") else []
            )
            new_children = [{"file": c["file"]} for c in categorized["files"][:max_children]
                           if c["file"] not in existing]
            if new_children:
                if "subtrees" not in entry:
                    entry["subtrees"] = [{"entries": []}]
                entry["subtrees"][0].setdefault("entries", []).extend(new_children)
            all_count = len(entry.get("subtrees", [{}])[0].get("entries", [])
                           if entry.get("subtrees") else [])
            if all_count > 0:
                expanded_count += 1
                total_children += all_count
                logger.info(f"{indent}  → files: {all_count} total file pages ({len(new_children)} from HTML)")
            return

        # ==== GROUP: route children to annotated/files siblings ====
        if not stem.startswith("group"):
            logger.info(f"{indent}  → skipped (leaf entry: {stem})")
            return

        html_file = doxygen_html / f"{stem}.html"
        categorized = _extract_children(html_file)

        # Find sibling 'annotated' and 'files' entries to route into
        annotated_entry = None
        files_entry = None

        for sibling in sibling_entries:
            if not isinstance(sibling, dict):
                continue
            sfile = sibling.get("file", "")
            if sfile == "doxygen/html/annotated":
                annotated_entry = sibling
            elif sfile == "doxygen/html/files":
                files_entry = sibling

        # Route struct/class/union children to 'annotated' sibling
        # Use dict COPIES to avoid PyYAML anchor/alias (&id / *id)
        routed_structs = categorized["structs"][:max_children]
        if routed_structs and annotated_entry is not None:
            existing = _collect_existing_files(
                annotated_entry.get("subtrees", [{}])[0].get("entries", [])
                if annotated_entry.get("subtrees") else []
            )
            new_structs = [{"file": c["file"]} for c in routed_structs
                          if c["file"] not in existing]
            if new_structs:
                if "subtrees" not in annotated_entry:
                    annotated_entry["subtrees"] = [{"entries": []}]
                annotated_entry["subtrees"][0].setdefault("entries", []).extend(new_structs)
                logger.info(f"{indent}  → routed {len(new_structs)} structs to annotated")

        # Route file children to 'files' sibling (also copies)
        routed_files = categorized["files"][:max_children]
        if routed_files and files_entry is not None:
            existing = _collect_existing_files(
                files_entry.get("subtrees", [{}])[0].get("entries", [])
                if files_entry.get("subtrees") else []
            )
            new_files = [{"file": c["file"]} for c in routed_files
                        if c["file"] not in existing]
            if new_files:
                if "subtrees" not in files_entry:
                    files_entry["subtrees"] = [{"entries": []}]
                files_entry["subtrees"][0].setdefault("entries", []).extend(new_files)
                logger.info(f"{indent}  → routed {len(new_files)} files to files")

        # Direct children for this group: only 'other' category
        # (structs go to annotated, files go to files, groups are skipped)
        direct_children = [{"file": c["file"]} for c in categorized["other"][:max_children]]

        # Set direct children on the group entry itself (always overwrite)
        if direct_children:
            entry["subtrees"] = [{"entries": direct_children}]
            expanded_count += 1
            total_children += len(direct_children)
            logger.info(f"{indent}  → expanded with {len(direct_children)} direct children")
        else:
            # Remove stale subtrees if no direct children
            entry.pop("subtrees", None)
            expanded_count += 1
            logger.info(f"{indent}  → no direct children (structs/files routed to siblings)")

    # --------------------------------------------------------
    def _walk(node: dict, level: int = 0):
        """
        Recursively walk a single TOC node (dict).

        TOC structure:
          container: { subtrees: [ {entries: [entry, ...]}, ... ] }
          entry:     { file: "...", subtrees: [ {entries: [...]}, ... ] }

        A container has "subtrees" (but no "file").
        An entry has "file" and optionally "subtrees".
        A subtree dict has "entries" and optionally "caption".
        """
        if not isinstance(node, dict):
            return

        indent = "  " * level

        # Process entries in this node — two passes:
        # Pass 1: group entries (route structs→annotated, files→files)
        # Pass 2: annotated/files entries (self-expand from their HTML)
        # This ensures groups populate annotated/files first, then
        # self-expansion only adds what's not already there.
        if "entries" in node:
            entries = node["entries"]
            logger.info(f"{indent}Processing entries ({len(entries)} items)")

            # Pass 1: groups
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                stem = Path(entry.get("file", "")).name
                if stem.startswith("group"):
                    had_subtrees = "subtrees" in entry
                    _try_expand_entry(entry, level + 1, sibling_entries=entries)
                    if had_subtrees:
                        for subtree in entry.get("subtrees", []):
                            _walk(subtree, level + 1)

            # Pass 2: annotated, files, and other doxygen entries
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                stem = Path(entry.get("file", "")).name
                if stem.startswith("group"):
                    continue  # already handled
                had_subtrees = "subtrees" in entry
                _try_expand_entry(entry, level + 1, sibling_entries=entries)
                if had_subtrees:
                    for subtree in entry.get("subtrees", []):
                        _walk(subtree, level + 1)

            # Pass 3: recurse into non-doxygen entries' subtrees
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                file_value = entry.get("file", "")
                if file_value.startswith("doxygen/html/"):
                    continue  # already handled above
                for subtree in entry.get("subtrees", []):
                    _walk(subtree, level + 1)

        # For container nodes (root or caption sections), descend
        # into subtrees. Skip if this node has "entries" — those
        # subtrees belong to entries and are handled above.
        elif "subtrees" in node:
            logger.info(f"{indent}Descending into subtrees ({len(node['subtrees'])} items)")

            for subtree in node["subtrees"]:
                _walk(subtree, level + 1)

    # --------------------------------------------------------
    # Start walking from each root node
    for node in nodes:
        _walk(node, level=0)

    # --------------------------------------------------------
    # Global deduplication pass: remove duplicate doxygen/html/
    # file entries across the ENTIRE tree (not just within one
    # entries list). First occurrence wins.
    # --------------------------------------------------------
    def _dedup_entries(tree, global_seen: set):
        """Remove duplicate doxygen/html/ file entries across the whole tree."""
        if not isinstance(tree, dict):
            return
        if "entries" in tree:
            deduped = []
            for entry in tree["entries"]:
                if isinstance(entry, dict):
                    fv = entry.get("file", "")
                    if fv.startswith("doxygen/html/") and fv in global_seen:
                        continue
                    if fv.startswith("doxygen/html/"):
                        global_seen.add(fv)
                deduped.append(entry)
            tree["entries"] = deduped

            for entry in tree["entries"]:
                if isinstance(entry, dict):
                    for subtree in entry.get("subtrees", []):
                        _dedup_entries(subtree, global_seen)

        if "subtrees" in tree:
            for subtree in tree["subtrees"]:
                _dedup_entries(subtree, global_seen)

    global_seen = set()
    for node in nodes:
        _dedup_entries(node, global_seen)

    # --------------------------------------------------------
    # Cleanup pass: remove empty entries/subtrees that result
    # from deduplication (etoc requires non-empty entries lists)
    # --------------------------------------------------------
    def _cleanup_empty(tree):
        """Remove subtrees with empty entries lists."""
        if not isinstance(tree, dict):
            return

        # Clean entries' subtrees first (depth-first)
        if "entries" in tree:
            for entry in tree["entries"]:
                if isinstance(entry, dict) and "subtrees" in entry:
                    for subtree in entry["subtrees"]:
                        _cleanup_empty(subtree)
                    # Remove subtrees that now have empty entries
                    entry["subtrees"] = [
                        st for st in entry["subtrees"]
                        if not isinstance(st, dict)
                        or "entries" not in st
                        or len(st["entries"]) > 0
                    ]
                    if not entry["subtrees"]:
                        del entry["subtrees"]

        if "subtrees" in tree:
            for subtree in tree["subtrees"]:
                _cleanup_empty(subtree)
            tree["subtrees"] = [
                st for st in tree["subtrees"]
                if not isinstance(st, dict)
                or "entries" not in st
                or len(st["entries"]) > 0
            ]

    for node in nodes:
        _cleanup_empty(node)

    logger.info(f"Expansion summary: {expanded_count} groups, {total_children} children")

    return expanded_count, total_children


# ============================================================
# Dummy Sphinx setup
# ============================================================

def setup(app):
    app.add_config_value("doxygen_toc_auto_expand", False, "env", bool)
    app.add_config_value("doxygen_toc_max_children", 50, "env", int)

    return {
        "parallel_read_safe": True,
        "parallel_write_safe": False,
        "version": "6.0.0",
    }