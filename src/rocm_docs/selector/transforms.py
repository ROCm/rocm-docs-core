"""Post-transforms for converting selector nodes for non-HTML builders."""

from collections.abc import Sequence

from docutils import nodes
from sphinx.transforms.post_transforms import SphinxPostTransform

from .nodes import SelectedContent, SelectorGroup, SelectorInfo, SelectorOption
from .utils import logger, make_unique_id, normalize_key

# ---------------------------------------------------------------------------
# Constants and helpers for SelectorPDFReorganizeTransform.
# These must appear after all node classes they reference.
# ---------------------------------------------------------------------------

# Node types that are selector UI chrome — always skipped when gathering content
_SELECTOR_UI = (SelectorGroup, SelectorOption, SelectorInfo)

# Condition keys to treat as always-match during PDF filtering.
#
# Empty by design: ``gfx``/``gpu``/``arch`` conditions must be *evaluated*, not
# ignored. A PDF combo is keyed on (fam, os, os-ver, i) and carries no ``gfx``
# entry, so a ``gfx=…`` condition falls through to ``_matches``'s "key absent
# from combo" branch and is correctly excluded — collapsing the many
# GPU-specific meta-package cells/blocks down to the single ``fam=all`` variant.
# Previously ``gfx`` was ignored (always-match), which dumped every GPU variant
# into the PDF (e.g. the 14-column meta-package table).
_IGNORE_KEYS: set[str] = set()


def _parse_cond(show_cond: str) -> dict[str, list[str]]:
    """Parse a ``show-cond`` string into {key: [values]}.

    Same-key entries are OR'd; different keys are AND'd.
    Keys in ``_IGNORE_KEYS`` are dropped so they never block a match.
    """
    result: dict[str, list[str]] = {}
    for token in show_cond.split():
        if "=" not in token:
            continue
        k, _, v = token.partition("=")
        k = normalize_key(k)
        v = normalize_key(v)
        if k in _IGNORE_KEYS:
            continue
        result.setdefault(k, []).append(v)
    return result


def _matches(show_cond: str, combo: dict[str, str]) -> bool:
    """Return True if *combo* satisfies all conditions in *show_cond*.

    *combo* is a dict of {key: value} for the current (fam, os, ver, i).

    - Empty show-cond → always True (unconditional content).
    - Keys in ``_IGNORE_KEYS`` are stripped before matching (too granular).
    - Any remaining key that is absent from *combo* means the content
      belongs to a dimension that does not exist in the PDF (e.g. ``w``
      for the graphics/compute workload toggle) → returns False so those
      blocks are excluded rather than duplicated across every combo.
    """
    if not show_cond:
        return True
    cond = _parse_cond(show_cond)
    for key, allowed in cond.items():
        if key not in combo:
            return False  # dimension absent from PDF combos — exclude
        if combo[key] not in allowed:
            return False
    return True


def _make_pdf_id(*parts: str) -> str:
    """Build a unique, valid HTML/LaTeX ID from an arbitrary list of strings."""
    raw = "-".join(str(p) for p in parts if p)
    id_ = nodes.make_id(raw)
    # make_id returns "" for strings that start with digits (e.g. version "26.04");
    # fall back to a prefixed slug.
    return id_ or "pdf-" + raw.replace(".", "-").replace(" ", "-").lower()


def _iter_matrix_own(start, cls_name):
    """Yield descendants of *start* whose class is *cls_name*, stopping at a nested matrix.

    An inner matrix's rows/cells are not pulled into the outer grid.

    The matrix nodes live in a sibling extension; they are matched by class
    name rather than imported so this module stays decoupled from the matrix
    package (the import path differs across repo layouts).
    """
    for child in start.children:
        if type(child).__name__ == "CustomTable":
            continue  # boundary: a nested matrix owns its own rows/cells
        if type(child).__name__ == cls_name:
            yield child
        yield from _iter_matrix_own(child, cls_name)


def _filter_matrix(
    table_node: nodes.Node, combo: dict[str, str], id_prefix: str = ""
) -> nodes.Node:
    """Return a deep copy of a matrix ``CustomTable`` filtered for *combo*.

    In HTML, matrix rows/cells carrying a ``show-cond`` are shown or hidden by
    JavaScript for the selected device. The PDF has no JavaScript, so without
    filtering every conditional cell would render — e.g. all 11 GPU-specific
    package-name cells exploding a 3-column table into 14 columns. This drops
    rows and cells whose ``show-cond`` does not match *combo*, then filters any
    ``SelectedContent`` nested inside a surviving cell (so its per-GPU variants
    collapse to the matching one).
    """
    new_table = table_node.deepcopy()
    for row in list(_iter_matrix_own(new_table, "CustomTableRow")):
        row_cond = row.get("show-cond", "")
        if row_cond and not _matches(row_cond, combo):
            row.parent.remove(row)
            continue
        for cell in list(_iter_matrix_own(row, "CustomTableCell")):
            cell_cond = cell.get("show-cond", "")
            if cell_cond and not _matches(cell_cond, combo):
                cell.parent.remove(cell)
                continue
            if list(cell.findall(SelectedContent)):
                filtered: list[nodes.Node] = []
                _gather_content(cell.children, combo, filtered, id_prefix)
                cell.children = []
                for c in filtered:
                    c.parent = cell
                    cell.children.append(c)
    return new_table


def _gather_content(
    children: Sequence[nodes.Node],
    combo: dict[str, str],
    into: list[nodes.Node],
    id_prefix: str = "",
) -> None:
    """Recursively collect content nodes that match *combo*.

    - ``SelectedContent`` nodes whose ``show-cond`` does not match *combo* are
      skipped entirely.
    - ``SelectedContent`` nodes that match are unwrapped: their children are
      processed recursively, with a heading section prepended if they carry one.
    - Regular ``section`` nodes (Prerequisites, Installation, etc.) are recursed
      into and rebuilt with only the filtered content; empty sections are dropped.
    - Selector UI nodes (``SelectorGroup`` etc.) are always skipped.
    - Any other container node (dropdowns, admonitions, etc.) that contains
      ``SelectedContent`` descendants is recursed into and rebuilt so that
      filtering propagates through it.  Containers with no ``SelectedContent``
      descendants are deep-copied as-is.
    - ``nodes.transition`` and ``nodes.target`` are skipped — they are structural
      markup (horizontal rules and RST label anchors) that carry no readable
      content and would otherwise be duplicated across every combo section.
    """
    for child in children:
        if isinstance(child, _SELECTOR_UI):
            continue
        if isinstance(child, (nodes.transition, nodes.target)):
            continue
        if isinstance(child, SelectedContent):
            if child.get("no-pdf"):
                continue
            show_cond = child.get("show-cond", "")
            if show_cond and not _matches(show_cond, combo):
                continue
            heading = child.get("heading", "")
            if heading:
                inner: list[nodes.Node] = []
                _gather_content(child.children, combo, inner, id_prefix)
                if inner:
                    sec_id = _make_pdf_id(id_prefix, heading)
                    section = nodes.section(ids=[sec_id], names=[sec_id])
                    section += nodes.title(text=heading)
                    for item in inner:
                        section += item
                    into.append(section)
            else:
                _gather_content(child.children, combo, into, id_prefix)
        elif isinstance(child, nodes.section):
            # Step section (e.g. Prerequisites, Installation): recurse and rebuild
            # with only the filtered content so unmatched variants are dropped.
            title_node = next(
                (c for c in child.children if isinstance(c, nodes.title)), None
            )
            non_title = [
                c for c in child.children if not isinstance(c, nodes.title)
            ]
            inner = []
            _gather_content(non_title, combo, inner, id_prefix)
            if inner:
                step_title = title_node.astext() if title_node else ""
                sec_id = _make_pdf_id(id_prefix, step_title)
                new_section = nodes.section(ids=[sec_id], names=[sec_id])
                if title_node:
                    new_section += title_node.deepcopy()
                for item in inner:
                    new_section += item
                into.append(new_section)
        elif type(child).__name__ == "CustomTable":
            # A matrix table: filter its rows/cells by show-cond for this combo
            # (JavaScript does this in HTML; the PDF has no JS). Keep the custom
            # node type intact — MatrixToTableTransform converts it to a docutils
            # table later.
            into.append(_filter_matrix(child, combo, id_prefix))
        elif list(child.findall(SelectedContent)):
            # Container (e.g. dropdown/admonition) wrapping SelectedContent nodes.
            # Deep-copy the container then replace its children with the filtered set
            # so that conditional content inside it is properly pruned.
            new_node = child.deepcopy()
            filtered: list[nodes.Node] = []
            _gather_content(child.children, combo, filtered, id_prefix)
            new_node.children = []
            for c in filtered:
                c.parent = new_node
                new_node.children.append(c)
            if new_node.children:
                into.append(new_node)
        else:
            into.append(child.deepcopy())


def _collect_selector_options(
    chapter: nodes.Node,
) -> dict[str, list[tuple[str, str, str]]]:
    """Scan the chapter for SelectorGroup/SelectorOption nodes and return options.

    Returns ``{key: [(value, label, group_show_cond)]}`` with values deduplicated in
    document order.  ``group_show_cond`` is the parent SelectorGroup's
    ``show-cond`` so callers can filter options by the active combo.
    """
    opts: dict[str, list[tuple[str, str, str]]] = {}
    seen: dict[str, set[str]] = {}  # key → set of values already added
    for sg in chapter.findall(SelectorGroup):
        key = sg.get("key", "")
        if not key:
            continue
        if key not in opts:
            opts[key] = []
            seen[key] = set()
        group_show_cond = sg.get("show-cond", "")
        for opt in sg.findall(SelectorOption):
            val = opt.get("value", "")
            label = opt.get("label", val)
            if val and val not in seen[key]:
                opts[key].append((val, label, group_show_cond))
                seen[key].add(val)
    return opts


def _get_primary_keys(
    sel_opts: dict[str, list[tuple[str, str, str]]],
) -> list[str]:
    """Return selector keys in document order, excluding version sub-keys.

    A key is a version sub-key when its name is ``{val}-ver`` for some value
    ``val`` that appears in any other key's option list.  Version sub-keys are
    iterated as an extra level nested *under* the parent value by
    ``_iter_combos`` rather than as independent top-level dimensions.
    """
    all_values = {val for entries in sel_opts.values() for val, _, _ in entries}
    return [
        k for k in sel_opts if not (k.endswith("-ver") and k[:-4] in all_values)
    ]


def _iter_combos(
    remaining_keys: list[str],
    sel_opts: dict[str, list[tuple[str, str, str]]],
    combo: dict[str, str],
    labels: dict[str, str],
    out: list[tuple[dict[str, str], dict[str, str]]],
) -> None:
    """Recursively build (combo, labels) pairs for every primary-key combination.

    For each primary key K with current value V, if ``V-ver`` is also present
    in *sel_opts* its entries are iterated as a nested version level immediately
    after V — so the section hierarchy mirrors the RST structure exactly.

    When multiple option groups expose the same value (e.g. the same
    install-method under different OSes), the label whose group ``show-cond``
    best matches the partial combo built so far is chosen.
    """
    if not remaining_keys:
        out.append((dict(combo), dict(labels)))
        return

    key = remaining_keys[0]
    rest = remaining_keys[1:]
    entries = sel_opts.get(key, [])

    # Unique values in document order; collect all (label, group_cond) per value.
    val_label_options: dict[str, list[tuple[str, str]]] = {}
    vals_ordered: list[str] = []
    seen_vals: set[str] = set()
    for val, label, group_cond in entries:
        if val not in seen_vals:
            vals_ordered.append(val)
            seen_vals.add(val)
        val_label_options.setdefault(val, []).append((label, group_cond))

    for val in vals_ordered:
        # Pick the label whose group show-cond best matches the partial combo.
        best_label = val_label_options[val][0][0]
        for lbl, group_cond in val_label_options[val]:
            if _matches(group_cond, combo):
                best_label = lbl
                break

        combo[key] = val
        labels[key] = best_label

        # If a version sub-key exists for this value, iterate its entries
        # as an extra nested level before recursing into remaining_keys.
        ver_key = f"{val}-ver"
        ver_entries = sel_opts.get(ver_key, [])
        if ver_entries:
            for ver_val, ver_label, _ in ver_entries:
                combo[ver_key] = ver_val
                labels[ver_key] = ver_label
                _iter_combos(rest, sel_opts, combo, labels, out)
            del combo[ver_key]
            del labels[ver_key]
        else:
            _iter_combos(rest, sel_opts, combo, labels, out)

        del combo[key]
        del labels[key]


def _build_combos(
    sel_opts: dict[str, list[tuple[str, str, str]]],
) -> list[tuple[dict[str, str], dict[str, str]]]:
    """Build the ordered list of (combo_dict, labels_dict) from selector options.

    Primary keys (those that are not ``{value}-ver`` sub-keys) are iterated in
    document order.  For any primary-key value V that has a corresponding
    ``V-ver`` key in *sel_opts*, that version key's values are inserted as an
    extra level immediately after V.

    Labels are resolved by matching each option group's ``show-cond`` against
    the partial combo at the time the label is needed, so context-dependent
    labels (e.g. ``apt`` vs ``dnf`` for the same install-method value) are
    picked correctly without any hardcoded key names.
    """
    primary_keys = _get_primary_keys(sel_opts)
    combos: list[tuple[dict[str, str], dict[str, str]]] = []
    _iter_combos(primary_keys, sel_opts, {}, {}, combos)
    return combos


def _combo_matches_spec(combo: dict[str, str], spec: dict[str, str]) -> bool:
    """Return True if *combo* satisfies every key in *spec* (a partial match).

    Keys absent from *spec* act as wildcards. Keys and values are normalized so
    specs can be written naturally (e.g. ``"Ubuntu"`` matches ``"ubuntu"``).
    Version sub-keys must be specified by their full name (e.g. ``ubuntu-ver``).
    """
    for raw_key, raw_val in spec.items():
        key = normalize_key(str(raw_key))
        want = normalize_key(str(raw_val))
        if key not in combo:
            return False
        if normalize_key(str(combo[key])) != want:
            return False
    return True


def _filter_combos_for_pdf(
    all_combos: list[tuple[dict[str, str], dict[str, str]]], specs: list[object]
) -> list[tuple[dict[str, str], dict[str, str]]]:
    """Keep only combos matching at least one spec dict in *specs*.

    Each entry of *specs* must be a dict of ``{dimension: value}`` constraints.
    Non-dict entries are ignored with a warning so a malformed config value
    degrades to "match nothing extra" rather than crashing the build.
    """
    valid_specs = []
    for spec in specs:
        if isinstance(spec, dict):
            valid_specs.append(spec)
        else:
            logger.warning(
                "rocm_selector_pdf_generation list entries must be dicts, "
                "got %r; ignoring it.",
                spec,
            )

    # Warn about spec keys that don't exist in any combo so users can spot
    # typos or incorrect dimension names early (e.g. "ver" vs "ubuntu-ver").
    if valid_specs and all_combos:
        known_keys = set(all_combos[0][0].keys())
        for spec in valid_specs:
            for raw_key in spec:
                if normalize_key(str(raw_key)) not in known_keys:
                    logger.warning(
                        "rocm_selector_pdf_generation: spec key %r does not "
                        "match any combo dimension; available dimensions: %s. "
                        "Version sub-keys use the format '<os>-ver' "
                        "(e.g. 'ubuntu-ver', not 'ver').",
                        raw_key,
                        sorted(known_keys),
                    )

    return [
        (combo, labels)
        for combo, labels in all_combos
        if any(_combo_matches_spec(combo, spec) for spec in valid_specs)
    ]


class SelectorPDFReorganizeTransform(SphinxPostTransform):
    """Reorganize selector-driven pages for PDF/LaTeX output.

    In HTML the selector widgets let users pick their configuration and see
    only the relevant content.  In a PDF that interactivity is lost, so the
    document is restructured: for every valid combination of selector values
    a dedicated section hierarchy is produced

        <key1 value> → <key2 value> → … → full guide

    so a reader can find the complete instructions for their setup in one
    place rather than scanning through all possible variants mixed together.
    The key order and names are discovered dynamically from the doctree.

    The transform only runs for the LaTeX builder and only when the page
    contains enough ``SelectedContent`` nodes to be worth reorganising
    (threshold: ≥ 10 nodes).
    """

    default_priority = 488  # before SelectorToSectionTransform (490)

    def apply(self, **_kwargs):
        """Reorganize the install chapter into per-combo sections for PDF output."""
        if self.app.builder.format != "latex":
            return

        # PDF generation disabled: skip the per-combo install-page reorganization.
        if not self.config.rocm_selector_pdf_generation:
            return

        all_selected = list(self.document.findall(SelectedContent))
        if len(all_selected) < 10:
            return

        # In the LaTeX builder, post-transforms run on the assembled mega-doctree
        # (all pages inlined).  Each sub-document's sections are tagged with
        # docname='install/rocm' by inline_all_toctrees, so locate the right one.
        chapter = None
        for sec in self.document.findall(nodes.section):
            if sec.get("docname") == "install/rocm":
                chapter = sec
                break

        if chapter is None:
            # Fallback for single-document builds where docname tags may be absent.
            chapter = next(
                (
                    n
                    for n in self.document.children
                    if isinstance(n, nodes.section)
                ),
                None,
            )

        if chapter is None:
            return

        # ------------------------------------------------------------------
        # Preserve the preamble: the chapter title and any non-selector,
        # non-section nodes before the first SelectedContent.
        # ------------------------------------------------------------------
        preamble = []
        first_selected_idx = None
        for i, child in enumerate(chapter.children):
            if isinstance(child, SelectedContent):
                first_selected_idx = i
                break
            if isinstance(child, _SELECTOR_UI):
                continue
            preamble.append(child.deepcopy())

        if first_selected_idx is None:
            return

        # Source pool: chapter children from the first SelectedContent onwards.
        # Everything before that index is already captured in the preamble and
        # must not be repeated inside every per-combo section.
        source_children = chapter.children[first_selected_idx:]

        # ------------------------------------------------------------------
        # Discover selector options from the doctree (no hardcoded arrays).
        # ------------------------------------------------------------------
        sel_opts = _collect_selector_options(chapter)
        all_combos = _build_combos(sel_opts)

        # Tri-state rocm_selector_pdf_generation: a list value restricts output
        # to the combos matching one of its spec dicts. (True generates all;
        # False never reaches here — the early-return guard above handles it.)
        pdf_setting = self.config.rocm_selector_pdf_generation
        if isinstance(pdf_setting, list):
            total = len(all_combos)
            if all_combos:
                logger.info(
                    "rocm_selector_pdf_generation: available combo "
                    "dimensions: %s",
                    sorted(all_combos[0][0].keys()),
                )
            all_combos = _filter_combos_for_pdf(all_combos, pdf_setting)
            logger.info(
                "rocm_selector_pdf_generation filter: keeping %d of %d install "
                "combinations for PDF.",
                len(all_combos),
                total,
            )
            if not all_combos:
                logger.warning(
                    "rocm_selector_pdf_generation filter matched no install "
                    "combinations; the install chapter will contain only its "
                    "preamble. Check the dimension names/values in the filter."
                )

        # ------------------------------------------------------------------
        # Build the new chapter contents: preamble + per-combo sections.
        #
        # The section hierarchy mirrors the selector key order discovered in
        # the doctree.  Each combo produces a path of (key, val) pairs; a
        # section is created for each step of the path on first encounter.
        # After all combos are processed, sections are connected bottom-up
        # so that only paths with actual content make it into the output.
        # ------------------------------------------------------------------
        new_children = list(preamble)
        primary_keys = _get_primary_keys(sel_opts)

        # path_sections: tuple of (key, val) pairs → section node
        path_sections: dict[tuple[tuple[str, str], ...], nodes.section] = {}
        # paths that received content (directly or via a descendant)
        path_has_content: set[tuple[tuple[str, str], ...]] = set()

        for combo, labels in all_combos:
            # Build the ordered section path for this combo:
            # primary keys in document order, with {val}-ver inserted after
            # each primary value that has a version sub-key.
            path: list[tuple[str, str, str]] = []
            for pk in primary_keys:
                if pk not in combo:
                    continue
                val = combo[pk]
                path.append((pk, val, labels.get(pk, val)))
                ver_key = f"{val}-ver"
                if ver_key in combo:
                    path.append(
                        (
                            ver_key,
                            combo[ver_key],
                            labels.get(ver_key, combo[ver_key]),
                        )
                    )

            id_prefix = _make_pdf_id(*[val for _, val, _ in path])
            content_nodes: list[nodes.Node] = []
            _gather_content(source_children, combo, content_nodes, id_prefix)

            if not content_nodes:
                continue

            # Create sections along the path (on first encounter).
            for depth in range(len(path)):
                path_key = tuple((k, v) for k, v, _ in path[: depth + 1])
                if path_key not in path_sections:
                    _, _, lbl = path[depth]
                    sec_id = _make_pdf_id("pdf", *[v for _, v in path_key])
                    sec = nodes.section(ids=[sec_id], names=[sec_id])
                    sec += nodes.title(text=lbl)
                    path_sections[path_key] = sec

            # Attach content to the innermost section.
            innermost = tuple((k, v) for k, v, _ in path)
            for n in content_nodes:
                path_sections[innermost] += n

            # Mark every ancestor path as having content.
            for depth in range(len(path)):
                path_has_content.add(
                    tuple((k, v) for k, v, _ in path[: depth + 1])
                )

        # Connect sections bottom-up (deepest first) and collect top-level ones.
        for path_key in sorted(path_sections, key=len, reverse=True):
            if path_key not in path_has_content:
                continue
            if len(path_key) == 1:
                new_children.append(path_sections[path_key])
            else:
                parent_key = path_key[:-1]
                if parent_key in path_sections:
                    path_sections[parent_key] += path_sections[path_key]

        # ------------------------------------------------------------------
        # Replace the chapter's children with the reorganised content.
        # ------------------------------------------------------------------
        chapter.children = []
        for child in new_children:
            child.parent = chapter
            chapter += child

        # IDs built by _make_pdf_id are combo-derived and never registered with
        # the document, so a heading repeated across combos (e.g. a shared
        # "Prerequisites" step) yields duplicate section IDs. Reassign every new
        # section a document-unique ID so PDF/HTML cross-references resolve to
        # the correct target.
        for section in chapter.findall(nodes.section):
            old_ids = section["ids"]
            base = (
                old_ids[0] if old_ids else (section.get("names") or ["sec"])[0]
            )
            unique = make_unique_id(self.document, base)
            section["ids"] = [unique]
            section["names"] = [unique]


class SelectorToSectionTransform(SphinxPostTransform):
    """Convert SelectedContent nodes to proper docutils structures for non-HTML builders.

    In HTML, SelectedContent nodes render as conditional show/hide sections driven
    by JavaScript. In static formats (LaTeX/PDF, text, man) there is no interactivity,
    so all content must be visible. This transform runs before the LaTeX translator:

    - Nodes with a ``:heading:`` option become proper docutils ``section`` nodes so
      that headings appear correctly in the PDF table of contents and body text.
    - Nodes without a heading are unwrapped in place — their children are spliced
      directly into the parent so all condition variants render sequentially, which
      is correct behaviour for a static format.

    The HTML path is untouched: the transform exits immediately for HTML builds.
    The Markdown path (llms-full.txt) is also left untouched — it runs under the
    HTML builder and renders SelectedContent via the dedicated Markdown node
    handler instead.
    """

    default_priority = 490  # run before MatrixToTableTransform (500)

    def apply(self, **_kwargs):
        """Convert SelectedContent nodes to docutils sections for non-HTML builders."""
        if self.app.builder.format == "html":
            return

        # PDF generation disabled: skip converting SelectedContent for LaTeX.
        # The nodes' latex visitors are no-ops, so the conditional content is
        # simply omitted from the PDF. Other non-HTML builders still convert.
        if (
            self.app.builder.format == "latex"
            and not self.config.rocm_selector_pdf_generation
        ):
            return

        # Collect upfront so that replacing nodes mid-traversal is safe.
        for node in list(self.document.findall(SelectedContent)):
            if node.parent is None:
                continue  # already detached by a parent replacement

            heading = node.get("heading", "")

            if heading:
                # Replace with a proper section so the heading appears in the PDF.
                # Headings repeat across conditional blocks (e.g. "Prerequisites"
                # under each OS), so the ID must be deduplicated against the
                # document or cross-references collapse onto the first match.
                sec_id = make_unique_id(self.document, heading)
                section = nodes.section(ids=[sec_id], names=[sec_id])
                section += nodes.title(text=heading)
                for child in node.children[:]:
                    section += child
                node.replace_self(section)
            else:
                # No heading — splice children directly into the parent so the
                # SelectedContent wrapper disappears without dropping any content.
                # replace_self routes through Element.replace, which reparents
                # each spliced child (sets .parent/.document); a raw children
                # slice assignment would leave them pointing at the detached
                # wrapper and corrupt later transforms/translators.
                node.replace_self(node.children[:])
