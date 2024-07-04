from rocm_docs import ROCmDocs

docs_core = ROCmDocs("ROCm Docs Core Test Project - Minimal Legacy")
docs_core.setup()

for sphinx_var in ROCmDocs.SPHINX_VARS:
    globals()[sphinx_var] = getattr(docs_core, sphinx_var)

external_projects_current_project = "a"
