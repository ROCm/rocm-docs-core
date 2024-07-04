from rocm_docs import ROCmDocs

docs_core = ROCmDocs("ROCm Docs Core Doxygen Test Project - Legacy")
docs_core.setup()
docs_core.run_doxygen(doxygen_root="doxygen", doxygen_path="doxygen/xml")
docs_core.enable_api_reference()

for sphinx_var in ROCmDocs.SPHINX_VARS:
    globals()[sphinx_var] = getattr(docs_core, sphinx_var)

if not "extensions" in globals():
    extensions = []

extensions += ["sphinxcontrib.doxylink"]

external_projects_current_project = "a"
