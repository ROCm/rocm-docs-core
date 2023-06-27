"""Module to use rocm-docs-core as a theme."""

from typing import Any, Dict

from pathlib import Path

from pydata_sphinx_theme.utils import (  # type: ignore[import]
    config_provided_by_user,
    get_theme_options_dict,
)
from sphinx.application import Sphinx

from rocm_docs import util


def _update_repo_opts(
    srcdir: str, url: str, branch: str, theme_opts: Dict[str, Any]
) -> None:
    default_branch_options = {
        "use_edit_page_button": False,
        "repository_url": url,
        "repository_branch": branch,
        "path_to_docs": util.get_path_to_docs(srcdir),
    }
    for key, val in default_branch_options.items():
        theme_opts.setdefault(key, val)


def _update_banner(announcement_info: str, theme_opts: Dict[str, Any]) -> None:
    if len(announcement_info) > 0:
        theme_opts.setdefault("announcement", announcement_info)


def _update_theme_options(app: Sphinx) -> None:
    url, branch = util.get_branch(app.srcdir)
    theme_opts = get_theme_options_dict(app)
    _update_repo_opts(app.srcdir, url, branch, theme_opts)

    theme_opts.setdefault(
        "article_header_start",
        ["components/toggle-primary-sidebar.html", "breadcrumbs.html"],
    )

    _update_banner(app.config.announcement_info, theme_opts)

    # Default the download, edit, and fullscreen buttons to off
    for button in ["download", "edit_page", "fullscreen"]:
        theme_opts.setdefault(f"use_{button}_button", False)

    if theme_opts.get("link_main_doc", True):
        theme_opts.setdefault("navbar_center", []).insert(
            0, "components/left-side-menu"
        )

    default_config_opts = {
        "html_show_sphinx": False,
        "html_favicon": "https://www.amd.com/themes/custom/amd/favicon.ico",
    }
    for key, default in default_config_opts.items():
        if not config_provided_by_user(app, key):
            setattr(app.config, key, default)


def setup(app: Sphinx) -> Dict[str, Any]:
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
    app.connect("builder-inited", _update_theme_options)

    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
