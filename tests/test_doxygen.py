from __future__ import annotations

from types import SimpleNamespace

import copy
import unittest.mock

import pytest

import rocm_docs.doxygen


def test_copy_tagfile(tmp_path_factory: pytest.TempPathFactory) -> None:
    app = unittest.mock.NonCallableMock()

    srcdir = tmp_path_factory.mktemp("srcdir")
    srcfile = srcdir.joinpath("tagfile.xml")
    expected_content = "Dummy doxygen tagfile"
    srcfile.write_text(expected_content)

    outdir = tmp_path_factory.mktemp("outdir").absolute()
    outfile = outdir.joinpath("tagfile.xml")

    app.config.doxygen_html = ""
    app.builder = SimpleNamespace(format="html")
    app.outdir = str(outdir)
    app.srcdir = str(srcdir)

    rocm_docs.doxygen._copy_tagfile(app)

    assert outfile.read_text() == expected_content


@pytest.mark.parametrize(
    ("output_format", "doxygen_html"),
    [("html", None), ("epub", "")],
    ids=["not_set", "skipped_format"],
)
def test_copy_tagfile_skipped(
    tmp_path_factory: pytest.TempPathFactory,
    output_format: str,
    doxygen_html: str | None,
) -> None:
    app = unittest.mock.NonCallableMock()

    srcdir = tmp_path_factory.mktemp("srcdir")
    srcfile = srcdir.joinpath("tagfile.xml")
    srcfile.touch(exist_ok=False)

    outdir = tmp_path_factory.mktemp("outdir").absolute()
    outfile = outdir.joinpath("tagfile.xml")

    app.config.doxygen_html = doxygen_html
    app.builder = SimpleNamespace(format=output_format)
    app.outdir = str(outdir)
    app.srcdir = str(srcdir)

    rocm_docs.doxygen._copy_tagfile(app)

    assert not outfile.exists()


@pytest.mark.parametrize(
    ("has_doxylink", "has_doxygen_html"),
    [(False, True), (True, False), (False, False)],
    ids=["no_doxylink", "no_html", "neither"],
)
def test_update_doxylink_settings_skipped(
    has_doxylink: bool, has_doxygen_html: bool
) -> None:
    app = unittest.mock.NonCallableMock(spec=["config", "srcdir"])
    app.srcdir = ""
    config_spec = ["doxygen_html", "overrides", "_raw_config"]

    if has_doxylink:
        config_spec.append("doxylink")

    config = unittest.mock.NonCallableMock(config_spec)
    config.doxygen_html = "doxygen/html" if has_doxygen_html else None
    config.overrides = []
    config._raw_config = []
    expected: dict[str, tuple[str, str]]
    if has_doxylink:
        expected = {"must-not-be-changed": ("tagfile.xml", "test-string")}
        config.doxylink = copy.copy(expected)
    app.config = config

    rocm_docs.doxygen._update_doxylink_settings(app, config)

    if has_doxylink:
        assert app.config.doxylink == expected
    else:
        assert not hasattr(app.config, "doxylink")
