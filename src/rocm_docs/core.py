"""Core rocm_docs extension that enables a core set of sphinx extensions and
provides good defaults for settings. Provides a consistent common
base environment for the rocm documentation projects."""

import inspect
import os
import re
import types
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, Generic, Type, TypeVar
from bs4 import BeautifulSoup

from pydata_sphinx_theme.utils import config_provided_by_user
from sphinx.application import Sphinx
from sphinx.config import Config

import rocm_docs.util as util

T = TypeVar("T")


class _ConfigUpdater(Generic[T], ABC):
    def __init__(self, default: T) -> None:
        super().__init__()
        self.default = default

    @abstractmethod
    def __call__(self, key: str, app: Sphinx) -> None:
        pass


def _config_updater(
    f: Callable[[str, Sphinx, T], None]
) -> Type[_ConfigUpdater]:
    def __call__(self: _ConfigUpdater[T], key: str, app: Sphinx) -> None:
        f(key, app, self.default)

    def update_body(body: Dict[str, Any]) -> None:
        body["__call__"] = __call__

    return types.new_class(
        f.__name__, bases=[_ConfigUpdater[T]], exec_body=update_body
    )


@_config_updater
def _ConfigExtend(key: str, app: Sphinx, default: T) -> None:
    getattr(app.config, key).extend(default)


@_config_updater
def _ConfigDefault(key: str, app: Sphinx, default: T) -> None:
    if not config_provided_by_user(app, key):
        setattr(app.config, key, default)


@_config_updater
def _ConfigOverride(key: str, app: Sphinx, value: T) -> None:
    setattr(app.config, key, value)


@_config_updater
def _ConfigMerge(key: str, app: Sphinx, default: Dict[str, Any]) -> None:
    setting: Dict[str, Any] = getattr(app.config, key)
    for key, value in default.items():
        setting.setdefault(key, value)


class _DefaultSettings:
    author = _ConfigDefault(
        'Advanced Micro Devices <a href="https://">Disclaimer and'
        " Licensing Info</a>"
    )
    # pylint: disable=redefined-builtin
    copyright = _ConfigDefault("2022-2023, Advanced Micro Devices Ltd")
    # pylint: enable=redefined-builtin
    myst_enable_extensions = _ConfigExtend(
        ["colon_fence", "fieldlist", "linkify", "replacements", "substitution"]
    )
    myst_heading_anchors = _ConfigDefault(3)
    external_toc_path = _ConfigOverride("./.sphinx/_toc.yml")
    external_toc_exclude_missing = _ConfigDefault(False)
    intersphinx_mapping = _ConfigMerge(
        {
            "rtd": ("https://docs.readthedocs.io/en/stable/", None),
            "python": ("https://docs.python.org/3/", None),
            "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
        }
    )
    intersphinx_disabled_domains = _ConfigDefault(["std"])
    epub_show_urls = _ConfigDefault("footnote")
    exclude_patterns = _ConfigExtend(["_build", "Thumbs.db", ".DS_Store"])
    numfig = _ConfigDefault(True)
    linkcheck_timeout = _ConfigDefault(10)
    linkcheck_request_headers = _ConfigMerge(
        {
            r'https://docs.github.com/': {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:112.0) Gecko/20100101 Firefox/112.0'}
        }
    )

    @classmethod
    def update_config(cls, app: Sphinx, _: Config) -> None:
        for name, attr in inspect.getmembers(cls):
            if isinstance(attr, _ConfigUpdater):
                attr(name, app)


def _format_toc_file(app: Sphinx, config: Config) -> None:
    toc_in_path = Path(app.srcdir) / "./.sphinx/_toc.yml.in"
    if not (toc_in_path.exists() and toc_in_path.is_file()):
        raise FileNotFoundError(
            f"Expected input toc file {toc_in_path} to exist and be"
            " readable."
        )
    util.format_toc(
        toc_path=app.srcdir,
        repo_path=app.srcdir,
        input_name="./.sphinx/_toc.yml.in",
        output_name=config.external_toc_path,
    )


def _force_notfound_prefix(app: Sphinx, _: Config) -> None:
    if not "READTHEDOCS" in os.environ:
        return

    if not config_provided_by_user(app, "notfound_urls_prefix"):
        return

    current_version = app.config["html_context"].get("current_version", "")
    if current_version != "":
        current_version += "/"
    abs_path = re.sub(
        r"^(?:.*://)?[^/]*/(.*)/[^/]*/$",
        r"/\1/" + current_version,
        app.config.html_baseurl,
    )
    app.config.notfound_urls_prefix = abs_path


def _add_article_info(app: Sphinx, _: Config) -> None:
    with open("_templates/components/article-info-linux.html", "r") as file:
        article_info_linux = file.read()
    with open("_templates/components/article-info-windows.html", "r") as file:
        article_info_win = file.read()
    with open("_templates/components/article-info-linux-windows.html", "r") as file:
        article_info_linux_and_win = file.read()
    for page in app.config.linux_pages:
        path = os.path.join(app.config.html_output_directory, page) + ".html"
        _write_article_info(path, article_info_linux)
    for page in app.config.windows_pages:
        path = os.path.join(app.config.html_output_directory, page) + ".html"
        _write_article_info(path, article_info_win)
    for page in app.config.linux_and_windows_pages:
        path = os.path.join(app.config.html_output_directory, page) + ".html"
        _write_article_info(path, article_info_linux_and_win)


def _write_article_info(path: str, article_info: str) -> None:
    with open(path, "r+") as file:
        page_html = file.read()
        file.truncate(0)
        soup = BeautifulSoup(page_html, 'html.parser')
        soup.article.insert(0, BeautifulSoup(article_info, 'html.parser'))
        file.write(str(soup))
        

def setup(app: Sphinx) -> Dict[str, Any]:
    required_extensions = [
        "myst_nb",
        "notfound.extension",
        "sphinx_copybutton",
        "sphinx_design",
        "sphinx_external_toc",
        "sphinx.ext.autodoc",
        "sphinx.ext.autosummary",
        "sphinx.ext.doctest",
        "sphinx.ext.duration",
        "sphinx.ext.intersphinx",
    ]
    for ext in required_extensions:
        app.setup_extension(ext)

    app.add_config_value("html_output_directory", default="_build/html/", rebuild="html", types=str)
    app.add_config_value("linux_pages", default=[], rebuild="html", types=Any)
    app.add_config_value("windows_pages", default=[], rebuild="html", types=Any)
    app.add_config_value("linux_and_windows_pages", default=[], rebuild="html", types=Any)

    # Run before notfound.extension sees the config (default priority(=500))
    app.connect("config-inited", _force_notfound_prefix, priority=400)
    app.connect("config-inited", _DefaultSettings.update_config)
    # This needs to happen before external-tocs's config-inited (priority=900)
    app.connect("config-inited", _format_toc_file)
    app.connect("build-finished", _add_article_info, priority=1000)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
