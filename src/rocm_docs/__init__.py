"""Set up variables for documentation of ROCm projects using RTD."""
import os
import shutil
import sys
from pathlib import Path
from typing import BinaryIO, List, Union, Dict, Tuple
from .util import format_toc, get_path_to_docs


if sys.version_info < (3, 9):
    # importlib.resources either doesn't exist or lacks the files()
    # function, so use the PyPI version:
    import importlib_resources

else:
    # importlib.resources has files(), so use that:
    import importlib.resources as importlib_resources


def setup_rocm_docs(
    project_name: str, docs_folder: Union[str, os.PathLike, None] = None
) -> Tuple[
    str,
    str,
    str,
    List[str],
    List[str],
    int,
    str,
    bool,
    Dict[str, Tuple[str, None]],
    List[str],
    List[str],
    str,
    List[str],
    str,
    str,
    List[str],
    List[str],
    List[str],
    List[str],
    Dict[str, Union[str, bool]],
    bool,
    str,
]:
    """Sets up default RTD variables and copies necessary files.

    Args:
        project_name (str): The name of the project.
        docs_folder (str | os.PathLike, optional): The path to the            \
            documentation folder. Defaults to None.

    Raises:
        NotADirectoryError: The specified documentation folder does not exist \
            or cannot be read.
        FileNotFoundError: The input table of contents file does not exist or \
            cannot be read.
        NotADirectoryError: An error occurred when trying to copy files from  \
            the rocm_docs package.
    """
    # pylint: disable=redefined-builtin
    copyright = "2022-2023, Advanced Micro Devices Ltd."
    # pylint: enable=redefined-builtin
    author = (
        'Advanced Micro Devices <a href="https://">Disclaimer and Licensing'
        " Info</a>"
    )
    project = project_name

    # -- General configuration ------------------------------------------------
    # -- General configuration
    extensions = [
        "sphinx.ext.duration",
        "sphinx.ext.doctest",
        "sphinx.ext.autodoc",
        "sphinx.ext.autosummary",
        "sphinx.ext.intersphinx",
        "sphinx_external_toc",
        "sphinx_design",
        "sphinx_copybutton",
        "myst_nb",
    ]

    # MyST Configuration
    myst_enable_extensions = ["colon_fence", "linkify"]
    myst_heading_anchors = 3

    # Table of Contents Configuration
    if docs_folder is None:
        docs_folder = Path.cwd()
    elif not isinstance(docs_folder, Path):
        docs_folder = Path(docs_folder)
    if not (docs_folder.exists() and docs_folder.is_dir()):
        raise NotADirectoryError(
            f"Expected docs folder {docs_folder} to exist and be readable."
        )

    toc_in_path = docs_folder / "_toc.yml.in"
    if not (toc_in_path.exists() and toc_in_path.is_file()):
        raise FileNotFoundError(
            f"Expected input toc file {toc_in_path} to exist and be readable."
        )
    url, branch = format_toc(docs_folder)

    external_toc_path = "_toc.yml"
    external_toc_exclude_missing = False

    # intersphinx Configuration
    intersphinx_mapping = {
        "rtd": ("https://docs.readthedocs.io/en/stable/", None),
        "python": ("https://docs.python.org/3/", None),
        "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
    }
    intersphinx_disabled_domains = ["std"]

    # Other configuration
    templates_path = ["_templates"]

    # -- Options for EPUB output
    epub_show_urls = "footnote"

    # List of patterns, relative to source directory, that match files and
    # directories to ignore when looking for source files.
    # This pattern also affects html_static_path and html_extra_path.
    exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

    # -- Options for HTML output ----------------------------------------------

    # The theme to use for HTML and HTML Help pages.  See the documentation for
    # a list of builtin themes.
    #
    html_theme = "sphinx_book_theme"
    html_title = project
    html_static_path = ["_static"]
    html_css_files = ["custom.css", "rocm_header.css", "rocm_footer.css"]
    html_js_files = ["code_word_breaks.js"]
    html_extra_path = ["_images"]
    html_theme_options = {
        "home_page_in_toc": True,
        "use_edit_page_button": True,
        "repository_url": url,
        "repository_branch": branch,
        "path_to_docs": get_path_to_docs(),
        "show_navbar_depth": "2",
        "body_max_width": "none",
        "show_toc_level": "0",
        "extra_navbar": "",
    }

    html_show_sphinx = False
    html_favicon = "https://www.amd.com/themes/custom/amd/favicon.ico"

    # Insert additional files into workspace
    def copy_from_package(data_dir, read_path: str, write_path: str):
        if not data_dir.is_dir():
            raise NotADirectoryError(
                f"Expected path {read_path}/{data_dir} to be traversable."
            )
        for entry in data_dir.iterdir():
            entry_path: Path = docs_folder / write_path / entry.name
            if entry.is_dir():
                entry_path.mkdir(parents=True, exist_ok=True)
                copy_from_package(
                    entry,
                    read_path + "/" + entry.name,
                    write_path + "/" + entry.name,
                )
            else:
                with entry.open("rb") as resource_file:
                    # We open the resource file as a binary stream instead of a
                    # file on disk because the latter may require unzipping
                    # and/or the creation of a temporary file. This is not the
                    # case when opening the file as a stream.
                    resource_file: BinaryIO
                    with open(entry_path, "wb") as output_file:
                        shutil.copyfileobj(resource_file, output_file)

    pkg = importlib_resources.files("rocm_docs")
    copy_from_package(pkg / "data", "data", ".")

    return (
        copyright,
        author,
        project,
        extensions,
        myst_enable_extensions,
        myst_heading_anchors,
        external_toc_path,
        external_toc_exclude_missing,
        intersphinx_mapping,
        intersphinx_disabled_domains,
        templates_path,
        epub_show_urls,
        exclude_patterns,
        html_theme,
        html_title,
        html_static_path,
        html_css_files,
        html_js_files,
        html_extra_path,
        html_theme_options,
        html_show_sphinx,
        html_favicon,
    )
