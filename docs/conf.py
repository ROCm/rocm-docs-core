# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

setting_all_article_info = True

# Disable fetching projects.yaml, it would be the same as the local one anyway
# except if a PR modifies it. We want to test with its version in that case
external_projects_remote_repository = ""
external_projects = ["hipify", "python", "rocm-docs-core", "rocm"]

external_projects_current_project = "rocm-docs-core"

# specific settings override any general settings (eg: all_article_info_<field>)
article_pages = [
    {
        "file": "index",
        "os": ["linux", "windows"],
        "author": "Author: AMD",
        "date": "2023-11-03",
        "read-time": "2 min read",
    },
    {"file": "developer_guide/commitizen"},
]

html_theme = "rocm_docs_theme"

extensions = ["rocm_docs", "rocm_docs.doxygen"]
external_toc_path = "./sphinx/_toc.yml"
doxygen_root = "demo/doxygen"
doxysphinx_enabled = True
doxygen_project = {
    "name": "doxygen",
    "path": "demo/doxygen/xml",
}

version = "0.34.2"
release = "0.34.2"
html_title = f"ROCm Docs Core {version}"
project = "ROCm Docs Core"
author = "Advanced Micro Devices, Inc."
copyright = (
    "Copyright (c) 2024 Advanced Micro Devices, Inc. All rights reserved."
)
