import sphinx
from sphinx.application import Sphinx
from sphinx.config import Config
from typing import Dict, Any
from pathlib import Path
from pydata_sphinx_theme import _get_theme_options
import rocm_docs.util as util

def _update_theme_options(app: Sphinx) -> None:
    url, branch, edit_page = util.get_branch(app.srcdir)

    options = _get_theme_options(app)
    options.update({
        "home_page_in_toc": False,
        "use_edit_page_button": edit_page,
        "repository_url": url,
        "repository_branch": branch,
        "path_to_docs": util.get_path_to_docs(app.srcdir),
        "show_navbar_depth": "0",
        "body_max_width": "none",
        "show_toc_level": "0",
        "article_header_start": [
            "toggle-primary-sidebar.html",
            "breadcrumbs.html",
        ],
    })
    if options.get("link_main_doc", True):
        options["navbar_center"] = ["components/left-side-menu"]

def setup(app: Sphinx) -> Dict[str, Any]:
    app.add_js_file("code_word_breaks.js", loading_method="async")
    here = Path(__file__).parent.resolve()
    theme_path = here / "rocm_docs_theme"
    app.add_html_theme("rocm_docs_theme", str(theme_path))
    for css in ["custom.css", "rocm_header.css", "rocm_footer.css", "fonts.css"]:
        app.add_css_file(css)
    app.connect("builder-inited", _update_theme_options)

    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
