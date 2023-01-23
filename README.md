# ROCm Documentation Core Utilities

### Purpose
In order to maintain a uniform appearance across all of the ROCm documentation, this repository was created to contain some utilities and styling that is
common to all ROCm projects. This greatly aids in maintaining the documentation, as any change to the appearance only needs to be modified in one location.

### Common elements covered
- A couple of Javascript tweaks for tables with long variable names, as Sphinx' default rendering is problematic.
- Creation of a header and footer for the documentation page.
- Common Sphinx configuration options for ROCm documentation processes.

### Use
- Install this repository as a Python package using pip, for example `pip install git+https://RadeonOpenCompute/rocm-docs-core.git`.
- From the `rocm_docs` package import the function `setup_rocm_docs` into `conf.py` for the ReadTheDocs project.
- Call exactly the following, replacing `<PROJECT NAME HERE>` with the name of the project.
```python
(
    copyright,
    author,
    project,
    extensions,
    myst_enable_extensions,
    myst_heading_anchors,
    external_toc_path,
    external_toc_exclude_missing,
    intersphinx_mapping,
    intersphinx_disabled_domains,
    templates_path,
    epub_show_urls,
    exclude_patterns,
    html_theme,
    html_title,
    html_static_path,
    html_css_files,
    html_js_files,
    html_extra_path,
    html_theme_options,
    html_show_sphinx,
    html_favicon,
) = setup_rocm_docs(<PROJECT NAME HERE>)
```
