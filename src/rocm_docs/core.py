"""Core rocm_docs extension that enables a core set of sphinx extensions and
provides good defaults for settings. Provides a consistent common
base environment for the rocm documentation projects."""

import contextlib
import datetime
import glob
import inspect
import itertools
import os
import re
import sys
import types
from abc import ABC, abstractmethod
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    Generic,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    cast,
)

import bs4
import git.repo
from pydata_sphinx_theme.utils import config_provided_by_user  # type: ignore[import]
from sphinx.application import Sphinx
from sphinx.config import Config

import rocm_docs.util as util

# based on doxygen.py
if sys.version_info < (3, 9):
    import importlib_resources
else:
    import importlib.resources as importlib_resources


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
def _ConfigUnion(key: str, app: Sphinx, default: Set[T]) -> None:
    getattr(app.config, key).update(default)


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
    myst_enable_extensions = _ConfigUnion(
        {"colon_fence", "fieldlist", "linkify", "replacements", "substitution"}
    )
    myst_heading_anchors = _ConfigDefault(3)
    external_toc_path = _ConfigDefault("./.sphinx/_toc.yml")
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
            r"https://docs.github.com/": {
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:112.0) \
                Gecko/20100101 Firefox/112.0"
            }
        }
    )

    @classmethod
    def update_config(cls, app: Sphinx, _: Config) -> None:
        for name, attr in inspect.getmembers(cls):
            if isinstance(attr, _ConfigUpdater):
                attr(name, app)


def _format_toc_file(app: Sphinx, config: Config) -> None:
    toc_in_path = Path(app.srcdir) / (config.external_toc_path + ".in")
    if not (toc_in_path.exists() and toc_in_path.is_file()):
        raise FileNotFoundError(
            f"Expected input toc file {toc_in_path} to exist and be"
            " readable."
        )
    util.format_toc(
        toc_path=app.srcdir,
        repo_path=app.srcdir,
        input_name=config.external_toc_path + ".in",
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
    app.config.notfound_urls_prefix = abs_path  # type: ignore[attr-defined]


def _set_article_info(app: Sphinx, _: Config) -> None:
    """Add article info headers to HTML pages"""
    if (
        app.config.setting_all_article_info is False
        and len(app.config.article_pages) == 0
    ):
        return

    rocm_docs_package = importlib_resources.files("rocm_docs")
    article_info_path = os.path.join(
        rocm_docs_package, "rocm_docs_theme/components/article-info.html"
    )
    with open(article_info_path, "r") as file:
        article_info = file.read()

    specific_pages: List[str] = []

    _set_page_article_info(app, article_info, specific_pages)

    if app.config.setting_all_article_info is True:
        _set_all_article_info(app, article_info, specific_pages)


def _set_page_article_info(
    app: Sphinx, article_info: str, specific_pages: List[str]
) -> None:
    """
    Add article info headers to specific HTML pages
    mentioned in app.config.article_pages
    """
    repo = git.repo.Repo(app.srcdir, search_parent_directories=True)
    for page in app.config.article_pages:
        path_rel = app.project.doc2path(page["file"], basedir=False)
        path_html = Path(app.outdir, path_rel).with_suffix(".html")
        path_source = Path(app.srcdir, path_rel)

        article_os_info = ""
        if "os" not in page.keys():
            page["os"] = app.config.all_article_info_os
        if "linux" in page["os"]:
            article_os_info += "Linux"
        if "windows" in page["os"]:
            if len(article_os_info) > 0:
                article_os_info += " and "
            article_os_info += "Windows"
        modified_info = article_info.replace("<!--os-info-->", article_os_info)

        author = app.config.all_article_info_author
        if "author" in page.keys():
            author = page["author"]
        modified_info = modified_info.replace("AMD", author)

        date_info: Optional[str] = None
        if "date" in page.keys():
            date_info = page["date"]
        else:
            date_info = _get_time_last_modified(repo, path_source)

        if not date_info:
            date_info = cast(str, app.config.all_article_info_date)

        modified_info = modified_info.replace("2023", date_info)

        if "read-time" in page.keys():
            read_time = page["read-time"]
        else:
            read_time = _estimate_read_time(path_html)
        modified_info = modified_info.replace("5 min read", read_time)

        specific_pages.append(page["file"])
        _write_article_info(path_html, modified_info)


def _set_all_article_info(
    app: Sphinx, article_info: str, specific_pages: List[str]
) -> None:
    """
    Add article info headers with general settings to all HTML pages
    except those in app.config.article_pages
    """
    repo = git.repo.Repo(app.srcdir, search_parent_directories=True)
    for docname in app.project.docnames:
        # skip pages with specific settings
        if docname in specific_pages:
            continue

        article_os_info = ""
        if "linux" in app.config.all_article_info_os:
            article_os_info += "Linux"
        if "windows" in app.config.all_article_info_os:
            if len(article_os_info) > 0:
                article_os_info += " and "
            article_os_info += "Windows"

        page_rel = app.project.doc2path(docname, basedir=False)
        page = Path(app.outdir, page_rel).with_suffix(".html")

        date_info = _get_time_last_modified(repo, Path(app.srcdir, page_rel))
        if not date_info:
            date_info = cast(str, app.config.all_article_info_date)

        modified_info = article_info.replace("<!--os-info-->", article_os_info)
        modified_info = modified_info.replace(
            "AMD", app.config.all_article_info_author
        )
        modified_info = modified_info.replace("2023", date_info)
        modified_info = modified_info.replace(
            "5 min read", _estimate_read_time(page)
        )

        _write_article_info(page, modified_info)


def _get_time_last_modified(repo: git.repo.Repo, path: Path) -> Optional[str]:
    try:
        time = next(
            repo.iter_commits(paths=path, max_count=1)
        ).committed_datetime
        return time.strftime("%Y-%m-%d")
    except StopIteration:
        return None


def _estimate_read_time(file_name: Path) -> str:
    def is_visible(element):
        if element.parent.name in [
            "style",
            "script",
            "[document]",
            "head",
            "title",
        ]:
            return False
        elif isinstance(element, bs4.element.Comment):
            return False
        elif element.string == "\n":
            return False
        return True

    def count_words(text, avg_word_len):
        words = 0
        for line in text:
            words += len(line) / avg_word_len
        return words

    WORDS_PER_MIN = 200
    AVG_WORD_LEN = 5

    file = open(file_name, "r")
    html = file.read()
    soup = bs4.BeautifulSoup(html, "html.parser")
    page_text = soup.findAll(text=True)
    visible_page_text = filter(is_visible, page_text)
    average_word_count = count_words(visible_page_text, AVG_WORD_LEN)
    time_minutes = max(1, int(average_word_count // WORDS_PER_MIN))
    return f"{time_minutes} min read time"


def _write_article_info(path: Path, article_info: str) -> None:
    with open(path, "r+") as file:
        page_html = file.read()
        soup = bs4.BeautifulSoup(page_html, "html.parser")

        has_article_info = soup.find("div", id="rocm-docs-core-article-info")
        if (
            has_article_info is not None
            or soup.article is None
            or soup.article.h1 is None
        ):
            return

        soup.article.h1.insert_after(
            bs4.BeautifulSoup(article_info, "html.parser")
        )
        file.seek(0)
        file.truncate(0)
        file.write(str(soup))


def setup(app: Sphinx) -> Dict[str, Any]:
    required_extensions = [
        "myst_parser",
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

    app.add_config_value(
        "setting_all_article_info", default=False, rebuild="html", types=str
    )
    app.add_config_value(
        "all_article_info_os",
        default=["linux", "windows"],
        rebuild="html",
        types=str,
    )
    app.add_config_value(
        "all_article_info_author", default="", rebuild="html", types=str
    )
    app.add_config_value(
        "all_article_info_date", default="2023", rebuild="html", types=str
    )
    app.add_config_value(
        "all_article_info_read_time", default="", rebuild="html", types=str
    )
    app.add_config_value("article_pages", default=[], rebuild="html", types=Any)

    # Run before notfound.extension sees the config (default priority(=500))
    app.connect("config-inited", _force_notfound_prefix, priority=400)
    app.connect("config-inited", _DefaultSettings.update_config)
    # This needs to happen before external-tocs's config-inited (priority=900)
    app.connect("config-inited", _format_toc_file)
    app.connect("build-finished", _set_article_info, priority=1000)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
