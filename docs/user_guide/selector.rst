:description: Add interactive selector widgets to ROCm documentation pages so readers can filter content by OS, device, install method, or any other dimension
:keywords: selector directive, conditional content, interactive docs, ROCm docs core user guide
:selector-toc2: Example
:selector-toc2-icon: fa-solid fa-computer

Selector widget
===============

The ``rocm_docs.selector`` extension adds interactive selector widgets to
documentation pages. Readers click tiles or choose from dropdowns to select
their configuration and only the content relevant to that selection is shown.
This is useful when there are many variations of instructions that need to be
documented (such as per GPU, per OS, per installation method) and you want to
provide copy-pasteable instructions.

Enabling the extension
----------------------

Add ``rocm_docs.selector`` to the ``extensions`` list in ``conf.py``:

.. code-block:: python

   extensions = ["rocm_docs", "rocm_docs.selector"]

No other configuration is required. The extension automatically registers its
static assets (CSS, JavaScript, and the `TomSelect <https://tom-select.js.org/>`_
library for dropdowns) and sidebar template.

Markup support
--------------

Both reStructuredText and MyST-flavored Markdown are supported. RST is
preferred because nested directives — ``selector-option`` inside ``selector``,
for example — are written naturally with indentation rather than requiring
progressively wider backtick fences:

.. code-block:: rst

   .. selector:: Operating System
      :key: os

      .. selector-option:: Ubuntu
         :value: ubuntu
         :default:

      .. selector-option:: RHEL
         :value: rhel

The MyST equivalent requires an extra backtick fence level for each level of
nesting:

.. code-block:: markdown

   ````{selector} Operating System
   :key: os

   ```{selector-option} Ubuntu
   :value: ubuntu
   :default:
   ```

   ```{selector-option} RHEL
   :value: rhel
   ```
   ````

Directives
----------

.. _selector-directive:

``selector``
~~~~~~~~~~~~

Creates a row of radio-button tiles. Readers click a tile to select a value.

.. code-block:: rst

   .. selector:: Operating System
      :key: os

      .. selector-option:: Ubuntu
         :value: ubuntu
         :default:

      .. selector-option:: RHEL
         :value: rhel

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Option
     - Description
   * - ``:key:``
     - Identifier used to match conditions in ``selected-content`` blocks.
       Defaults to the title normalized to lowercase with underscores.
   * - ``:show-cond:``
     - Space-separated ``key=value`` pairs. The group is hidden unless all
       conditions are met.
   * - ``:heading-width:``
     - Width of the label column. Accepts a Bootstrap column width (1–12) or a
       CSS percentage (e.g. ``25%``). Default: ``3``.

``selector-dropdown``
~~~~~~~~~~~~~~~~~~~~~

Same as ``selector`` but renders as a dropdown instead of tiles. Accepts the
same options plus ``:sort:``.

.. code-block:: rst

   .. selector-dropdown:: OS version
      :key: ubuntu-ver
      :show-cond: os=ubuntu
      :sort: desc

      .. selector-option:: 24.04
         :value: 24.04

      .. selector-option:: 22.04
         :value: 22.04

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Option
     - Description
   * - ``:key:``
     - Identifier used to match conditions in ``selected-content`` blocks.
       Defaults to the title normalized to lowercase with underscores.
   * - ``:show-cond:``
     - Space-separated ``key=value`` pairs. The group is hidden unless all
       conditions are met.
   * - ``:heading-width:``
     - Width of the label column. Accepts a Bootstrap column width (1–12) or a
       CSS percentage (e.g. ``25%``). Default: ``3``.
   * - ``:sort:``
     - Sort options alphabetically. Accepts ``asc`` or ``desc``.

``selector-option``
~~~~~~~~~~~~~~~~~~~

An individual option within a ``selector`` or ``selector-dropdown``. Must be
nested directly inside one of those directives.

.. code-block:: rst

   .. selector-option:: Ubuntu
      :value: ubuntu
      :default:
      :width: 4

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Option
     - Description
   * - ``:value:``
     - Key written to the selector state. Defaults to the title normalized to
       lowercase. Can include extra ``key=value`` bindings separated by spaces
       (see :ref:`extra-bindings`).
   * - ``:default:``
     - Marks this option as selected on first load. If no option has
       ``:default:``, the first option is used.
   * - ``:width:``
     - Bootstrap column width (1–12) or a CSS percentage (e.g. ``25%``).
       Default: ``6``.
   * - ``:alt-name:``
     - Alternate display text used in dropdown mode.
   * - ``:toc-label:``
     - Label shown in the secondary sidebar instead of the option title.
   * - ``:show-cond:``
     - Space-separated ``key=value`` pairs. The option is hidden unless all
       conditions are met.
   * - ``:disable-cond:``
     - Space-separated ``key=value`` pairs. The option is disabled (greyed out)
       when all conditions are met.

.. _extra-bindings:

Extra bindings
^^^^^^^^^^^^^^

A ``selector-option`` can set additional selector keys when chosen by embedding
``key=value`` pairs in the ``:value:`` option after the option's own value:

.. code-block:: rst

   .. selector-option:: MI355X
      :value: mi355x gfx=gfx950 arch=cdna3

When "MI355X" is selected, the state is updated with ``mi355x`` as the value
for the option's group key, and ``gfx=gfx950`` and ``arch=cdna3`` are also set.
This allows downstream ``selected-content`` blocks to condition on ``gfx`` or
``arch`` without a separate visible selector.

``selector-info``
~~~~~~~~~~~~~~~~~

An informational icon added to a selector group heading. Clicking it opens a
link. Must be nested inside a ``selector`` or ``selector-dropdown``.

.. code-block:: rst

   .. selector:: AMD GPU
      :key: gpu

      .. selector-info:: https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html
         :icon: fa-solid fa-circle-info fa-lg

      .. selector-option:: MI355X
         :value: mi355x

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Option
     - Description
   * - ``:icon:``
     - FontAwesome icon class. Default: ``fa-solid fa-circle-info fa-lg``.

``selected-content`` / ``selected``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A block of content shown only when its condition matches the current selector
state. ``selected`` is an alias for ``selected-content``.

.. code-block:: rst

   .. selected-content:: os=ubuntu
      :heading: Ubuntu installation

      Steps for Ubuntu go here.

   .. selected-content:: os=rhel
      :heading: RHEL installation

      Steps for RHEL go here.

Conditions are space-separated ``key=value`` pairs. Multiple values for the
same key are OR'd:

.. code-block:: rst

   .. selected-content:: os=ubuntu os=debian
      :heading: Debian-based installation

      Shown for Ubuntu or Debian.

Mixing keys in a single ``selected-content`` condition is discouraged — it
becomes difficult to reason about on pages with many selectors. Prefer using
one key per ``selected-content`` block and layering content by chaining
selectors.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Option
     - Description
   * - ``:heading:``
     - Section heading rendered inside the block. Creates an anchor link.
   * - ``:heading-level:``
     - Heading level (2–6). Default: ``2``.
   * - ``:class:``
     - Extra CSS class added to the container element.
   * - ``:id:``
     - Custom HTML ``id`` attribute.
   * - ``:no-pdf:``
     - Excludes this block from PDF output even when PDF generation is enabled.

Basic example
-------------

.. selector:: Linux distribution
   :key: distro

   .. selector-option:: Debian
      :value: debian
      :width: 20%

   .. selector-option:: Ubuntu
      :value: ubuntu
      :width: 20%

   .. selector-option:: Fedora
      :value: fedora
      :width: 20%

   .. selector-option:: RHEL
      :value: rhel
      :width: 20%

   .. selector-option:: Oracle Linux
      :value: ol
      :width: 20%

.. selector:: Installation method
   :key: i
   :show-cond: distro=debian distro=ubuntu

   .. selector-option:: apt
      :value: pkgman

   .. selector-option:: pip
      :value: pip

.. selector:: Installation method
   :key: i
   :show-cond: distro=fedora distro=rhel distro=sles

   .. selector-option:: dnf
      :value: pkgman
      :width: 100%

.. selected:: i=pkgman

   .. selected:: distro=ubuntu distro=debian
      :heading: Install using apt
      :heading-level: 3

      Example:

      .. code-block:: bash

         sudo apt update

   .. selected:: distro=fedora distro=rhel distro=ol
      :heading: Install using dnf
      :heading-level: 3

      Example:

      .. code-block:: bash

         sudo dnf check-update

.. selected:: i=pip
   :heading: Install using pip
   :heading-level: 3

   Example:

   .. code-block:: bash

      pip install -r requirements.txt

.. code-block:: rst

   .. selector:: Linux distribution
      :key: distro

      .. selector-option:: Debian
         :value: debian
         :width: 25%

      .. selector-option:: Ubuntu
         :value: ubuntu
         :width: 25%

      .. selector-option:: Fedora
         :value: fedora
         :width: 25%

      .. selector-option:: RHEL
         :value: rhel
         :width: 25%

   .. selector:: Installation method
      :key: i
      :show-cond: distro=debian distro=ubuntu

      .. selector-option:: apt
         :value: pkgman

      .. selector-option:: pip
         :value: pip

   .. selector:: Installation method
      :key: i
      :show-cond: distro=fedora distro=rhel

      .. selector-option:: dnf
         :value: pkgman
         :width: 100%

   .. selected:: i=pkgman

      .. selected:: distro=ubuntu distro=debian
         :heading: Example: Install on Ubuntu or Debian
         :heading-level: 3

         Example:

         .. code-block:: bash

            sudo apt install

      .. selected:: distro=fedora distro=rhel
         :heading: Example: Install on Fedora or Red Hat Enterprise Linux
         :heading-level: 3

         Example:

         .. code-block:: bash

            sudo dnf install

   .. selected:: i=pip
      :heading: Example: Install using pip
      :heading-level: 3

      Example:

      .. code-block:: bash

         pip install -r requirements.txt

Secondary sidebar panel
-----------------------

Pages with selectors can display a secondary sidebar that shows the active
selections and a filtered heading list. The sidebar has two sections:

- **Options** — a compact dropdown for each visible selector group, mirroring
  the page's tile/dropdown widgets so readers can change selections without
  scrolling back up.
- **Contents** — a filtered heading list that shows only the headings currently
  visible given the active selections.

Enabling the sidebar
~~~~~~~~~~~~~~~~~~~~

Add the following `field list
<https://www.sphinx-doc.org/en/master/usage/restructuredtext/field-lists.html>`__
metadata at the top of your page:

.. code-block:: rst

   :selector-toc2: Installation environment
   :selector-toc2-icon: fa-solid fa-computer

In MyST Markdown:

.. code-block:: yaml

   ---
   myst:
     html_meta:
       "selector-toc2": "Installation environment"
       "selector-toc2-icon": "fa-solid fa-computer"
   ---

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Metadata key
     - Description
   * - ``selector-toc2``
     - Title shown at the top of the secondary sidebar. Required to activate
       the sidebar.
   * - ``selector-toc2-icon``
     - `FontAwesome <https://fontawesome.com/search?ic=free-collection>`__ icon
       class displayed next to the title. Optional.

The extension automatically registers the ``selector-toc2`` sidebar template
and adds it to the secondary sidebar for any page that sets the
``selector-toc2`` metadata key.

Controlling the label in the Options section
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default the label shown in the sidebar dropdown for each ``selector-option``
is the option's title text. Use ``:toc-label:`` to override it:

.. code-block:: rst

   .. selector-option:: Ubuntu 24.04 LTS
      :value: ubuntu-24
      :toc-label: 24.04

PDF output
----------

By default, ``selected-content`` blocks are omitted from PDF (LaTeX) output.
Set ``rocm_docs_pdf_mock_selector_state = True`` in ``conf.py`` to expand all
selector combinations into separate sections in the PDF:

.. code-block:: python

   rocm_docs_pdf_mock_selector_state = True

To limit the PDF to a specific subset of combinations, pass a dict that maps
each page's docname to a list of simulated selector selections. Each entry
represents the selector state as if a user had made those choices — only
combinations matching at least one entry are included:

.. code-block:: python

   rocm_docs_pdf_mock_selector_state = {
       "install/rocm": [
           {"os": "ubuntu", "ubuntu-ver": "24.04", "i": "pkgman"},
           {"os": "rhel", "rhel-ver": "9.4", "i": "pkgman"},
           {"os": "windows"},
       ],
   }

Each entry is a partial match — keys not listed act as wildcards. Key names
must match the ``:key:`` values declared in the ``selector`` directives of
your source files. If a key does not match any combo dimension, the build
will fail with an error listing the available dimensions.

Excluding pages from PDF
~~~~~~~~~~~~~~~~~~~~~~~~

To exclude source files from PDF output (e.g. HTML-only redirect stubs), set
``rocm_docs_pdf_exclude_patterns`` in ``conf.py``:

.. code-block:: python

   rocm_docs_pdf_exclude_patterns = ["how-to/archive/*"]

The patterns are standard Sphinx source-file globs, appended to
``exclude_patterns`` only for LaTeX builds.  If the excluded files are
referenced by a toctree, add ``"etoc.ref"`` and ``"toc.excluded"`` to
``suppress_warnings`` to silence the resulting warnings.

LLM output
----------

``selected-content`` blocks are included in ``llms-full.txt`` by default,
prefixed with a bold label showing the condition and heading so that mutually
exclusive variants are not conflated. Set
``rocm_selector_markdown_generation = False`` to exclude selector content from
LLM output:

.. code-block:: python

   rocm_selector_markdown_generation = False
