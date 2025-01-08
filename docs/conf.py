"""Configuration file for the Sphinx documentation builder.

This file only contains a selection of the most common options. For a full
list see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html

For a list of options specific to rocm-docs-core, see the user guide:
https://rocm.docs.amd.com/projects/rocm-docs-core/en/latest/
"""

# Disable fetching projects.yaml, it would be the same as the local one anyway
# except if a PR modifies it. We want to test with its version in that case
external_projects_remote_repository = ""
external_projects = ["hipify", "python", "rocm-docs-core", "rocm"]
external_projects_current_project = "rocm-docs-core"

setting_all_article_info = True
all_article_info_os = []
all_article_info_author = ""
# specific settings override any general settings (eg: all_article_info_<field>)
article_pages = [
    {
        "file": "index",
        "os": ["linux", "windows"],
        "author": "Author: AMD",
        "date": "2024-07-03",
        "read-time": "2 min read",
    },
    {
        "file": "user_guide/article_info",
        "os": [],
        "author": "",
        "date": "",
        "read-time": "",
    },
    {
        "file": "developer_guide/commitizen",
    },
]

html_theme = "rocm_docs_theme"
html_theme_options = {"flavor": "rocm"}

external_toc_path = "./sphinx/_toc.yml"

extensions = ["rocm_docs", "rocm_docs.doxygen"]
doxygen_root = "demo/doxygen"
doxysphinx_enabled = True
doxygen_project = {
    "name": "doxygen",
    "path": "demo/doxygen/xml",
}

version = "1.13.0"
release = "1.13.0"
html_title = f"ROCm Docs Core {version}"
project = "ROCm Docs Core"
author = "Advanced Micro Devices, Inc."
copyright = (
    "Copyright (c) 2025 Advanced Micro Devices, Inc. All rights reserved."
)
