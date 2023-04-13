"""Set up variables for documentation of ROCm projects using RTD."""
import os
from pathlib import Path
from typing import BinaryIO, Dict, Generator, List, Optional, Union

from rocm_docs.core import setup

MaybePath = Union[str, os.PathLike, None]


# Intentionally disabling the too-many-instance-attributes check in pylint
# as this class is intended to contain all necessary Sphinx config variables
# pylint: disable=too-many-instance-attributes
class ROCmDocs:
    """A class to contain all of the Sphinx variables"""

    SPHINX_VARS = [
        "extensions",
        "html_title",
        "html_theme_options",
        "doxygen_root",
        "doxygen_project",
        "doxyfile",
        "doxysphinx_enabled",
    ]

    def __init__(
        self,
        project_name: str,
        _: MaybePath = None,
    ) -> None:
        self._project_name = project_name
        self.extensions: List[str] = []
        self.html_title: str
        self.html_theme_options: Dict[str, Union[str, bool, List[str]]] = {}
        self.doxygen_root: MaybePath
        self.doxygen_project: Tuple[Optional[str], MaybePath]
        self.doxyfile: MaybePath
        self.doxysphinx_enabled = False

    @property
    def project(self) -> str:
        """Sphinx project variable."""
        return self._project_name

    def run_doxygen(
        self,
        doxygen_root: MaybePath = None,
        doxygen_path: MaybePath = None,
        doxygen_file: Optional[str] = None,
    ) -> None:
        if not "rocm_docs.doxygen" in self.extensions:
            self.extensions.append("rocm_docs.doxygen")

        self.doxygen_root = doxygen_root
        self.doxygen_project = {
            "name": self._project_name,
            "path": doxygen_path,
        }
        self.doxyfile = doxygen_file

    def enable_api_reference(self) -> None:
        """Enable embedding the doxygen generated api."""
        if not "rocm_docs.doxygen" in self.extensions:
            self.extensions.append("rocm_docs.doxygen")

        self.doxysphinx_enabled = True

    def setup(self) -> None:
        """Sets up default RTD variables and copies necessary files."""
        self.extensions.append("rocm_docs")
        self.html_title = self._project_name

    def disable_main_doc_link(self):
        self.html_theme_options["link_main_doc"] = False


__all__ = ["setup", "ROCmDocs"]
