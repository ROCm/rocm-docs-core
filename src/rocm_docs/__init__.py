"""Set up variables for documentation of ROCm projects using RTD."""
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, List, Optional, Union, Dict, Tuple
from sphinx.application import Sphinx

from .util import format_toc, get_branch, get_path_to_docs


if sys.version_info < (3, 9):
    # importlib.resources either doesn't exist or lacks the files()
    # function, so use the PyPI version:
    import importlib_resources

else:
    # importlib.resources has files(), so use that:
    import importlib.resources as importlib_resources

MaybePath = Union[str, os.PathLike, None]


# Intentionally disabling the too-many-instance-attributes check in pylint
# as this class is intended to contain all necessary Sphinx config variables
# pylint: disable=too-many-instance-attributes
class ROCmDocs:
    """A class to contain all of the Sphinx variables"""

    SPHINX_VARS = [
        "copyright",
        "author",
        "project",
        "extensions",
        "breathe_projects",
        "breathe_default_project",
        "myst_enable_extensions",
        "myst_heading_anchors",
        "external_toc_path",
        "external_toc_exclude_missing",
        "intersphinx_mapping",
        "intersphinx_disabled_domains",
        "epub_show_urls",
        "exclude_patterns",
        "html_theme",
        "html_title",
        "html_theme_options",
        "numfig",
    ]

    def __init__(
        self,
        project_name: str,
        docs_folder: MaybePath = None,
    ) -> None:
        self._project_name = project_name
        self.copyright: str
        self.author: str
        self.extensions: List[str]
        self.breathe_projects: Dict[str, str]
        self.breathe_default_project: str
        self.myst_enable_extensions: List[str]
        self.myst_heading_anchors: int
        self.external_toc_path: str
        self.external_toc_exclude_missing: bool
        self.intersphinx_mapping: Dict[str, Tuple[str, None]]
        self.intersphinx_disabled_domains: List[str]
        self.templates_path: List[str]
        self.epub_show_urls: str
        self.exclude_patterns: List[str]
        self.html_theme: str
        self.html_title: str
        self.html_theme_options: Dict[str, Union[str, bool, List[str]]] = {}
        self.numfig: bool
        self._docs_folder: Path
        tmp_docs_folder = self.to_path(docs_folder)
        self._docs_folder = (
            tmp_docs_folder if tmp_docs_folder is not None else Path(".")
        )
        self._doxygen_context = _DoxygenContext()
        self._copied_files = False
        self._ran_doxygen = False
        self._setup = False

    @property
    def project(self) -> str:
        """Sphinx project variable."""
        return self._project_name

    @staticmethod
    def to_path(path_obj: MaybePath) -> Optional[Path]:
        """Ensure that an object is a pathlib Path."""
        if path_obj is None:
            return path_obj
        if not isinstance(path_obj, Path):
            return Path(path_obj)
        return path_obj

    def run_doxygen(
        self,
        doxygen_root: MaybePath = None,
        doxygen_path: MaybePath = None,
        doxygen_file: Optional[str] = None,
    ) -> None:
        """Run doxygen, validating all paths."""
        if self._ran_doxygen:
            # Only run doxygen once
            return
        self._ran_doxygen = True
        doxygen_root = self.to_path(doxygen_root)
        if doxygen_root is None:
            doxygen_root = Path("./.doxygen")
        doxygen_path = self.to_path(doxygen_path)
        if doxygen_path is None:
            doxygen_path = Path("docBin/xml")
        doxygen_file = "Doxyfile" if doxygen_file is None else doxygen_file

        try:
            doxygen_root = doxygen_root.resolve(strict=True)
        except FileNotFoundError as err:
            raise NotADirectoryError(
                f"Expected doxygen root folder {doxygen_root} to exist"
                " and be readable."
            ) from err
        doxyfile = doxygen_root / doxygen_file
        if not doxyfile.is_file():
            raise FileNotFoundError(
                f"Expected doxyfile {doxyfile} to exist and be readable."
            )

        doxygen_exe = shutil.which("doxygen")
        if doxygen_exe is None:
            raise RuntimeError("'doxygen' command not found! Make sure that "
                               "doxygen is installed and in the PATH")

        
        # Running doxygen requires that the files are already copied because 
        # the Doxyfile references files distributed with rocm-docs-core
        # (e.g. stylesheets)
        self.copy_files()
        try:
            subprocess.check_call([doxygen_exe, "--version"], cwd=doxygen_root)
            subprocess.check_call([doxygen_exe, doxygen_file], cwd=doxygen_root)
        except subprocess.CalledProcessError as err:
            raise RuntimeError("Failed when running doxygen") from err
        try:
            doxygen_path = doxygen_path.resolve(strict=True)
        except FileNotFoundError:
            try:
                doxygen_path = (doxygen_root / doxygen_path).resolve(
                    strict=True
                )
            except FileNotFoundError as err:
                raise NotADirectoryError(
                    "Expected doxygen to generate the folder"
                    f" {doxygen_path} but it could not be found."
                ) from err

        self._doxygen_context = _DoxygenContext(ran_doxygen=True,
                                                root=doxygen_root,
                                                path=doxygen_path,
                                                doxyfile=Path(doxygen_file))
        if hasattr(setup, '_doxygen_context'):
            setup._doxygen_context = self._doxygen_context

        if self._setup:
            self.extensions += ["sphinx.ext.mathjax", "breathe"]
            self.breathe_projects = {
                self._project_name: str(self._doxygen_context.path)
            }
            self.breathe_default_project = self._project_name

    def enable_api_reference(self) -> None:
        """Enable embedding the doxygen generated api.
        `run_doxygen` must be called (before or after) for this to work
        This requires extra dependencies exposed as the api_reference option.
        """
        try:
            import doxysphinx.cli
        except ImportError:
            raise RuntimeError("Missing optional dependencies: make sure the " 
                               "[api_reference] feature is enabled. (e.g. "
                               "\"pip install rocm-docs-core[api_reference]\")")

        # Register the data that will be needed for doxysphinx, it will be run
        # during setup()
        # It cannot run just yet as we don't know the location of
        # doxygen source and output directories.
        # In the future rocm-docs-core could be converted to a sphinx extension,
        # then this hack wouldn't be required.
        setup._doxygen_context = self._doxygen_context

    def setup(self) -> None:
        """Sets up default RTD variables and copies necessary files."""
        if self._setup:
            return
        self._setup = True
        # pylint: disable=redefined-builtin
        self.copyright = "2022-2023, Advanced Micro Devices Ltd."
        # pylint: enable=redefined-builtin
        self.author = (
            'Advanced Micro Devices <a href="https://">Disclaimer and'
            " Licensing Info</a>"
        )

        # -- General configuration --------------------------------------------
        # -- General configuration
        self.extensions = [
            "rocm_docs",
            "sphinx.ext.duration",
            "sphinx.ext.doctest",
            "sphinx.ext.autodoc",
            "sphinx.ext.autosummary",
            "sphinx.ext.intersphinx",
            "sphinx_external_toc",
            "sphinx_design",
            "sphinx_copybutton",
            "myst_nb",
            "notfound.extension",
        ]

        if self._ran_doxygen:
            self.extensions += ["sphinx.ext.mathjax", "breathe"]
            self.breathe_projects = {
                self._project_name: str(self._doxygen_context.path)
            }
            self.breathe_default_project = self._project_name
        else:
            self.breathe_projects = {}
            self.breathe_default_project = ""

        # MyST Configuration
        self.myst_enable_extensions = [
            "colon_fence",
            "linkify",
            "fieldlist",
            "replacements"
        ]
        self.myst_heading_anchors = 3

        # Table of Contents Configuration

        if not (self._docs_folder.exists() and self._docs_folder.is_dir()):
            raise NotADirectoryError(
                f"Expected docs folder {self._docs_folder} to exist and be"
                " readable."
            )

        toc_in_path = self._docs_folder / "./.sphinx/_toc.yml.in"
        if not (toc_in_path.exists() and toc_in_path.is_file()):
            raise FileNotFoundError(
                f"Expected input toc file {toc_in_path} to exist and be"
                " readable."
            )
        format_toc(self._docs_folder)

        self.external_toc_path = "./.sphinx/_toc.yml"
        self.external_toc_exclude_missing = False

        # intersphinx Configuration
        self.intersphinx_mapping = {
            "rtd": ("https://docs.readthedocs.io/en/stable/", None),
            "python": ("https://docs.python.org/3/", None),
            "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
        }
        self.intersphinx_disabled_domains = ["std"]

        # -- Options foself.r EPUB output
        self.epub_show_urls = "footnote"

        # List of patterns, relative to source directory, that match files and
        # directories to ignore when looking for source files.
        # This pattern also affects html_static_path and html_extra_path.
        self.exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

        # -- Options for HTML output ------------------------------------------

        # The theme to use for HTML and HTML Help pages.  See the documentation
        # for a list of builtin themes.
        #
        self.html_theme = "rocm_docs_theme"
        self.html_title = self._project_name

        self.numfig = True

        self.copy_files()

    def disable_main_doc_link(self):
        self.html_theme_options["link_main_doc"] = False

    def copy_files(self):
        """Insert additional files into workspace."""
        if self._copied_files:
            return
        self._copied_files = True

        def copy_from_package(data_dir, read_path: str, write_path: str):
            if not data_dir.is_dir():
                raise NotADirectoryError(
                    f"Expected path {read_path}/{data_dir} to be traversable."
                )
            for entry in data_dir.iterdir():
                entry_path: Path = self._docs_folder / write_path / entry.name
                if entry.is_dir():
                    entry_path.mkdir(parents=True, exist_ok=True)
                    copy_from_package(
                        entry,
                        read_path + "/" + entry.name,
                        write_path + "/" + entry.name,
                    )
                else:
                    with entry.open("rb") as resource_file:
                        # We open the resource file as a binary stream instead
                        # of a file on disk because the latter may require
                        # unzipping and/or the creation of a temporary file.
                        # This is not the case when opening the file as a
                        # stream.
                        resource_file: BinaryIO
                        with open(entry_path, "wb") as output_file:
                            shutil.copyfileobj(resource_file, output_file)

        pkg = importlib_resources.files("rocm_docs")
        copy_from_package(pkg / "data", "data", ".")


def force_notfound_prefix(app, config):
    if os.environ.get("READTHEDOCS", "False") == "True":
        default, _, _ = app.config.values.get("notfound_urls_prefix")
        if app.config.notfound_urls_prefix == default:
            current_version = app.config["html_context"].get("current_version") + "/" if app.config["html_context"].get("current_version") is not None else ""
            abs_path = re.sub(
                r"^(?:.*://)?[^/]*/(.*)/[^/]*/$",
                r"/\1/" + current_version,
                config.html_baseurl,
            )
            app.config.notfound_urls_prefix = abs_path


@dataclass
class _DoxygenContext:
    ran_doxygen: bool = False
    root: Path = Path()
    path: Path = Path()
    doxyfile: str = ""


def setup(app: Sphinx) -> None:
    app.setup_extension("notfound.extension")
    app.connect("config-inited", force_notfound_prefix, 300)

    # Execute doxysphinx now that sphinx source and output directories are known
    if not hasattr(setup, '_doxygen_context'):
        return

    doxygen_context = setup._doxygen_context
    if not doxygen_context.ran_doxygen:
        raise RuntimeError("Doxysphinx enabled but run_doxygen not called")

    res = subprocess.run([sys.executable, "-m", "doxysphinx", "build",
                          app.srcdir, app.outdir, doxygen_context.doxyfile],
                         cwd=doxygen_context.root)
    if res.returncode != 0:
        raise RuntimeError(f"doxysphinx failed (exitcode={res.returncode:d})")
