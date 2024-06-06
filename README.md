# ROCm Documentation Core Utilities

ROCm Docs Core is also distributed as a pip package available from PyPi as
[rocm-docs-core](https://pypi.org/project/rocm-docs-core/)

## Purpose

This repository is comprised of utilities, styling, scripts, and additional HTML content that is common to all ROCm projects' documentation. This greatly aids in maintaining the documentation, as any change to the appearance only needs to be modified in one location.

## Usage

### Setup

- Install this repository as a Python package using pip
  - From PyPi: `pip install rocm-docs-core`
  - From GitHub: `pip install git+https://github.com/ROCm/rocm-docs-core.git`.

- Set `rocm_docs_theme` as the HTML theme
- Add `rocm_docs` as an extension
- Optionally, add `rocm_docs.doxygen` and `sphinxcontrib.doxylink` as extensions

For an example, see the [test conf.py](./tests/sites/doxygen/extension/conf.py)

### Legacy Setup

- From the `rocm_docs` package import the function `setup_rocm_docs` into `conf.py` for the ReadTheDocs project.
- Call exactly the following, replacing `<PROJECT NAME HERE>` with the name of the project.

For an example, see the [test legacy conf.py](./tests/sites/doxygen/legacy/conf.py)

## Documentation

The `rocm-docs-core` documentation is viewable at [https://rocm.docs.amd.com/projects/rocm-docs-core/en/latest/](https://rocm.docs.amd.com/projects/rocm-docs-core/en/latest/)

### User Guide

The User Guide describes how users can make use of functionality in `rocm-docs-core`

It is viewable at [https://rocm.docs.amd.com/projects/rocm-docs-core/en/latest/user_guide/user_guide.html](https://rocm.docs.amd.com/projects/rocm-docs-core/en/latest/user_guide/user_guide.html)

### Developer Guide

The Developer Guide provides additional information on the processes in toolchains for `rocm-docs-core`

It is viewable at [https://rocm.docs.amd.com/projects/rocm-docs-core/en/latest/developer_guide/developer_guide.html](https://rocm.docs.amd.com/projects/rocm-docs-core/en/latest/developer_guide/developer_guide.html)

### Build Documentation Locally

To build the `rocm-docs-core` documentation locally, run the commands below:

```bash
pip install -r requirements.txt
cd docs
python3 -m sphinx -T -E -b html -d _build/doctrees -D language=en . _build/html
```
