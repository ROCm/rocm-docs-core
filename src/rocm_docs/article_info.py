"""Logic to add article info to a page.

For all options see the user guide:
https://rocm.docs.amd.com/projects/rocm-docs-core/en/latest/user_guide/article_info.html
"""

from typing import Any, cast

import importlib.resources
import os
import re
from pathlib import Path

import bs4
import git.repo
from docutils.parsers.rst import Directive, directives
from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.util import logging as sphinx_logging

logger = sphinx_logging.getLogger(__name__)


class ArticleInfoDirective(Directive):
    """RST directive to set article info metadata for a page.

    Usage::

        .. article-info::
           :os: linux windows
           :author: Author: AMD
           :date: 2024-07-03
           :read-time: 2 min read

    The stored data is identical in shape to the ``article_info`` key in
    MyST front matter, so the rest of the pipeline handles both sources
    the same way.

    Only one ``article-info`` definition per page is allowed. If
    ``article_info`` is already present in page metadata (e.g. set via
    MyST front matter, or by a previous directive), a warning is emitted
    and the duplicate is ignored.
    """

    has_content = False
    required_arguments = 0
    optional_arguments = 0
    option_spec = {
        "os": directives.unchanged,
        "author": directives.unchanged,
        "date": directives.unchanged,
        "read-time": directives.unchanged,
    }

    def run(self):
        env = self.state.document.settings.env

        if "article_info" in env.metadata[env.docname]:
            logger.warning(
                "article-info is already defined for '%s'; ignoring duplicate."
                " In MyST Markdown, prefer the front matter 'article_info:'"
                " block over the '{article-info}' directive.",
                env.docname,
                location=(env.docname, self.lineno),
            )
            return []

        article_info: dict[str, Any] = {}
        if "os" in self.options:
            article_info["os"] = self.options["os"].split()
        if "author" in self.options:
            article_info["author"] = self.options["author"]
        if "date" in self.options:
            article_info["date"] = self.options["date"]
        if "read-time" in self.options:
            article_info["read-time"] = self.options["read-time"]

        if article_info:
            env.metadata[env.docname]["article_info"] = article_info

        return []


def _get_page_article_info_meta(app: Sphinx, docname: str) -> dict[str, Any]:
    """Return the article_info dict from page metadata, or empty dict."""
    return app.env.metadata.get(docname, {}).get("article_info", {})


def set_article_info(app: Sphinx, _: Config) -> None:
    """Add article info headers to HTML pages."""
    has_metadata_pages = any(
        _get_page_article_info_meta(app, docname)
        for docname in app.project.docnames
    )

    if (
        app.config.setting_all_article_info is False
        and len(app.config.article_pages) == 0
        and not has_metadata_pages
    ):
        return

    article_info_html = (
        importlib.resources.files("rocm_docs")
        .joinpath("rocm_docs_theme/components/article-info.html")
        .read_text(encoding="utf-8")
    )

    specific_pages: list[str] = []

    _set_page_article_info(app, article_info_html, specific_pages)

    if app.config.setting_all_article_info is True or has_metadata_pages:
        _set_all_article_info(app, article_info_html, specific_pages)


def _set_page_article_info(
    app: Sphinx, article_info_html: str, specific_pages: list[str]
) -> None:
    """Add article info headers to the configured HTML pages.

    The pages can be set in "article_pages" of the Sphinx configuration.
    """
    repo = git.repo.Repo(app.srcdir, search_parent_directories=True)
    for page in app.config.article_pages:
        path_rel = app.project.doc2path(page["file"], False)
        path_html = Path(app.outdir, path_rel).with_suffix(".html")
        path_source = Path(app.srcdir, path_rel)

        # FIXME: This will silently skip all files when not building the default
        # `html` format (e.g `htmlzip`, `epub` or `pdf`)
        if not path_html.is_file():
            continue

        os_list = []
        page.setdefault("os", app.config.all_article_info_os)
        if "linux" in page["os"]:
            os_list.append("Linux")
        if "windows" in page["os"]:
            os_list.append("Windows")
        article_os_info = " and ".join(os_list)
        if os_list:
            article_os_info = f"Applies to {article_os_info}"
        modified_info = article_info_html.replace("<!--os-info-->", article_os_info)

        author = app.config.all_article_info_author
        if "author" in page:
            author = page["author"]
        modified_info = modified_info.replace("<!--author-info-->", author)

        date_info: str | None = None
        if "date" in page:
            date_info = page["date"]
        else:
            date_info = _get_time_last_modified(repo, path_source)

        if date_info == "":
            soup = bs4.BeautifulSoup(modified_info, "html.parser")
            svg_to_remove = soup.find("span", class_="article-info-date-svg")
            if svg_to_remove and isinstance(svg_to_remove, bs4.Tag):
                svg_to_remove.decompose()
            modified_info = str(soup)

        if date_info is not None:
            modified_info = modified_info.replace("<!--date-info-->", date_info)

        if "read-time" in page:
            read_time = page["read-time"]
        else:
            read_time = _estimate_read_time(path_html)

        if read_time == "":
            soup = bs4.BeautifulSoup(modified_info, "html.parser")
            svg_to_remove = soup.find(
                "span", class_="article-info-read-time-svg"
            )
            if svg_to_remove and isinstance(svg_to_remove, bs4.Tag):
                svg_to_remove.decompose()
            modified_info = str(soup)

        if read_time is not None:
            modified_info = modified_info.replace("<!--read-info-->", read_time)

        specific_pages.append(page["file"])
        _write_article_info(path_html, modified_info)


def _set_all_article_info(
    app: Sphinx, article_info_html: str, specific_pages: list[str]
) -> None:
    """Add article info headers with general settings to all HTML pages.

    Pages that have specific settings (configured by "article_pages") are
    skipped. Pages may also supply an ``article_info`` dict via MyST front
    matter or the ``.. article-info::`` RST directive; those values override
    the global ``all_article_info_*`` config defaults.
    """
    repo = git.repo.Repo(app.srcdir, search_parent_directories=True)
    for docname in app.project.docnames:
        # skip pages with specific settings
        if docname in specific_pages:
            continue

        page_rel = app.project.doc2path(docname, False)
        page = Path(app.outdir, page_rel).with_suffix(".html")

        # FIXME: This will silently skip all files when not building the default
        # `html` format (e.g `htmlzip`, `epub` or `pdf`)
        if not page.is_file():
            continue

        page_meta = _get_page_article_info_meta(app, docname)

        # Skip pages that have no article_info metadata when not in "all" mode
        if not app.config.setting_all_article_info and not page_meta:
            continue

        # OS: page metadata overrides global config
        raw_os = page_meta.get("os", app.config.all_article_info_os)
        if isinstance(raw_os, str):
            raw_os = raw_os.split()
        os_list = []
        if "linux" in raw_os:
            os_list.append("Linux")
        if "windows" in raw_os:
            os_list.append("Windows")
        article_os_info = " and ".join(os_list)
        if os_list:
            article_os_info = f"Applies to {article_os_info}"

        # Author: page metadata overrides global config
        author: str = page_meta.get("author", app.config.all_article_info_author)

        # Date: page metadata > git last-modified > global config
        if "date" in page_meta:
            date_info: str = page_meta["date"]
        else:
            date_info = _get_time_last_modified(repo, Path(app.srcdir, page_rel)) or cast(
                str, app.config.all_article_info_date
            )

        # Read time: page metadata overrides auto-calculated value
        if "read-time" in page_meta:
            read_time: str = page_meta["read-time"]
        else:
            read_time = _estimate_read_time(page)

        modified_info = article_info_html.replace("<!--os-info-->", article_os_info)
        modified_info = modified_info.replace("<!--author-info-->", author)
        modified_info = modified_info.replace("<!--date-info-->", date_info)
        modified_info = modified_info.replace("<!--read-info-->", read_time)

        _write_article_info(page, modified_info)


def _get_time_last_modified(repo: git.repo.Repo, path: Path) -> str | None:
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
        if isinstance(element, bs4.element.Comment):
            return False
        return element.string != "\n"

    def count_words(text):
        words = re.findall(r"\w+", text)
        return len(words)

    words_per_minute = 200

    with open(file_name, encoding="utf-8") as file:
        html = file.read()
    soup = bs4.BeautifulSoup(html, "html.parser")
    article = soup.find("article") or soup.find("main") or soup
    page_text = article.find_all(text=True)
    visible_page_text = filter(is_visible, page_text)
    average_word_count = sum(count_words(line) for line in visible_page_text)
    time_minutes = int(max(1, round(average_word_count / words_per_minute)))
    return f"{time_minutes} min read time"


def _write_article_info(path: os.PathLike[Any], article_info: str) -> None:
    with open(path, "r+", encoding="utf8") as file:
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
