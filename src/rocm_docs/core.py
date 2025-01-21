"""Core rocm_docs extension.

It enables a core set of sphinx extensions and provides good defaults for
settings. The environment provided is meant as consistent common base for
ROCm documentation projects.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

import inspect
import os
import urllib.parse
from abc import ABC, abstractmethod

from pydata_sphinx_theme.utils import (  # type: ignore[import-untyped]
    config_provided_by_user,
)
from sphinx.application import Sphinx
from sphinx.config import Config

from rocm_docs import article_info

T = TypeVar("T")


class _ConfigUpdater(Generic[T], ABC):
    def __init__(self, default: T) -> None:
        super().__init__()
        self.default = default

    @abstractmethod
    def __call__(self, key: str, app: Sphinx) -> None:
        pass


class _ConfigExtend(_ConfigUpdater[list[T]]):
    def __call__(self, key: str, app: Sphinx) -> None:
        getattr(app.config, key).extend(self.default)


class _ConfigDefault(_ConfigUpdater[T]):
    def __call__(self, key: str, app: Sphinx) -> None:
        if not config_provided_by_user(app, key):
            setattr(app.config, key, self.default)


class _ConfigUnion(_ConfigUpdater[set[T]]):
    def __call__(self, key: str, app: Sphinx) -> None:
        getattr(app.config, key).update(self.default)


class _ConfigMerge(_ConfigUpdater[dict[str, Any]]):
    def __call__(self, key: str, app: Sphinx) -> None:
        current_setting: dict[str, Any] = getattr(app.config, key)
        for item in self.default.items():
            current_setting.setdefault(item[0], item[1])


class _DefaultSettings:
    author = _ConfigDefault(
        'Advanced Micro Devices <a href="https://">Disclaimer and'
        " Licensing Info</a>"
    )
    # pylint: disable=redefined-builtin
    copyright = _ConfigDefault("2022-2023, Advanced Micro Devices Ltd")
    # pylint: enable=redefined-builtin
    myst_enable_extensions = _ConfigUnion(
        {
            "colon_fence",
            "dollarmath",
            "fieldlist",
            "html_image",
            "replacements",
            "substitution",
        }
    )
    myst_heading_anchors = _ConfigDefault(3)
    external_toc_exclude_missing = _ConfigDefault(False)
    epub_show_urls = _ConfigDefault("footnote")
    exclude_patterns = _ConfigExtend(["_build", "Thumbs.db", ".DS_Store"])
    numfig = _ConfigDefault(True)
    linkcheck_timeout = _ConfigDefault(10)
    linkcheck_request_headers = _ConfigMerge(
        {
            r"https://docs.github.com/": {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:112.0)          "
                    "       Gecko/20100101 Firefox/112.0"
                )
            }
        }
    )

    @classmethod
    def update_config(cls, app: Sphinx, _: Config) -> None:
        """Update the Sphinx configuration from the default settings."""
        for name, attr in inspect.getmembers(cls):
            if isinstance(attr, _ConfigUpdater):
                attr(name, app)


def _force_notfound_prefix(app: Sphinx, _: Config) -> None:
    if "READTHEDOCS" not in os.environ:
        return

    if config_provided_by_user(app, "notfound_urls_prefix"):
        return

    components = urllib.parse.urlparse(os.environ["READTHEDOCS_CANONICAL_URL"])
    app.config.notfound_urls_prefix = components.path


def setup(app: Sphinx) -> dict[str, Any]:
    """Set up rocm_docs.core as a Sphinx extension."""
    required_extensions = [
        "myst_nb",
        "notfound.extension",
        "rocm_docs.projects",
        "sphinx_copybutton",
        "sphinx_design",
        "sphinx.ext.autodoc",
        "sphinx.ext.autosummary",
        "sphinx.ext.doctest",
        "sphinx.ext.duration",
    ]
    for ext in required_extensions:
        app.setup_extension(ext)

    app.add_config_value(
        "setting_all_article_info", default=False, rebuild="html", types=str
    )
    app.add_config_value(
        "all_article_info_os",
        default=[],
        rebuild="html",
        types=str,
    )
    app.add_config_value(
        "all_article_info_author", default="", rebuild="html", types=str
    )
    app.add_config_value(
        "all_article_info_date", default="", rebuild="html", types=str
    )
    app.add_config_value(
        "all_article_info_read_time", default="", rebuild="html", types=str
    )
    app.add_config_value(
        "article_pages", default=[], rebuild="html", types=list
    )

    # Run before notfound.extension sees the config (default priority(=500))
    app.connect("config-inited", _force_notfound_prefix, priority=400)
    app.connect("config-inited", _DefaultSettings.update_config)
    app.connect("build-finished", article_info.set_article_info, priority=1000)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
