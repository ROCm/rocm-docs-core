"""Tests for the ROCm Sphinx theme."""

from collections import Counter
from io import StringIO
from pathlib import Path
from unittest.mock import Mock

import pytest
from sphinx.application import Sphinx


def test_header_metadata_is_fetched_once_per_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from rocm_docs import theme

    values = {
        "latest_version.txt": "ROCm: 7.0",
        "release_candidate.txt": "7.1",
        "google_site_verification.txt": "verification",
        "rocm_toolkits.txt": "Toolkit: https://example.org",
    }
    requests_by_file: Counter[str] = Counter()

    def fetch(url: str, **_kwargs: object) -> Mock:
        name = url.rsplit("/", 1)[-1]
        requests_by_file[name] += 1
        return Mock(status_code=200, text=values[name])

    monkeypatch.setattr(theme.requests, "get", fetch)
    src = tmp_path / "src"
    src.mkdir()
    (src / "conf.py").write_text(
        "extensions = ['rocm_docs.theme']\n"
        "project = 'Test'\n"
        "html_context = {'custom': 'kept'}\n"
    )
    (src / "index.rst").write_text(
        "Index\n=====\n\n.. toctree::\n\n   second\n"
    )
    (src / "second.rst").write_text("Second\n======\n")
    app = Sphinx(
        src,
        src,
        tmp_path / "html",
        tmp_path / "doctrees",
        "html",
        status=StringIO(),
        warning=StringIO(),
    )
    pages = {}

    def capture(_app, name, _template, context, _doctree):
        pages[name] = {
            key: context[key]
            for key in (
                "custom",
                "header_latest_version",
                "header_release_candidate_version",
                "google_site_verification_content",
                "header_rocm_toolkits",
            )
        }

    app.connect("html-page-context", capture, priority=900)
    app.build(force_all=True)
    assert (
        pages["index"]
        == pages["second"]
        == {
            "custom": "kept",
            "header_latest_version": {"ROCm": "7.0"},
            "header_release_candidate_version": "7.1",
            "google_site_verification_content": "verification",
            "header_rocm_toolkits": {"Toolkit": "https://example.org"},
        }
    )
    assert requests_by_file == dict.fromkeys(values, 1)
