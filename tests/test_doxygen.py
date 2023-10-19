from __future__ import annotations

from types import SimpleNamespace

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
