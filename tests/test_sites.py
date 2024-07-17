from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from sphinx.errors import ExtensionError, ConfigError
from sphinx.application import Sphinx

from .log_fixtures import ExpectLogFixture
from .sphinx_fixtures import SITES_BASEFOLDER

TEMPLATE_FOLDER = SITES_BASEFOLDER / "templates"


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    mark = metafunc.definition.get_closest_marker("for_all_folders")
    if mark is not None and "build_factory" in metafunc.fixturenames:

        def folder_id(p: Path) -> str:
            return str(p.relative_to(mark.args[0]))

        metafunc.parametrize(
            "build_factory",
            (
                x.relative_to(SITES_BASEFOLDER)
                for x in SITES_BASEFOLDER.joinpath(mark.args[0]).iterdir()
            ),
            ids=folder_id,
            indirect=True,
        )


@pytest.mark.for_all_folders("pass")
@pytest.mark.template_folder(TEMPLATE_FOLDER / "minimal")
@pytest.mark.usefixtures("mocked_projects")
def test_e2e_pass(
    build_factory: Callable[..., tuple[Path, Path]],
) -> None:
    srcdir, outdir = build_factory()
    build_sphinx(srcdir, outdir)


@pytest.mark.for_all_folders("doxygen")
@pytest.mark.template_folder(
    TEMPLATE_FOLDER / "minimal", TEMPLATE_FOLDER / "doxygen"
)
@pytest.mark.usefixtures("mocked_projects")
def test_e2e_doxygen(
    build_factory: Callable[..., tuple[Path, Path]], expect_log: ExpectLogFixture
) -> None:
    srcdir, outdir = build_factory()
    with expect_log(
        "sphinx.sphinx.util.docutils",
        "WARNING",
        "toctree directive not expected with external-toc [etoc.toctree]",
        required=False,
        capture_all=True,
    ):
        build_sphinx(srcdir, outdir)

    expected_tagfile = Path(outdir, "tagfile.xml")
    assert expected_tagfile.is_file()


def suppress_specific_warnings(app, msg, *args, **kwargs):
    if "node class 'toctree' is already registered" in msg:
        return  # Suppress this specific warning


class SphinxWarning(Exception):
    pass


def build_sphinx(srcdir: Path, outdir: Path, confdir: Path | None = None) -> None:
    confdir = confdir or srcdir
    doctreedir = outdir / '.doctrees'
    buildername = 'html'
    app = Sphinx(srcdir, confdir, outdir, doctreedir, buildername)

    # Connect the warning filter
    app.connect('warning', suppress_specific_warnings)

    try:
        app.build()
    except ExtensionError as e:
        print(f"ExtensionError occurred: {e}")
        raise
    except ConfigError as e:
        print(f"ConfigError occurred: {e}")
        raise
