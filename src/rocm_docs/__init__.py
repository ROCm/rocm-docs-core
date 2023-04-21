"""Set up variables for documentation of ROCm projects using RTD."""

import os
import subprocess
from typing import Dict, List, Optional, Union
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
        version_string : str = None,
        _: MaybePath = None,
    ) -> None:
        self._project_name = project_name
        self._version_string = version_string
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
        self.doxysphinx_enabled = False

    @property
    def project(self) -> str:
        """Sphinx project variable."""
        return self._project_name

    def copy_file(self, source: str, dest: str) -> None:
        os.system(f"cp {source} {dest}")
        copied_files = "copied_files.txt"
        file = open(copied_files, "a")
        file.write(dest + "\r\n")


    def run_sed_on_file(self, expression: str, file: str) -> None:
        os.system(f"sed -i '{expression}' {file}")

    def run_doxygen(
        self,
        doxygen_root: MaybePath = None,
        doxygen_path: MaybePath = None,
        doxygen_file: Optional[str] = None,
    ) -> None:
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
        """Sets up default RTD variables and copies necessary files."""
        self.extensions.append("rocm_docs")
        full_project_name = self._project_name
        if self._version_string is None and os.path.exists("../CMakeLists.txt"):
            getVersionString = r'sed -n -e "s/^.*VERSION_STRING.* \"\([0-9\.]\{1,\}\).*/\1/p" ../CMakeLists.txt'
            self._version_string = subprocess.getoutput(getVersionString)
        if self._version_string is not None and len(self._version_string) > 0:
            full_project_name += f" {self._version_string}"
        self.html_title = full_project_name
        self.html_theme = "rocm_docs_theme"

    def disable_main_doc_link(self):
        self.html_theme_options["link_main_doc"] = False


__all__ = ["setup", "ROCmDocs"]
