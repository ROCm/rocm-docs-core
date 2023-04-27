# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from rocm_docs import ROCmDocs

html_output_directory = "../_readthedocs/html"
setting_all_article_info = True
all_article_info_os = ["linux", "windows"]
all_article_info_author = ""
all_article_info_date = "2023"
all_article_info_read_time = "5-10 min read"

article_pages = [
    {"file":"index", "os":["windows"], "author":"Author: AMD", "date":"May 1, 2023", "read-time":"2 min read"},
    {"file":"developer_guide/commitizen", "os":["linux"], "date":"May 1, 2023", "read-time":"10 min read"}
]

docs_core = ROCmDocs("ROCm Docs Core")
docs_core.run_doxygen(doxygen_root="demo/doxygen", doxygen_path=".")
docs_core.enable_api_reference()
docs_core.setup()

for sphinx_var in ROCmDocs.SPHINX_VARS:
    globals()[sphinx_var] = getattr(docs_core, sphinx_var)
