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
from sphinx.application import Sphinx
from sphinx.config import Config


def set_article_info(app: Sphinx, _: Config) -> None:
    """Add article info headers to HTML pages."""
    if (
        app.config.setting_all_article_info is False
        and len(app.config.article_pages) == 0
    ):
        return

    article_info = (
        importlib.resources.files("rocm_docs")
        .joinpath("rocm_docs_theme/components/article-info.html")
        .read_text(encoding="utf-8")
    )

    specific_pages: list[str] = []

    _set_page_article_info(app, article_info, specific_pages)

    if app.config.setting_all_article_info is True:
        _set_all_article_info(app, article_info, specific_pages)


def _set_page_article_info(
    app: Sphinx, article_info: str, specific_pages: list[str]
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
        modified_info = article_info.replace("<!--os-info-->", article_os_info)

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
    app: Sphinx, article_info: str, specific_pages: list[str]
) -> None:
    """Add article info headers with general settings to all HTML pages.

    Pages that have specific settings (configured by "article_pages") are
    skipped.
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

        os_list = []
        if "linux" in app.config.all_article_info_os:
            os_list.append("Linux")
        if "windows" in app.config.all_article_info_os:
            os_list.append("Windows")
        article_os_info = " and ".join(os_list)
        if os_list:
            article_os_info = f"Applies to {article_os_info}"

        date_info = _get_time_last_modified(repo, Path(app.srcdir, page_rel))
        if not date_info:
            date_info = cast(str, app.config.all_article_info_date)

        modified_info = article_info.replace("<!--os-info-->", article_os_info)
        modified_info = modified_info.replace(
            "<!--author-info-->", app.config.all_article_info_author
        )
        modified_info = modified_info.replace("<!--date-info-->", date_info)
        modified_info = modified_info.replace(
            "<!--read-info-->", _estimate_read_time(page)
        )

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
    page_text = soup.find_all(text=True)
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
