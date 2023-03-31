"""Doxygen sub-extension of rocm-docs-core"""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from sphinx.application import Sphinx


@dataclass
class _DoxygenContext:
    ran_doxygen: bool = False
    root: Path = Path()
    path: Path = Path()
    doxyfile: str = ""


def setup(app: Sphinx) -> None:
    # Execute doxysphinx now that sphinx source and output directories are known
    if not hasattr(setup, "_doxygen_context"):
        return

    doxygen_context = setup._doxygen_context
    if not doxygen_context.ran_doxygen:
        raise RuntimeError("Doxysphinx enabled but run_doxygen not called")

    res = subprocess.run(
        [
            sys.executable,
            "-m",
            "doxysphinx",
            "build",
            app.srcdir,
            app.outdir,
            doxygen_context.doxyfile,
        ],
        cwd=doxygen_context.root,
    )
    if res.returncode != 0:
        raise RuntimeError(f"doxysphinx failed (exitcode={res.returncode:d})")
    return {"parallel_read_safe": True, "parallel_write_safe": True}
