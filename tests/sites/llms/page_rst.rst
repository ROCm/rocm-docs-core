.. meta::
   :description lang=en: An RST page with a list-table, code block, and cross-reference.

RST page
========

Some prose on the RST page mentioning the inline literal ``hipFree``. See
:doc:`page_md` for the Markdown page.

.. list-table::
   :header-rows: 1

   * - Feature
     - RDNA
     - CDNA
   * - Atomics
     - Yes
     - Yes
   * - Wavefront size
     - 32
     - 64

.. code-block:: cpp

   __global__ void rst_kernel(double* a, size_t size) {
       int i = threadIdx.x;
       if (i < size) { a[i] = 1.0; }
   }

.. code-block:: bash

   export HIP_VISIBLE_DEVICES=0

.. note::

   Supported note body text that must be rendered.

.. tip::

   Unique tip body text that must survive conversion.

.. tab-set::

   .. tab-item:: AMD

      Use ``amdclang++`` on AMD platforms.

   .. tab-item:: NVIDIA

      Use ``nvcc`` on NVIDIA platforms.
