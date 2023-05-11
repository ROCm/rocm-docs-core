# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from rocm_docs import ROCmDocs

setting_all_article_info = True

# Disable fetching projects.yaml, it would be the same as the local one anyway
# except if a PR modifies it. We want to test with its version in that case
external_projects_remote_repository = ""

external_projects_current_project = "rocm-docs-core"

# specific settings override any general settings (eg: all_article_info_<field>)
article_pages = [
    {
        "file":"index", 
        "os":["linux", "windows"], 
        "author":"Author: AMD", 
        "date":"2023-05-01", 
        "read-time":"2 min read"
    },
    {"file":"developer_guide/commitizen"}
]

docs_core = ROCmDocs("ROCm Docs Core")
docs_core.run_doxygen(doxygen_root="demo/doxygen", doxygen_path=".")
docs_core.enable_api_reference()
docs_core.setup()

for sphinx_var in ROCmDocs.SPHINX_VARS:
    globals()[sphinx_var] = getattr(docs_core, sphinx_var)
