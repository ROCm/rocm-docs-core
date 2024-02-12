# Doxygen Integration

## What

`doxysphinx` is a package that handles integration
of `Doxygen` and `Sphinx` documentation.

`doxysphinx` allows displaying `Doxygen` documentation in the `Sphinx` documentation.

`rocm-docs-core` applies some additional formatting and styling on top of this
to stay in line with our themes.

Since doxysphinx automatically integrates the Doxygen documentation,
developers only have to update the documentation strings in the source code
if they are formatted for Doxygen.

## How

Assuming Doxygen documentation is already configured correctly,
call the `run_doxygen` method in the configuration file (`conf.py`)
located in the `docs` folder.
Then add the Doxygen output to the table of contents (`_toc.yml.in`)

This project has [Demo Doxygen Docs here](../demo/doxygen/html/index),
which was achieved using the [configuration here](https://github.com/RadeonOpenCompute/rocm-docs-core/blob/develop/docs/conf.py)
and the [table of contents set here](https://github.com/RadeonOpenCompute/rocm-docs-core/blob/develop/docs/sphinx/_toc.yml.in).

See [this PR for a simple example of adding a Doxygen code snippet](https://github.com/RadeonOpenCompute/rocm-docs-core/pull/222).
