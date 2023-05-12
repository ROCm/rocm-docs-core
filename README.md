# ROCm Documentation Core Utilities

### Purpose

This repository is comprised of utilities, styling, scripts, and additional HTML content that is common to all ROCm projects' documentation. This greatly aids in maintaining the documentation, as any change to the appearance only needs to be modified in one location.

### Common elements covered

- Javascript tweaks for tables with long variable names, as Sphinx' default rendering is problematic.
- HTML for a header and footer for the documentation page.
- Common Sphinx configuration options for ROCm documentation processes.

### Use

- Install this repository as a Python package using pip, for example `pip install git+https://github.com/RadeonOpenCompute/rocm-docs-core.git`.
- From the `rocm_docs` package import the function `setup_rocm_docs` into `conf.py` for the ReadTheDocs project.
- Call exactly the following, replacing `<PROJECT NAME HERE>` with the name of the project.
```python
from rocm_docs import ROCmDocs

docs_core = ROCmDocs(<PROJECT NAME HERE>)
docs_core.run_doxygen()  # Only if Doxygen is required for this project
docs_core.setup()

for sphinx_var in ROCmDocs.SPHINX_VARS:
    globals()[sphinx_var] = getattr(docs_core, sphinx_var)
```

### Documentation

Build documentation by running the commands below:

```
pip install -r requirements.txt
cd docs
python3 -m sphinx -T -E -b html -d _build/doctrees -D language=en . _build/html
```
