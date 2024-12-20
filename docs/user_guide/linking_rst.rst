.. meta::
   :description: Setting up links in RST to other projects, current project and external sites in ROCm documentation
   :keywords: RST links, Project linking, Project reference, Adding links in RST, Documentation settings


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

See the `Sphinx documentation on cross-referencing arbitrary locations <https://www.sphinx-doc.org/en/master/usage/referencing.html#ref-role>`_
for information on labels.

The format using a label would appear as follows:

.. code-block:: RST

    :ref:`Text here<project_name:label_name>`

Cross-references are achieved via Intersphinx.
For more information, refer to the
`Sphinx documentation <https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html>`_
or `Read the Docs documentation <https://docs.readthedocs.io/en/stable/guides/intersphinx.html>`_
on Intersphinx.

Example
^^^^^^^

The following RST:

.. code-block:: RST

    :ref:`ROCm for AI Install<rocm:rocm-for-ai-install>`

will be rendered as the following link:

:ref:`ROCm for AI Install<rocm:rocm-for-ai-install>`
