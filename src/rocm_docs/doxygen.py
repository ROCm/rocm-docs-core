"""Doxygen sub-extension of rocm-docs-core."""

from __future__ import annotations

from typing import Any, Dict, Union

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

from pydata_sphinx_theme.utils import config_provided_by_user  # type: ignore[import]
from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.errors import ConfigError

from rocm_docs import util

if sys.version_info < (3, 9):
    # importlib.resources either doesn't exist or lacks the files()
    # function, so use the PyPI version:
    import importlib_resources
else:
    # importlib.resources has files(), so use that:
    import importlib.resources as importlib_resources


def _copy_files(app: Sphinx) -> None:
    """Insert additional files into workspace."""
    pkg = importlib_resources.files("rocm_docs")
    Path(app.srcdir, "_doxygen").mkdir(exist_ok=True)
    util.copy_from_package(
        app, pkg / "data/_doxygen", "data/_doxygen", "_doxygen"
    )


def _get_config_default(config: Config, key: str) -> Any:
    """Get the default value for a sphinx configuration key."""
    default_or_callable = config.values[key][0]
    if callable(default_or_callable):
        return default_or_callable(config)
    return default_or_callable


def _run_doxygen(app: Sphinx, config: Config) -> None:
    """Run doxygen, validating all paths."""
    # To support the (legacy) ROCmDocs interface 'None' is a synonym for the
    # default value
    for i in ["doxygen_root", "doxyfile"]:
        if getattr(config, i) is None:
            setattr(config, i, _get_config_default(config, i))

    doxygen_root = Path(app.confdir, config.doxygen_root)
    try:
        doxygen_root = doxygen_root.resolve(strict=True)
    except FileNotFoundError as err:
        raise ConfigError(
            f"Expected doxygen root folder {doxygen_root} to exist"
            " and be readable."
        ) from err

    if config["doxygen_executable"] is None:
        cmd_path = shutil.which("doxygen")
        if cmd_path is None:
            raise RuntimeError(
                "'doxygen' command not found! Make sure that "
                "doxygen is installed and in the PATH or specify "
                "via doxygen_executable configuration variable."
            )
        doxygen_exe = Path(cmd_path)
    else:
        doxygen_exe = Path(app.confdir, config.doxygen_executable)

    doxyfile = Path(app.confdir, config["doxyfile"]).absolute()
    if not doxyfile.is_file():
        raise ConfigError(
            f"Expected doxyfile {doxyfile} to exist and be readable."
        )

    # Running doxygen requires that the files are already copied because
    # the Doxyfile references files distributed with rocm-docs-core
    # (e.g. stylesheets)
    _copy_files(app)
    try:
        subprocess.check_call([doxygen_exe, "--version"], cwd=doxygen_root)
        subprocess.check_call([doxygen_exe, doxyfile], cwd=doxygen_root)
    except subprocess.CalledProcessError as err:
        raise RuntimeError("Failed when running doxygen") from err

    _update_breathe_settings(app, doxygen_root)
    _run_doxysphinx(app, doxygen_root, doxyfile)


def _update_breathe_settings(app: Sphinx, doxygen_root: Path) -> None:
    if config_provided_by_user(
        app, "breathe_projects"
    ) or config_provided_by_user(app, "breathe_default_project"):
        return

    doxygen_project: dict[
        str, None | str | os.PathLike[Any]
    ] = app.config.doxygen_project

    # To support the (legacy) ROCmDocs interface 'None' is a synonym for the
    # default value for each element of the Tuple
    default: dict[str, None | str | os.PathLike[Any]] = _get_config_default(
        app.config, "doxygen_project"
    )
    for key, value in doxygen_project.items():
        if value is None:
            doxygen_project[key] = default[key]

    # FIXME: Log an error and reset to default instead of asserting
    assert isinstance(doxygen_project["name"], str)
    project_name: str = doxygen_project["name"]

    # First try relative to the
    assert doxygen_project["path"] is not None
    xml_path = Path(app.confdir, doxygen_project["path"])
    try:
        xml_path = xml_path.resolve(strict=True)
    except FileNotFoundError as err:
        raise NotADirectoryError(
            "Expected doxygen to generate the folder"
            f" {str(doxygen_root)} but it could not be found."
        ) from err

    setattr(app.config, "breathe_projects", {project_name: str(xml_path)})
    setattr(app.config, "breathe_default_project", project_name)


def _run_doxysphinx(app: Sphinx, doxygen_root: Path, doxyfile: Path) -> None:
    if not app.config.doxysphinx_enabled:
        return

    if (
        "doxysphinx.cli" not in sys.modules
        and importlib.util.find_spec("doxysphinx.cli") is None
    ):
        raise RuntimeError(
            "Missing optional dependencies: make sure the "
            "[api_reference] feature is enabled. (e.g. "
            '"pip install rocm-docs-core[api_reference]")'
        )

    try:
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "doxysphinx",
                "build",
                app.srcdir,
                app.outdir,
                doxyfile,
            ],
            cwd=doxygen_root,
        )
    except subprocess.CalledProcessError as err:
        raise RuntimeError(
            f"doxysphinx failed (exit code: {err.returncode})"
        ) from err


def setup(app: Sphinx) -> dict[str, Any]:
    """Set up rocm_docs.doxygen as a Sphinx extension."""
    app.setup_extension("sphinx.ext.mathjax")
    app.setup_extension("breathe")

    app.add_config_value(
        "doxygen_root", ".doxygen", rebuild="", types=[None, str, os.PathLike]
    )
    app.add_config_value(
        "doxygen_executable",
        None,
        rebuild="",
        types=[None, str, "os.PathLike[Any]"],
    )
    app.add_config_value(
        "doxyfile",
        lambda config: Path(config.doxygen_root, "Doxyfile"),
        rebuild="",
        types=[None, str, "os.PathLike[Any]"],
    )
    app.add_config_value(
        "doxygen_project",
        lambda config: {
            "name": "doxygen",
            "path": Path(config.doxygen_root, "docBin", "xml"),
        },
        rebuild="",
        types=Dict[str, Union[None, str, "os.PathLike[Any]"]],
    )
    app.add_config_value("doxysphinx_enabled", False, rebuild="", types=bool)

    # Should run before breathe sees their parameters, as we provide defaults.
    app.connect("config-inited", _run_doxygen, priority=400)

    return {"parallel_read_safe": True, "parallel_write_safe": True}
