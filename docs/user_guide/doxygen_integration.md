# Doxygen Integration

## What

`doxysphinx` is a package that handles integration
of Doxygen and Sphinx documentation.

`doxysphinx` allows displaying Doxygen documentation in the Sphinx documentation.

`rocm-docs-core` applies some additional formatting and styling on top of this
to stay in line with our themes.

Since `doxysphinx` automatically integrates the Doxygen documentation,
developers only have to update the documentation strings in the source code
if they are formatted for Doxygen.

For more information on `doxysphinx`, see the [GitHub repository](https://github.com/boschglobal/doxysphinx)
or the [doxysphinx documentation](https://boschglobal.github.io/doxysphinx/).

## How

Some examples of how to use `doxysphinx` with `rocm-docs-core` are included below.

Assuming Doxygen documentation is already configured correctly,
several changes must be made to the configuration file (`conf.py`)
located in the `docs` folder
and the requirements files (`requirements.in` and `requirements.txt`)
located in the `sphinx` folder.

For the configuration file:

- Include the `rocm_docs.doxygen` extension in the `extensions` list.

- Include the path to the Doxygen configuration in `doxygen_root`. For ROCm projects, this value is usually `doxygen`.

- Set `doxysphinx_enabled` to True.

- Define a `doxygen_project` dictionary and set a `name` and `path`. For ROCm projects, the value of path is usually `doxygen/xml`.

For the requirements files:

- Specify the `api_reference` in the `requirements.in` (example: `rocm-docs-core[api_reference]==0.36.0`)

- Use `pip-tools` to compile the `requirements.in`

  - `pip install pip-tools`

  - `pip-compile requirements.in --resolver=backtracking`

Then add the Doxygen output to the table of contents (`_toc.yml.in`).

Optionally, specify custom style sheets to use in the Doxygen configuration (`Doxyfile`).
These style sheets are a part of `rocm-docs-core`.

- `HTML_HEADER`

- `HTML_FOOTER`

- `HTML_STYLESHEET`

- `HTML_EXTRA_STYLESHEET`

When building the documentation with the API reference enabled,
the console output will also make configuration recommendations to make
documentation builds succeed.
If documentation builds are still failing, please follow the recommendations.

This project has [Demo Doxygen Docs here](../demo/doxygen/html/index).
See the [source code](https://github.com/ROCm/rocm-docs-core) for details.

The `tests` folder in the `rocm-docs-core` project on GitHub
also has example configuration files.

See [this PR for a simple example of adding a Doxygen code snippet](https://github.com/ROCm/rocm-docs-core/pull/222).
