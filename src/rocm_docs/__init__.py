"""Set up variables for documentation of ROCm projects using RTD."""

import os
import re
from typing import Dict, List, Optional, Union

from deprecated import deprecated

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
        "html_theme",
        "html_theme_options",
        "doxygen_root",
        "doxygen_project",
        "doxyfile",
        "doxysphinx_enabled",
    ]

    def __init__(
        self,
        project_name: str,
        version_string: Optional[str] = None,
        _: MaybePath = None,
    ) -> None:
        self._project_name: str = project_name
        self._version_string: str = (
            "" if version_string is None else version_string
        )
        self.extensions: List[str] = []
        self.html_title: str
        self.html_theme: str
        self.html_theme_options: Dict[str, Union[str, bool, List[str]]] = {}
        self.doxygen_root: MaybePath = None
        self.doxygen_project: Dict[str, Union[Optional[str], MaybePath]] = {
            "name": None,
            "path": None,
        }
        self.doxyfile: MaybePath = None
        self.doxysphinx_enabled: bool = False

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
        """Run doxygen as part of Sphinx by adding rocm_docs.doxygen."""
        if "rocm_docs.doxygen" not in self.extensions:
            self.extensions.append("rocm_docs.doxygen")

        self.doxygen_root = doxygen_root
        self.doxygen_project = {
            "name": self._project_name,
            "path": doxygen_path,
        }
        self.doxyfile = doxygen_file

    def enable_api_reference(self) -> None:
        """Enable embedding the doxygen generated api."""
        if "rocm_docs.doxygen" not in self.extensions:
            self.extensions.append("rocm_docs.doxygen")

        self.doxysphinx_enabled = True

    def setup(self) -> None:
        """Sets up default RTD variables."""
        self.extensions.append("rocm_docs")
        full_project_name = self._project_name
        if self._version_string is None and os.path.exists(
            "../CMakeLists.txt"
        ):
            with open("../CMakeLists.txt", encoding="utf8") as file:
                for line in file.readlines():
                    if "VERSION_STRING" in line:
                        self._version_string = re.sub(
                            r"^.*VERSION_STRING.*\s\"([0-9]+(?:\.[0-9]+)*).*$",
                            "\1",
                            line,
                        )
                        break
        if self._version_string is not None and len(self._version_string) > 0:
            full_project_name += f" {self._version_string}"
        self.html_title = full_project_name
        self.html_theme = "rocm_docs_theme"

__all__ = ["setup", "ROCmDocs"]
