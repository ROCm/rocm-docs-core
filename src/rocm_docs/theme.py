"""Module to use rocm-docs-core as a theme."""

from typing import Any

from pathlib import Path

import sphinx.util.logging
from pydata_sphinx_theme.utils import (  # type: ignore[import-untyped]
    config_provided_by_user,
    get_theme_options_dict,
)
from sphinx.application import Sphinx

from rocm_docs import common, util

logger = sphinx.util.logging.getLogger(__name__)


def _get_rocm_toolkits(common_dir: str | None = None) -> dict[str, str]:
    """Read rocm_toolkits.txt from the rocm-docs-common checkout."""
    return _parse_rocm_toolkits(
        common.read_common_file("data/rocm_toolkits.txt", common_dir).strip()
    )


def _parse_rocm_toolkits(content: str) -> dict[str, str]:
    """Parse rocm_toolkits.txt (name: url lines) into a dict.

    Splits on the first colon only; the URL value (which also contains
    colons) is captured in full after that first separator.
    Example line: "ROCm Data Science: https://rocm.docs.amd.com/..."
    """
    result: dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        key, sep, value = line.partition(": ")
        if not sep:
            continue
        key = key.strip()
        value = value.strip()
        if key and value:
            result[key] = value
    return result


def _read_common_version(
    relative_path: str, common_dir: str | None = None
) -> str:
    """Read a version data file from the rocm-docs-common checkout."""
    return common.read_common_file(relative_path, common_dir).strip()


def _parse_version(version_string: str) -> dict[str, str]:
    """Parse latest_version.txt and output a dictionary of site_name : latest_version.

    Example:
    {"ROCm": "7.0.2", "AI-Developer-Hub": "v7.0", "ROCm-DS": "25.05"}
    """
    header_latest_version_list = [
        site_version.split(":") for site_version in version_string.split("\n")
    ]
    return {
        site_version_pair[0].strip(): site_version_pair[1].strip()
        for site_version_pair in header_latest_version_list
    }


def _add_custom_context(
    app: Sphinx,
    pagename: str,  # noqa: ARG001
    templatename: str,  # noqa: ARG001
    context: dict[str, str | dict[str, str]],
    doctree: object,  # noqa: ARG001
) -> None:
    common_dir = getattr(app.config, common.COMMON_DIR_CONFIG, None)
    latest_version_list = _read_common_version(
        "data/latest_version.txt", common_dir
    )
    context["header_latest_version"] = _parse_version(latest_version_list)

    header_release_candidate_version = _read_common_version(
        "data/release_candidate.txt", common_dir
    )
    context["header_release_candidate_version"] = (
        header_release_candidate_version
    )

    google_site_verification_content = _read_common_version(
        "data/google_site_verification.txt", common_dir
    )
    context["google_site_verification_content"] = (
        google_site_verification_content
    )

    context["header_rocm_toolkits"] = _get_rocm_toolkits(common_dir)


def _update_repo_opts(srcdir: str, theme_opts: dict[str, Any]) -> None:
    default_branch_options: dict[str, Any] = {
        "use_edit_page_button": False,
    }
    try:
        url, branch = util.get_branch(srcdir)
        default_branch_options.update(
            {
                "repository_url": url,
                "repository_branch": branch,
                "path_to_docs": util.get_path_to_docs(srcdir),
            }
        )
    except util.InvalidGitRepositoryError:
        logger.warning("Not in a Git Directory, disabling repository buttons")

    for key, val in default_branch_options.items():
        theme_opts.setdefault(key, val)


def _update_banner(
    flavor: str, version_type: util.VersionType, theme_opts: dict[str, Any]
) -> None:
    if flavor != "rocm":
        return

    if (
        version_type == util.VersionType.ROCM_LATEST_RELEASE
        or version_type == util.VersionType.OTHER_LATEST_RELEASE
    ):
        return

    announcement_info: str
    if version_type == util.VersionType.RELEASE_CANDIDATE:
        announcement_info = "This page contains changes for a test release of ROCm. Read the <a id='rocm-banner' href='https://rocm.docs.amd.com/en/latest/'>latest Linux release of ROCm documentation</a> for your production environments."
    elif version_type == util.VersionType.OLD_RELEASE:
        announcement_info = "This is not the latest version of ROCm documentation. See <a id='rocm-banner' href='https://rocm.docs.amd.com/en/latest/'>ROCm documentation</a> for the latest version."
    elif version_type == util.VersionType.DEVELOPMENT:
        announcement_info = "This page contains proposed changes for a future release of ROCm. Read the <a id='rocm-banner' href='https://rocm.docs.amd.com/en/latest/'>latest Linux release of ROCm documentation</a> for your production environments."

    theme_opts.setdefault("announcement", announcement_info)


def _update_theme_options(app: Sphinx) -> None:
    theme_opts = get_theme_options_dict(app)
    _update_repo_opts(str(app.srcdir), theme_opts)

    supported_flavors = [
        "rocm",
        "local",
        "instinct",
        "instinct-design",
        "rocm-docs-home",
        "rocm-blogs",
        "generic",
        "rocm-ds",
        "ai-developer-hub",
        "ai-ecosystem",
        "rocm-ls",
        "gsplat",
        "rocm-rag",
        "amdgpu",
        "rocm-finance",
        "rocm-simulation",
        "rocm-llmext",
        "rocm-ft",
        "hyperloom",
        "rocm-ai",
        "rocm-extras",
    ]
    flavor = theme_opts.get("flavor", "rocm")
    if flavor not in supported_flavors:
        logger.error(
            f'Unsupported theme flavor "{flavor}", must be one of: {supported_flavors}.\n'
            "Using flavor={supported_flavors[0]}"
        )
        flavor = supported_flavors[0]
        theme_opts["flavor"] = flavor

    if flavor == "rocm-ft":
        theme_opts["nosidebar"] = True
        theme_opts["primary_sidebar_end"] = []
        theme_opts["primary_sidebar_start"] = []

    # Set default generic theme options
    if flavor == "generic":
        theme_opts.setdefault("header_title", "")
        theme_opts.setdefault("header_link", "#")
        theme_opts.setdefault("version_list_link", None)
        theme_opts.setdefault("nav_secondary_items", {})
        theme_opts.setdefault("license_link", None)
        theme_opts.setdefault("license_text", "")

    theme_opts.setdefault(
        "article_header_start",
        ["components/toggle-primary-sidebar.html", "breadcrumbs.html"],
    )

    if hasattr(app.config, "projects_version_type"):
        _update_banner(flavor, app.config.projects_version_type, theme_opts)

    # Default the download, edit, and fullscreen buttons to off
    for button in ["download", "edit_page", "fullscreen"]:
        theme_opts.setdefault(f"use_{button}_button", False)

    if theme_opts.get("link_main_doc", True):
        theme_opts.setdefault("navbar_center", []).insert(
            0, "components/left-side-menu"
        )

    common_dir = getattr(app.config, common.COMMON_DIR_CONFIG, None)
    header_latest_version = _read_common_version(
        "data/latest_version.txt", common_dir
    )

    header_release_candidate_version = _read_common_version(
        "data/release_candidate.txt", common_dir
    )

    default_config_opts = {
        "html_show_sphinx": False,
        "html_favicon": "https://www.amd.com/content/dam/code/images/favicon/favicon.ico",
        "notfound_context": {"title": "404 - Page Not Found"},
        "notfound_template": "404.html",
        "html_context": {
            "header_latest_version": _parse_version(header_latest_version),
            "header_release_candidate_version": header_release_candidate_version,
            "header_rocm_toolkits": _get_rocm_toolkits(common_dir),
        },
    }
    for key, default in default_config_opts.items():
        if not config_provided_by_user(app, key):
            setattr(app.config, key, default)


def _load_flavor_assets(app: Sphinx) -> None:
    """Load CSS and JS files from a flavor's static/ directory, if present."""
    theme_opts = get_theme_options_dict(app)
    flavor = theme_opts.get("flavor", "rocm")
    flavor_static = (
        Path(__file__).parent
        / "rocm_docs_theme"
        / "flavors"
        / flavor
        / "static"
    )
    if not flavor_static.is_dir():
        return

    app.config.html_static_path.append(str(flavor_static))
    for css_file in sorted(flavor_static.glob("*.css")):
        app.add_css_file(css_file.name)
    for js_file in sorted(flavor_static.glob("*.js")):
        app.add_js_file(js_file.name, loading_method="async")


def setup(app: Sphinx) -> dict[str, Any]:
    """Set up the module as a Sphinx extension."""
    app.add_js_file(
        "https://download.amd.com/js/analytics/analyticsinit.js",
        priority=999_999,
        loading_method="async",
    )
    app.add_js_file("code_word_breaks.js", loading_method="async")
    app.add_js_file("renameVersionLinks.js", loading_method="async")
    app.add_js_file("rdcMisc.js", loading_method="async")
    app.add_js_file("theme_mode_captions.js", loading_method="async")
    app.add_js_file("search.js", loading_method="defer")
    here = Path(__file__).parent.resolve()
    theme_path = here / "rocm_docs_theme"
    app.add_html_theme("rocm_docs_theme", str(theme_path))
    for css in [
        "custom.css",
        "rocm_header.css",
        "rocm_footer.css",
        "fonts.css",
    ]:
        app.add_css_file(css)

    app.connect("html-page-context", _add_custom_context)
    app.connect("builder-inited", _update_theme_options)
    app.connect("builder-inited", _load_flavor_assets)

    # Add theme option declarations
    app.add_config_value("header_title", "", "html")
    app.add_config_value("header_link", "#", "html")
    app.add_config_value("version_list_link", None, "html")
    app.add_config_value("nav_secondary_items", {}, "html", [dict])
    app.add_config_value("license_link", None, "html")
    app.add_config_value("license_text", "", "html")

    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
