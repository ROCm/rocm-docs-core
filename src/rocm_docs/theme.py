from typing import Dict, Any
from pathlib import Path

from sphinx.application import Sphinx
from pydata_sphinx_theme.utils import (
    config_provided_by_user,
    get_theme_options_dict,
)

import rocm_docs.util as util


def _update_edit_opts(
    srcdir: Path, theme_opts: Dict[str, Any]
) -> Dict[str, Any]:
    # Bail if the user explicitly disabled the edit button
    if not theme_opts.get("use_edit_page_button", True):
        return

    url, branch, edit_page = util.get_branch(srcdir)
    default_branch_options = {
        "use_edit_page_button": edit_page,
        "repository_url": url,
        "repository_branch": branch,
        "path_to_docs": util.get_path_to_docs(srcdir),
    }
    for k, v in default_branch_options.items():
        theme_opts.setdefault(k, v)


def _update_theme_options(app: Sphinx) -> None:
    theme_opts = get_theme_options_dict(app)
    _update_edit_opts(app.srcdir, theme_opts)

    theme_opts.setdefault(
        "article_header_start",
        ["toggle-primary-sidebar.html", "breadcrumbs.html"],
    )

    # Prepend or set as value if the list doesn't yet exist
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
    app.add_js_file(
        "https://download.amd.com/js/analytics/analyticsinit.js",
        priority=999_999,
        loading_method="async",
    )
    app.add_js_file("code_word_breaks.js", loading_method="async")
    app.add_js_file("renameVersionLinks.js", loading_method="async")
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
