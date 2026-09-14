"""Branch-aware ``remote-content`` Sphinx directive.

Downloads an ``.rst`` file from another GitHub repository at a branch or tag
matching the current documentation build, then inlines it. Along the way it can
rewrite ``:doc:`` roles to external URLs, remap or ignore selected doc links,
download referenced images, apply text and regex replacements, add widths to
CSV tables, and fix common LaTeX math issues.

This is the canonical implementation, consolidated from copies that had been
duplicated (and diverged) across ROCm documentation repositories. Enable it by
adding ``"rocm_docs.remote_content"`` to ``extensions`` in ``conf.py``.
"""

from __future__ import annotations

from typing import Any

import os
import re
from pathlib import Path

import requests
import sphinx.util.logging
from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import StringList
from sphinx.application import Sphinx
from sphinx.util.nodes import nested_parse_with_titles

logger = sphinx.util.logging.getLogger(__name__)

CONFIG_DOCS_BASE = "rocm_docs_remote_content_docs_base"
DEFAULT_DOCS_BASE = "https://rocm.docs.amd.com/projects"


class BranchAwareRemoteContent(Directive):
    """Include RST content from another repo at the matching branch/tag.

    Usage::

        .. remote-content::
           :repo: owner/repository
           :path: path/to/file.rst
           :default_branch: docs/develop  # Branch to use when not on a release
           :tag_prefix: docs/  # Optional
           :replace: old1|new1;; old2|new2
           :project_name: ProjectName  # Optional override for URL construction
           :docs_base_url: https://rocm.docs.amd.com/projects  # Optional
           :doc_ignore: path/to/ignore;; another/path
           :doc_remap: remote/path|local/path;; remote/path2|New Text|local/path2

    The ``:replace:`` option uses ``|`` to separate old and new text, and ``;;``
    to separate multiple replacements. ``:doc_ignore:`` uses ``;;`` to separate
    paths left unconverted. ``:doc_remap:`` remaps ``:doc:`` links to local
    paths, in the format ``old_path|new_path`` (keeps display text) or
    ``old_path|new_display_text|new_path``.
    """

    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = True
    has_content = False
    option_spec = {  # noqa: RUF012
        "repo": str,
        "path": str,
        "default_branch": str,  # Branch to use when not on a release tag
        "start_line": int,  # Include the file from a specific line
        "tag_prefix": str,  # Prefix for release tags (e.g., 'docs/')
        "replace": str,  # Text replacement "old|new" (;; separates multiple)
        "project_name": str,  # Override project name for URL construction
        "docs_base_url": str,  # Override base URL for documentation
        "doc_ignore": str,  # Doc links to leave unconverted (;; separated)
        "doc_remap": str,  # Remap doc links to local paths (;; separated)
        "csv_widths": str,  # Add widths to CSV tables (e.g., "33 67")
        "fix_latex_math": str,  # Enable LaTeX math fixes (true/false)
        "replace_re": str,  # Regex replacements "pattern|replacement" (;; sep)
    }

    def get_current_version(self) -> str | None:
        """Return the version being built if this is a release build."""
        env = self.state.document.settings.env
        html_context = env.config.html_context

        version = html_context.get("version", "")
        if not re.match(r"^\d+\.\d+\.\d+$", version):
            return None

        # Detect a release build in order of reliability:
        # 1. Local: building from a docs/ branch (official_branch == 0).
        # 2. Read the Docs tag build: READTHEDOCS_VERSION_TYPE is "tag".
        # 3. Read the Docs tag build (fallback): the version number appears
        #    in the READTHEDOCS_VERSION slug (e.g. "docs-7.13.0" contains
        #    "7.13.0"). This handles environments where VERSION_TYPE is unset.
        rtd_version_slug = os.environ.get("READTHEDOCS_VERSION", "")
        is_release = (
            html_context.get("official_branch") == 0
            or os.environ.get("READTHEDOCS_VERSION_TYPE") == "tag"
            or (bool(rtd_version_slug) and version in rtd_version_slug)
        )

        if is_release:
            return str(version)
        return None

    def get_target_ref(self) -> str | None:
        """Return the git ref (tag or branch) to fetch content from."""
        current_version = self.get_current_version()

        # If it's a version number, use tag prefix and version
        if current_version:
            tag_prefix = self.options.get("tag_prefix", "")
            return f"{tag_prefix}{current_version}"

        # For any other case, use the specified default branch
        if "default_branch" not in self.options:
            logger.warning(
                "No default_branch specified and not building from a version "
                "tag"
            )
            return None

        return str(self.options["default_branch"])

    def get_project_name(self) -> str:
        """Return the project name used when constructing doc URLs."""
        if "project_name" in self.options:
            return str(self.options["project_name"])

        # Parse from repo: "ROCm/HIP" -> "HIP"
        repo = self.options.get("repo", "")
        if "/" in repo:
            return str(repo.split("/")[-1])

        return str(repo)

    def get_ignored_doc_paths(self) -> list[str]:
        """Return the list of doc paths that should not be converted."""
        if "doc_ignore" not in self.options:
            return []

        ignored_paths = self.options["doc_ignore"].split(";;")
        return [path.strip() for path in ignored_paths if path.strip()]

    def get_doc_remaps(self) -> list[tuple[str, str | None, str]]:
        """Return doc path remappings as ``(old, display_or_None, new)``."""
        if "doc_remap" not in self.options:
            return []

        remap_specs = self.options["doc_remap"].split(";;")

        remaps: list[tuple[str, str | None, str]] = []
        for raw_spec in remap_specs:
            remap_spec = raw_spec.strip()
            if not remap_spec:
                continue

            if "|" not in remap_spec:
                logger.warning(
                    'doc_remap option must be in format "old_path|new_path" '
                    'or "old_path|new_text|new_path", got: "%s"',
                    remap_spec,
                )
                continue

            parts = remap_spec.split("|")

            if len(parts) == 2:
                # Format: old_path|new_path (keep original display text)
                remaps.append((parts[0].strip(), None, parts[1].strip()))
            elif len(parts) == 3:
                # Format: old_path|new_display_text|new_path
                remaps.append(
                    (parts[0].strip(), parts[1].strip(), parts[2].strip())
                )
            else:
                logger.warning(
                    "doc_remap option has too many parts (expected 2 or 3, "
                    'got %d): "%s"',
                    len(parts),
                    remap_spec,
                )

        return remaps

    def get_docs_base_url(self) -> str:
        """Return the base URL used to build external documentation links."""
        if "docs_base_url" in self.options:
            return str(self.options["docs_base_url"])

        env = self.state.document.settings.env
        base = getattr(env.config, CONFIG_DOCS_BASE, "")
        if base:
            return str(base)

        return DEFAULT_DOCS_BASE

    def construct_raw_url(self, repo: str, path: str, ref: str) -> str:
        """Return the ``raw.githubusercontent.com`` URL for a repo file."""
        return f"https://raw.githubusercontent.com/{repo}/{ref}/{path}"

    def construct_doc_url(self, doc_path: str, ref: str) -> str:
        """Return the external documentation URL for a ``:doc:`` target."""
        base_url = self.get_docs_base_url()
        project_name = self.get_project_name()

        if doc_path.endswith(".rst"):
            doc_path = doc_path[:-4]

        # Remove leading slash to avoid double slashes in URL
        doc_path = doc_path.lstrip("/")

        # Special case: main ROCm docs don't use /projects/ structure
        if self.options.get("repo") == "ROCm/ROCm":
            return f"https://rocm.docs.amd.com/en/{ref}/{doc_path}.html"
        # Standard project pattern: domain/projects/name/en/ref/path
        return f"{base_url}/{project_name}/en/{ref}/{doc_path}.html"

    def resolve_relative_doc_path(
        self, doc_path: str, source_file_path: str
    ) -> str:
        """Resolve a relative ``:doc:`` target against its source file."""
        if not doc_path.startswith("./") and not doc_path.startswith("../"):
            return doc_path

        source_dir = Path(source_file_path).parent
        resolved_path = (source_dir / doc_path).as_posix()
        return str(Path(resolved_path))

    def process_doc_roles(self, content: str, ref: str) -> str:
        """Convert or remap ``:doc:`` roles in the fetched content."""
        ignored_paths = self.get_ignored_doc_paths()
        doc_remaps = self.get_doc_remaps()

        # Matches both :doc:`target` and :doc:`text <target>`.
        doc_pattern = r":doc:`([^`]+)`"

        def replace_doc_role(match: re.Match[str]) -> str:
            full_content = match.group(1)

            # Parse the display text and target ("text <target>" or "target").
            if "<" in full_content and ">" in full_content:
                text_match = re.match(r"(.+?)\s*<(.+?)>", full_content)
                if text_match:
                    display_text = text_match.group(1).strip()
                    target = text_match.group(2).strip()
                else:
                    display_text = full_content
                    target = full_content
            else:
                target = full_content.strip()
                display_text = target

            is_namespaced = ":" in target

            # Ignore (leave unconverted) if requested.
            if target in ignored_paths:
                logger.info("Ignoring doc link as requested: %s", target)
                return match.group(0)

            target_stripped = target.lstrip("/")
            if target_stripped in ignored_paths:
                logger.info("Ignoring doc link as requested: %s", target)
                return match.group(0)

            # Remap to a local :doc: role if requested.
            for old_path, new_display_text, new_path in doc_remaps:
                if target == old_path or target_stripped == old_path:
                    if new_display_text is not None:
                        final_display_text = new_display_text
                    else:
                        final_display_text = display_text

                    if final_display_text == new_path:
                        result = f":doc:`{new_path}`"
                    else:
                        result = f":doc:`{final_display_text} <{new_path}>`"

                    logger.info(
                        "Remapped :doc:`%s` to %s", full_content, result
                    )
                    return result

            # Leave namespaced references for intersphinx to handle.
            if is_namespaced:
                logger.debug(
                    "Skipping namespaced doc reference (no remap match): %s",
                    full_content,
                )
                return match.group(0)

            resolved_target = self.resolve_relative_doc_path(
                target, self.options["path"]
            )
            url = self.construct_doc_url(resolved_target, ref)
            logger.info(
                "Converted :doc:`%s` to external link: %s", full_content, url
            )
            return f"`{display_text} <{url}>`__"

        return re.sub(doc_pattern, replace_doc_role, content)

    def process_csv_tables(self, content: str) -> str:
        """Inject ``:widths:`` into CSV tables when ``csv_widths`` is set."""
        if "csv_widths" not in self.options:
            return content

        csv_widths = self.options["csv_widths"].strip()
        if not csv_widths:
            return content

        # Match CSV table directives with their options (RST indentation).
        csv_pattern = re.compile(
            r"^(\s*)\.\. csv-table::.*?\n" r"((?:\s+:[^:]+:.*\n)*)",
            re.MULTILINE,
        )

        def add_widths_to_csv(match: re.Match[str]) -> str:
            indent = match.group(1)
            existing_options = match.group(2)

            if ":widths:" in existing_options:
                return match.group(0)

            header_pattern = re.compile(r"^(\s+):header:.*\n", re.MULTILINE)
            header_match = header_pattern.search(existing_options)

            if header_match:
                option_indent = header_match.group(1)
                widths_line = f"{option_indent}:widths: {csv_widths}\n"
                modified_options = (
                    existing_options[: header_match.end()]
                    + widths_line
                    + existing_options[header_match.end() :]
                )
                logger.info("Added :widths: %s to CSV table", csv_widths)
                return f"{indent}.. csv-table::\n{modified_options}"
            if existing_options:
                first_option_match = re.match(r"^(\s+):", existing_options)
                if first_option_match:
                    option_indent = first_option_match.group(1)
                    widths_line = f"{option_indent}:widths: {csv_widths}\n"
                    logger.info("Added :widths: %s to CSV table", csv_widths)
                    return (
                        f"{indent}.. csv-table::\n"
                        f"{widths_line}{existing_options}"
                    )
            else:
                # No existing options: 3-space RST option indentation.
                widths_line = f"   :widths: {csv_widths}\n"
                logger.info("Added :widths: %s to CSV table", csv_widths)
                return f"{indent}.. csv-table::\n{widths_line}"

            return match.group(0)

        return csv_pattern.sub(add_widths_to_csv, content)

    def process_latex_math(self, content: str) -> str:
        r"""Escape underscores inside ``\text{}`` when enabled."""
        if "fix_latex_math" not in self.options:
            return content

        fix_latex = self.options.get("fix_latex_math", "").strip().lower()
        if fix_latex not in ("true", "1", "yes"):
            return content

        def escape_underscores_in_text(match: re.Match[str]) -> str:
            text_content = match.group(1)
            escaped_content = re.sub(r"(?<!\\)_", r"\\_", text_content)
            if escaped_content != text_content:
                logger.info(
                    "Fixed underscores in \\text{%s} -> \\text{%s}",
                    text_content,
                    escaped_content,
                )
            return f"\\text{{{escaped_content}}}"

        # Match \text{} with one level of nested braces.
        text_pattern = r"\\text\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"
        modified_content = re.sub(
            text_pattern, escape_underscores_in_text, content
        )

        if modified_content != content:
            logger.info("Applied LaTeX math fixes")

        return modified_content

    def apply_regex_replacements(self, content: str) -> str:
        """Apply ``replace_re`` regex substitutions (multi-line aware)."""
        if "replace_re" not in self.options:
            return content

        for raw_spec in self.options["replace_re"].split(";;"):
            spec = raw_spec.strip()
            if not spec:
                continue
            if "|" not in spec:
                logger.warning(
                    "replace_re option must be in format "
                    '"pattern|replacement", got: "%s"',
                    spec,
                )
                continue
            pattern, replacement = spec.split("|", 1)
            replacement = replacement.replace("\\n", "\n")
            modified = re.sub(pattern, replacement, content, flags=re.DOTALL)
            if modified != content:
                logger.info("replace_re matched pattern: %s", pattern)
                content = modified
        return content

    def apply_replacements(self, content: str) -> str:
        """Apply literal ``replace`` text substitutions."""
        if "replace" not in self.options:
            return content

        replace_specs = self.options["replace"].split(";;")

        for raw_spec in replace_specs:
            replace_spec = raw_spec.strip()
            if not replace_spec:
                continue

            if "|" not in replace_spec:
                logger.warning(
                    'Replace option must be in format "old_text|new_text", '
                    'got: "%s"',
                    replace_spec,
                )
                continue

            old_text, new_text = replace_spec.split("|", 1)
            modified_content = content.replace(old_text, new_text)
            if modified_content != content:
                logger.info('Replaced "%s" with "%s"', old_text, new_text)
                content = modified_content

        return content

    def get_image_cache_dir(self) -> Path:
        """Return (creating if needed) the cache dir for remote images."""
        env = self.state.document.settings.env
        srcdir = Path(str(env.srcdir))
        repo_dir = str(self.options["repo"]).replace("/", "_")
        cache_dir = srcdir / "_remote_images" / repo_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def download_image(self, image_path: str, ref: str) -> Path | None:
        """Download a single referenced image, returning its local path."""
        image_url = self.construct_raw_url(
            self.options["repo"], image_path, ref
        )

        try:
            logger.info("Downloading image from %s", image_url)
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            cache_dir = self.get_image_cache_dir()

            # Drop a leading 'docs/' segment; we handle that separately.
            save_path = Path(image_path)
            if save_path.parts and save_path.parts[0] == "docs":
                save_path = Path(*save_path.parts[1:])

            local_image_path = cache_dir / save_path
            local_image_path.parent.mkdir(parents=True, exist_ok=True)
            local_image_path.write_bytes(response.content)
            logger.info("Saved image to %s", local_image_path)
            return local_image_path
        except requests.exceptions.RequestException as error:
            logger.warning(
                "Failed to download image from %s: %s", image_url, error
            )
            return None

    def _resolve_image_path(self, original_uri: str) -> str:
        """Resolve an image URI to a repo-relative path for downloading."""
        source_path = Path(self.options["path"])
        source_dir = source_path.parent
        repo = self.options.get("repo", "")

        if source_dir.as_posix() and source_dir.as_posix() != ".":
            joined_path = (source_dir / original_uri).as_posix()
            image_path = os.path.normpath(joined_path).replace("\\", "/")

            if repo == "ROCm/rocm-systems":
                # In the rocm-systems monorepo, component docs live under
                # projects/<component>/docs/. Derive that base from the source
                # path so images resolve for every component, and strip any
                # leading ../ that would escape the component directory.
                base = ""
                parts = source_path.as_posix().split("/")
                if (
                    len(parts) >= 3
                    and parts[0] == "projects"
                    and parts[2] == "docs"
                ):
                    base = f"projects/{parts[1]}/docs"
                if base:
                    rest_of_path = original_uri.replace("\\", "/")
                    while rest_of_path.startswith(("../", "./")):
                        rest_of_path = rest_of_path.split("/", 1)[1]
                    rest_of_path = rest_of_path.lstrip("/")
                    image_path = f"{base}/{rest_of_path}"
            elif repo in ("ROCm/ROCm", "ROCm/rccl"):
                if image_path.startswith("../"):
                    image_path = f"docs/{image_path[3:]}"
                elif not image_path.startswith("docs/"):
                    image_path = f"docs/{image_path}"
        else:
            image_path = original_uri
            if repo == "ROCm/rocm-systems" and not image_path.startswith(
                "projects/"
            ):
                image_path = f"projects/hip/docs/{image_path}"
            elif repo in (
                "ROCm/ROCm",
                "ROCm/rccl",
            ) and not image_path.startswith("docs/"):
                image_path = f"docs/{image_path}"

        # Final normalization to remove any remaining ../ components.
        image_path = os.path.normpath(image_path).replace("\\", "/")
        return image_path.lstrip("/")

    def process_image_nodes(self, node: nodes.Node, ref: str) -> None:
        """Download images referenced in the parsed content and repoint them."""
        srcdir = Path(str(self.state.document.settings.env.srcdir))
        for img_node in node.findall(nodes.image):
            original_uri = img_node.get("uri", "")

            # Skip absolute URLs and source-root-absolute paths.
            if original_uri.startswith(("http://", "https://", "/")):
                continue

            image_path = self._resolve_image_path(original_uri)
            logger.info("Processing image: %s -> %s", original_uri, image_path)

            local_image_path = self.download_image(image_path, ref)
            if local_image_path:
                try:
                    rel_path = local_image_path.relative_to(srcdir)
                    # Absolute-from-source-root path so Sphinx always finds it.
                    new_path = "/" + str(rel_path.as_posix())
                except ValueError:
                    new_path = str(local_image_path.as_posix())

                img_node["uri"] = new_path
                logger.info(
                    "Updated image URI: %s -> %s", original_uri, new_path
                )
            else:
                logger.warning(
                    "Keeping original image path due to download failure: %s",
                    original_uri,
                )

    def fetch_and_parse_content(
        self, url: str, source_path: str, ref: str
    ) -> list[nodes.Node]:
        """Fetch remote RST, apply transforms, and parse it into nodes."""
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content = response.text

        # Normalize tabs after numbered list markers to spaces.
        content = re.sub(r"^(\s*\d+\.)\t+", r"\1 ", content, flags=re.MULTILINE)

        content = self.apply_replacements(content)
        content = self.apply_regex_replacements(content)
        content = self.process_latex_math(content)
        content = self.process_csv_tables(content)
        content = self.process_doc_roles(content, ref)

        start_line = self.options.get("start_line", 0)

        # Compute the source path relative to Sphinx's srcdir so that
        # directives like ``.. raw:: html :file: data/foo.html`` resolve
        # correctly. The remote :path: includes the repo's docs/ prefix
        # (e.g. "docs/index.rst"); locally srcdir IS the docs/ directory, so
        # stripping that first segment gives a path whose parent matches srcdir.
        env = self.state.document.settings.env
        srcdir = Path(str(env.srcdir))
        remote_path = Path(source_path)
        try:
            rel_source_path = str(remote_path.relative_to(remote_path.parts[0]))
        except (ValueError, IndexError):
            rel_source_path = source_path
        viewlist_source = str(srcdir / rel_source_path)

        content_list = StringList()
        for line_no, line in enumerate(content.splitlines()):
            if line_no >= start_line:
                content_list.append(line, viewlist_source, line_no)

        node = nodes.section()
        nested_parse_with_titles(self.state, content_list, node)

        # Download images after parsing and repoint their URIs.
        self.process_image_nodes(node, ref)

        return list(node.children)

    def run(self) -> list[nodes.Node]:
        """Entry point: resolve the ref, fetch, and return parsed nodes."""
        if "repo" not in self.options or "path" not in self.options:
            logger.warning("Both repo and path options are required")
            return []

        target_ref = self.get_target_ref()
        logger.info(
            "Target ref determined: %s for repo: %s",
            target_ref,
            self.options["repo"],
        )
        if not target_ref:
            return []

        raw_url = self.construct_raw_url(
            self.options["repo"], self.options["path"], target_ref
        )

        try:
            logger.info("Attempting to fetch content from %s", raw_url)
            return self.fetch_and_parse_content(
                raw_url, self.options["path"], target_ref
            )
        except requests.exceptions.RequestException as error:
            logger.warning(
                "Failed to fetch content from %s: %s", raw_url, error
            )

            # If we failed on a tag, fall back to default_branch.
            if self.get_current_version() and "default_branch" in self.options:
                fallback_ref = self.options["default_branch"]
                logger.info("Attempting fallback to %s...", fallback_ref)
                try:
                    fallback_url = self.construct_raw_url(
                        self.options["repo"],
                        self.options["path"],
                        fallback_ref,
                    )
                    return self.fetch_and_parse_content(
                        fallback_url, self.options["path"], fallback_ref
                    )
                except requests.exceptions.RequestException as error2:
                    logger.warning("Fallback also failed: %s", error2)

            return []


def setup(app: Sphinx) -> dict[str, Any]:
    """Set up ``rocm_docs.remote_content`` as a Sphinx extension."""
    app.add_directive("remote-content", BranchAwareRemoteContent)
    app.add_config_value(CONFIG_DOCS_BASE, DEFAULT_DOCS_BASE, "html", types=str)

    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
