extensions = ["rocm_docs", "rocm_docs.doxygen", "sphinxcontrib.doxylink"]
html_theme = "rocm_docs_theme"

external_projects_current_project = "a"

doxygen_project = {
    "name": "ROCm Docs Core Test Project - Extension",
    "path": "doxygen/xml",
}
doxysphinx_enabled = True
