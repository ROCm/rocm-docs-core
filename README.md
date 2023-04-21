# ROCm Documentation Core Utilities

### Purpose

This repository is comprised of utilities, styling, scripts, and additional HTML content that is common to all ROCm projects' documentation. This greatly aids in maintaining the documentation, as any change to the appearance only needs to be modified in one location.

### Common elements covered

- Javascript tweaks for tables with long variable names, as Sphinx' default rendering is problematic.
- HTML for a header and footer for the documentation page.
- Common Sphinx configuration options for ROCm documentation processes.

### Use

- Install this `rocm-docs-core` as a Python package using pip: `pip install rocm-docs-core`.
- From the `rocm_docs` package import the class `ROCmDocs` into `conf.py` for the ReadTheDocs project.
- Example, replacing `<PROJECT NAME HERE>` with the name of the project.

```python
from rocm_docs import ROCmDocs

docs_core = ROCmDocs(<PROJECT NAME HERE>)
docs_core.run_doxygen()  # Only if Doxygen is required for this project
docs_core.setup()

for sphinx_var in ROCmDocs.SPHINX_VARS:
    globals()[sphinx_var] = getattr(docs_core, sphinx_var)
```
