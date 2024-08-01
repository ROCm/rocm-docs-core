Linking in RST
==============

reStructuredText (RST)
----------------------

Cross References to Arbitrary Locations in Other Projects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `projects.yaml <https://github.com/ROCm/rocm-docs-core/blob/develop/src/rocm_docs/data/projects.yaml>`_
configuration file contains the names of projects
that should be used when making links that cross-reference documentation sites.

Cross references to anchors or arbitrary locations in documentation
can be done using labels.

See the `Sphinx documentation on cross-referencing arbitrary locations<https://www.sphinx-doc.org/en/master/usage/referencing.html#ref-role>`_
for information on labels.

The format using a label would appear as follows:

```RST
:ref:`Text here<project_name:label_name>`
```

Example
^^^^^^^

The following RST:

```RST
{doc}`ROCm Documentation<rocm:about/license>`

:ref:`ROCm for AI Install<rocm:rocm-for-ai-install>`
```

will be rendered as the following link:

{doc}`ROCm Documentation<rocm:about/license>`

:ref:`ROCm for AI Install<rocm:rocm-for-ai-install>`
