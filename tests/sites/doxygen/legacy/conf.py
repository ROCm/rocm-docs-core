from rocm_docs import ROCmDocs

# base setup for using rocm-docs-core package
docs_core = ROCmDocs("ROCm Docs Core Doxygen Test Project - Legacy")
docs_core.setup()

# doxygen integration
docs_core.run_doxygen(doxygen_root="doxygen", doxygen_path="doxygen/xml")

# doxysphinx integration
docs_core.enable_api_reference()

# used in intersphinx linking
external_projects_current_project = "a"

# custom path to table of contents
external_toc_path = "./sphinx/_toc.yml"

# set variables from rocm-docs-core for sphinx
for sphinx_var in ROCmDocs.SPHINX_VARS:
    globals()[sphinx_var] = getattr(docs_core, sphinx_var)

# optional extension for additional linking to doxygen
if not "extensions" in globals():
    extensions = []
extensions += ["sphinxcontrib.doxylink"]
