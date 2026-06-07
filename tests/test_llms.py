"""Tests for rocm_docs.llms — llms-full.txt generation."""

from __future__ import annotations

from typing import Any

import unittest.mock
from pathlib import Path

import pytest

from rocm_docs.llms import _is_prose_line, _should_skip, generate_llms_full

# ---------------------------------------------------------------------------
# _should_skip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "parts",
    [
        ("_build", "index.md"),
        ("_templates", "base.html"),
        ("_static", "custom.css"),
        (".git", "config"),
        (".venv", "pyvenv.cfg"),
    ],
)
def test_should_skip_excluded_dirs(parts: tuple[str, ...]) -> None:
    assert _should_skip(Path(*parts))


@pytest.mark.parametrize(
    "parts",
    [
        ("docs", "index.md"),
        ("how-to", "setup.rst"),
        ("reference", "api.md"),
    ],
)
def test_should_skip_included_dirs(parts: tuple[str, ...]) -> None:
    assert not _should_skip(Path(*parts))


# ---------------------------------------------------------------------------
# _is_prose_line — lines that should be kept
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "This is a normal sentence.",
        "You can use hipSetDevice to select a device.",
        ":cpp:func:`hipMalloc` allocates device memory.",
        ":ref:`some-label <target>` describes the feature.",
        "Use ``rocm-smi`` to monitor GPU usage.",
        "The value of ``x`` must be positive.",
        "  Indented prose inside a code block.",
        "kernel<<<grid, block>>>(args);",
        "std::vector<float> data;",
        "template<typename T>",
        "| Environment Variable | Type | Default |",
        # RST multi-line inline hyperlink — URL continuation line must be kept
        "<https://github.com/ROCm/rccl>`_.",
        "<https://rocm.docs.amd.com/en/latest/>`_",
    ],
)
def test_is_prose_line_kept(line: str) -> None:
    assert _is_prose_line(line), f"Expected kept: {line!r}"


# ---------------------------------------------------------------------------
# _is_prose_line — lines that should be dropped
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        # Empty / blank
        "",
        "   ",
        # MyST fences
        "```python",
        "```{note}",
        ":::",
        # Directive options (bare)
        "align: center",
        "alt:",
        "name: my-figure",
        # MyST/RST anchor labels
        "(some-label)=",
        "(my-ref)=",
        # RST directives and comments
        ".. code-block:: python",
        ".. note::",
        ".. _target:",
        ".. |sub| replace:: text",
        # RST field list items (not inline roles)
        ":type: int",
        # RST section underlines
        "================",
        "----------------",
        "~~~~~~~~~~~~~~~~",
        # Sphinx-design badge lines
        "{bdg-primary}`label`",
        # HTML comment close
        "-->",
        # HTML tags (caught by _HTML_TAG_RE, not MARKUP_PREFIXES)
        '<div class="note">',
        "</section>",
        "<!DOCTYPE html>",
        # sphinx-tags badge
        ":img-top: image.png",
        # RST .. meta:: options with extended field names (space + qualifier)
        ":description lang=en: AMD Instinct GPU architecture",
        # YAML frontmatter key-value pairs (double-quoted keys)
        '"description lang=en": "AMD Instinct GPU architecture"',
        # Markdown table separator rows
        "|-----|------|---------|-------------|",
        "| :--- | ---: |",
    ],
)
def test_is_prose_line_dropped(line: str) -> None:
    assert not _is_prose_line(line), f"Expected dropped: {line!r}"


# ---------------------------------------------------------------------------
# generate_llms_full
# ---------------------------------------------------------------------------


def _make_app(
    srcdir: Path, outdir: Path, project: str = "My Project"
) -> unittest.mock.NonCallableMock:
    app = unittest.mock.NonCallableMock()
    app.srcdir = srcdir
    app.outdir = outdir
    app.config = unittest.mock.NonCallableMock()
    app.config.project = project
    return app


def test_generate_llms_full_skips_on_exception(tmp_path: Path) -> None:
    """generate_llms_full does nothing when exception is not None."""
    app = _make_app(tmp_path, tmp_path)
    generate_llms_full(app, RuntimeError("build failed"))
    assert not (tmp_path / "llms-full.txt").exists()


def test_generate_llms_full_uses_llms_txt_header(tmp_path: Path) -> None:
    """The content of llms.txt is used as the header section."""
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    (srcdir / "llms.txt").write_text(
        "# Custom Header\n\nSome intro text.", encoding="utf-8"
    )
    # A minimal doc file with enough prose lines
    prose = "\n".join([f"This is sentence number {i}." for i in range(12)])
    (srcdir / "index.md").write_text(prose, encoding="utf-8")

    app = _make_app(srcdir, outdir, project="Ignored Project")
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    assert output.startswith("# Custom Header")
    assert "Ignored Project" not in output


def test_generate_llms_full_fallback_header(tmp_path: Path) -> None:
    """When llms.txt is absent, the Sphinx project name is used as the header."""
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    prose = "\n".join([f"Sentence {i} of the document." for i in range(12)])
    (srcdir / "index.md").write_text(prose, encoding="utf-8")

    app = _make_app(srcdir, outdir, project="ROCm HIP")
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    assert output.startswith("# ROCm HIP")


def test_generate_llms_full_skips_short_files(tmp_path: Path) -> None:
    """Files with fewer than MIN_PROSE_LINES prose lines are excluded."""
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    (srcdir / "stub.md").write_text(
        "Too short.\n\nOnly two lines.", encoding="utf-8"
    )

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    assert "stub.md" not in output


def test_generate_llms_full_excludes_build_dir(tmp_path: Path) -> None:
    """Files inside excluded directories are not included."""
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    build_dir = srcdir / "_build"
    build_dir.mkdir()
    prose = "\n".join([f"Line {i} of excluded content." for i in range(12)])
    (build_dir / "excluded.md").write_text(prose, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    assert "excluded.md" not in output


def test_generate_llms_full_includes_rst_code_blocks(tmp_path: Path) -> None:
    """RST code blocks (indented content after .. code-block::) are preserved."""
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    rst_content = "\n".join(
        [
            "Introduction to HIP.",
            "",
            "Here is an example:",
            "",
            ".. code-block:: cpp",
            "",
            "   hipSetDevice(0);",
            "   hipMalloc(&ptr, size);",
            "",
            "After the code block, prose continues here.",
            "You can call hipFree to release the allocation.",
            "Additional context about memory management.",
            "Remember to check the return value.",
            "Error handling is important for robustness.",
            "See the HIP documentation for more details.",
            "The device must be initialised before use.",
        ]
    )
    (srcdir / "hip_intro.rst").write_text(rst_content, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    assert "hipSetDevice(0);" in output
    assert "hipMalloc(&ptr, size);" in output


def test_generate_llms_full_drops_rst_directive_line(tmp_path: Path) -> None:
    """The .. code-block:: directive line itself is not included in output."""
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    rst_content = "\n".join(
        [
            "Some introductory prose about the topic.",
            "This covers the basic usage patterns.",
            "A third sentence to add more context.",
            "A fourth sentence for additional detail.",
            "",
            ".. code-block:: python",
            "",
            "   print('hello')",
            "",
            "More prose follows to pad the file.",
            "This ensures the file has enough lines.",
            "We need at least ten prose lines total.",
            "Here is line ten of actual content.",
            "And one more for good measure.",
        ]
    )
    (srcdir / "example.rst").write_text(rst_content, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    assert ".. code-block::" not in output
    assert "print('hello')" in output


def test_generate_llms_full_preserves_myst_fences(tmp_path: Path) -> None:
    """MyST backtick fences and their content are preserved intact."""
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    md_content = "\n".join(
        [
            "Introduction paragraph with enough context.",
            "This document explains how to use the API.",
            "A third sentence to meet the prose threshold.",
            "A fourth sentence for completeness.",
            "",
            "```python",
            "import hip",
            "hip.hipSetDevice(0)",
            "```",
            "",
            "Additional prose after the code block.",
            "More explanation of the above example.",
            "Refer to the API reference for full details.",
            "The function returns zero on success.",
        ]
    )
    (srcdir / "guide.md").write_text(md_content, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    assert "```python" in output
    assert "import hip" in output
    assert "hip.hipSetDevice(0)" in output
    assert "```" in output


def test_generate_llms_full_hip_example(tmp_path: Path) -> None:
    """HIP kernel launch syntax and angle brackets in code blocks are preserved.

    This is a regression test for the original bug where lines containing
    angle brackets (e.g. kernel<<<grid, block>>>(...) or std::vector<int>)
    were incorrectly dropped by the prose filter.
    """
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    rst_content = "\n".join(
        [
            "Vector addition example using HIP.",
            "",
            "This example demonstrates how to add two vectors on a GPU.",
            "It uses the HIP runtime API for device memory management.",
            "The kernel is launched with a grid of blocks and threads.",
            "",
            ".. code-block:: cpp",
            "",
            "   #include <hip/hip_runtime.h>",
            "   #include <vector>",
            "",
            "   __global__ void add(int *a, int *b, int *c, std::size_t size)",
            "   {",
            "       const std::size_t index = threadIdx.x + blockDim.x * blockIdx.x;",
            "       if(index < size)",
            "       {",
            "           c[index] += a[index] + b[index];",
            "       }",
            "   }",
            "",
            "   int main()",
            "   {",
            "       constexpr int numOfBlocks = 256;",
            "       constexpr int threadsPerBlock = 256;",
            "       constexpr std::size_t arraySize = 1U << 16;",
            "",
            "       std::vector<int> a(arraySize), b(arraySize), c(arraySize);",
            "       int *d_a, *d_b, *d_c;",
            "",
            "       HIP_CHECK(hipMalloc(&d_a, arraySize * sizeof(int)));",
            "       HIP_CHECK(hipMalloc(&d_b, arraySize * sizeof(int)));",
            "       HIP_CHECK(hipMalloc(&d_c, arraySize * sizeof(int)));",
            "",
            "       add<<<numOfBlocks, threadsPerBlock>>>(d_a, d_b, d_c, arraySize);",
            "       HIP_CHECK(hipGetLastError());",
            "       HIP_CHECK(hipDeviceSynchronize());",
            "",
            "       HIP_CHECK(hipFree(d_a));",
            "       HIP_CHECK(hipFree(d_b));",
            "       HIP_CHECK(hipFree(d_c));",
            "   }",
        ]
    )
    (srcdir / "hip_add.rst").write_text(rst_content, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    # Kernel launch syntax with triple angle brackets must be preserved.
    assert (
        "add<<<numOfBlocks, threadsPerBlock>>>(d_a, d_b, d_c, arraySize);"
        in output
    )
    # C++ template syntax with angle brackets must be preserved.
    assert (
        "std::vector<int> a(arraySize), b(arraySize), c(arraySize);" in output
    )
    # Regular HIP API calls must be preserved.
    assert "HIP_CHECK(hipMalloc(&d_a, arraySize * sizeof(int)));" in output
    assert "HIP_CHECK(hipDeviceSynchronize());" in output
    # The directive line itself must not appear.
    assert ".. code-block::" not in output


def test_generate_llms_full_skips_rst_raw_html(tmp_path: Path) -> None:
    """Content inside .. raw:: html blocks is excluded from the output."""
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    rst_content = "\n".join(
        [
            "Introduction to the MI300X GPU.",
            "",
            ".. raw:: html",
            "",
            '   <meta name="keywords" content="MI300X, AMD Instinct">',
            '   <p>MI300X, AMD Instinct"></p>',
            "",
            "The MI300X accelerator is designed for AI workloads.",
            "It features 192 GB of HBM3 memory.",
            "The peak memory bandwidth exceeds 5 TB/s.",
            "Multiple compute dies are connected via Infinity Fabric.",
            "It supports PCIe 5.0 for host communication.",
            "The device can be used for LLM inference and training.",
            "ROCm provides the software stack for this hardware.",
            "See the MI300X documentation for full specifications.",
            "The architecture supports FP8, BF16, and FP32 formats.",
            "Tensor parallelism is well-supported across devices.",
        ]
    )
    (srcdir / "mi300x.rst").write_text(rst_content, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    assert 'content="MI300X, AMD Instinct"' not in output
    assert "MI300X, AMD Instinct" not in output
    assert "MI300X accelerator" in output


def test_generate_llms_full_skips_meta_directive_options(
    tmp_path: Path,
) -> None:
    """RST .. meta:: options with extended field names are excluded."""
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    rst_content = "\n".join(
        [
            ".. meta::",
            "   :description lang=en: MI100 GPU architecture overview",
            "   :keywords: MI100, AMD Instinct, GPU",
            "",
            "Introduction to the MI100 GPU.",
            "The MI100 was AMD's first Instinct GPU based on CDNA architecture.",
            "It features 32 GB of HBM2 memory.",
            "The peak FP64 performance is 11.5 TFLOPS.",
            "ROCm supports MI100 with a full software stack.",
            "The device is suitable for HPC and AI workloads.",
            "Multiple MI100 GPUs can be connected via Infinity Fabric.",
            "See the AMD documentation for full specifications.",
            "The MI100 supports PCIe 4.0 for host communication.",
            "Matrix operations are accelerated via the Matrix Core Engine.",
        ]
    )
    (srcdir / "mi100.rst").write_text(rst_content, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    assert ":description lang=en:" not in output
    assert "MI100 GPU" in output


def test_generate_llms_full_preserves_rst_multiline_hyperlinks(
    tmp_path: Path,
) -> None:
    """RST multi-line inline hyperlinks are preserved intact in the output.

    In RST a hyperlink can span two lines::

        `link text
        <https://example.com>`_

    The second line starts with ``<https://...>``.  It must NOT be dropped by
    the HTML-tag filter because it is not an HTML tag — it is a URL wrapped in
    angle brackets as part of an RST inline hyperlink reference.
    """
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    rst_content = "\n".join(
        [
            "Overview of ROCm Communication Libraries.",
            "",
            "You can verify UCC and ROCm version compatibility using the `communication libraries tables",
            "<https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html>`_.",
            "",
            "Additional prose about GPU-to-GPU communication.",
            "The RCCL library enables collective operations across GPUs.",
            "You can install RCCL via the ROCm package repository.",
            "review and implement the `rccl test install script",
            "<https://github.com/ROCm/rccl>`_.",
            "MPI libraries can also be used alongside RCCL.",
            "See the RCCL documentation for configuration options.",
            "Bandwidth depends on the interconnect topology.",
        ]
    )
    (srcdir / "comms.rst").write_text(rst_content, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    # The URL continuation line must be present so the hyperlink reads correctly.
    assert (
        "<https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html>`_."
        in output
    )
    assert "<https://github.com/ROCm/rccl>`_." in output
    # The surrounding prose sentences must also be intact.
    assert "communication libraries tables" in output
    assert "rccl test install script" in output


def test_generate_llms_full_drops_multiline_html_tag_continuation(
    tmp_path: Path,
) -> None:
    """Multi-line HTML opening tags discard their attribute continuation lines.

    A ``<meta>`` tag whose ``content`` attribute value wraps to a second line
    produces a continuation such as ``  MI100, AMD Instinct">`` that does not
    start with ``<``.  Without state tracking this line passes through the
    prose filter and appears verbatim in the output.  The fix tracks the
    unclosed-tag state and discards all lines until the closing ``>`` is seen.
    """
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    md_content = "\n".join(
        [
            "<head>",
            '  <meta name="keywords" content="GPU architecture, MI200, MI250, RDNA,',
            '  MI100, AMD Instinct">',
            "</head>",
            "",
            "# GPU architecture documentation",
            "",
            "This page covers AMD Instinct GPU architectures.",
            "The MI300 series is based on the CDNA 3 architecture.",
            "The MI200 series is based on the CDNA 2 architecture.",
            "Each generation improves on memory bandwidth and compute.",
            "ROCm provides a unified software stack across all devices.",
            "See the hardware documentation for detailed specifications.",
            "Performance counters are available for profiling workloads.",
            "The architecture supports FP64, FP32, FP16, and BF16 formats.",
            "Compute Units expose vector and matrix execution pipelines.",
            "Each device exposes telemetry through rocm-smi for monitoring.",
        ]
    )
    (srcdir / "gpu-arch.md").write_text(md_content, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    # The continuation line of the wrapped <meta> attribute must not appear.
    assert 'MI100, AMD Instinct">' not in output
    # Surrounding prose must be preserved.
    assert "GPU architecture documentation" in output
    assert "CDNA 3 architecture" in output


def test_generate_llms_full_strips_trailing_html_close_tags(
    tmp_path: Path,
) -> None:
    """Trailing HTML close tags on prose lines are stripped from the output.

    Sphinx-design card bodies sometimes contain lines like::

        Browse blogs detailing ROCm workloads.</p>

    where a closing tag is appended to an otherwise plain prose sentence.
    The sentence should appear in the output without the trailing tag.
    """
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    md_content = "\n".join(
        [
            "# ROCm Data Science",
            "",
            "View the source code for all ROCm-DS components on Github.</p>",
            "Browse blogs detailing ROCm data-science workloads.</p>",
            "Installation instructions are available in the documentation.</li>",
            "The library supports NumPy, PyTorch, and TensorFlow workflows.",
            "GPU acceleration is enabled transparently via ROCm.",
            "Multiple GPUs can be used with data-parallel training.",
            "See the quickstart guide to set up your environment.",
            "All major Linux distributions are supported.",
            "Binary packages are available via pip and conda.",
        ]
    )
    (srcdir / "index.md").write_text(md_content, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    # Text content must be present, close tags must be absent.
    assert (
        "View the source code for all ROCm-DS components on Github." in output
    )
    assert "Browse blogs detailing ROCm data-science workloads." in output
    assert (
        "Installation instructions are available in the documentation."
        in output
    )
    assert "</p>" not in output
    assert "</li>" not in output


def test_generate_llms_full_drops_html_comment_body(tmp_path: Path) -> None:
    """Content inside HTML comment blocks (<!-- ... -->) is excluded.

    HTML comments span multiple lines::

        <!--
        We need performance data about the P2P communication here.
        -->

    The opener (``<!--``) and closer (``-->``) are already filtered, but the
    body lines are plain text that pass the prose filter without state tracking.
    """
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    md_content = "\n".join(
        [
            "# P2P communication",
            "",
            "AMD Instinct GPUs support peer-to-peer memory access.",
            "Low-latency AMD Infinity Fabric links connect GPUs in a node.",
            "",
            "<!---",
            "We need performance data about the P2P communication here.",
            "-->",
            "",
            "The NPS setting controls how memory is partitioned across dies.",
            "ROCm exposes P2P transfers via the hipMemcpyPeer API.",
            "Bandwidth is determined by the Infinity Fabric link speed.",
            "The topology can be queried with rocm-smi --showtopo.",
            "NUMA-aware placement improves overall system throughput.",
            "Use hipMemcpyPeerAsync for non-blocking transfers between GPUs.",
            "Check the supported peer pairs before enabling P2P access.",
            "Performance counters surface bandwidth utilisation per link.",
            "Synchronisation primitives coordinate transfers across streams.",
            "Profiling tools can attribute traffic to specific source GPUs.",
        ]
    )
    (srcdir / "mi300.md").write_text(md_content, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    # The placeholder comment body must not appear.
    assert "We need performance data" not in output
    # Surrounding prose must be preserved.
    assert "Infinity Fabric links connect GPUs" in output
    assert "hipMemcpyPeer" in output


def test_generate_llms_full_drops_inline_html_comment(tmp_path: Path) -> None:
    """Single-line HTML comments (<!-- comment -->) are discarded entirely."""
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    md_content = "\n".join(
        [
            "# Installation guide",
            "",
            "<!-- TODO: add package manager instructions -->",
            "",
            "Install ROCm using the package manager for your distribution.",
            "Ubuntu and RHEL are officially supported Linux distributions.",
            "Follow the pre-installation checklist before running the installer.",
            "Verify the installation with rocm-smi after completing setup.",
            "The ROCm version must match the supported driver version.",
            "Check compatibility with your GPU model before upgrading.",
            "Documentation for each release is available on ROCm Docs.",
            "File issues on GitHub if you encounter installation problems.",
            "Pre-built packages are available for Ubuntu, RHEL, and SLES.",
        ]
    )
    (srcdir / "install.md").write_text(md_content, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    assert "TODO" not in output
    assert "add package manager instructions" not in output
    assert "Install ROCm using the package manager" in output


def test_generate_llms_full_drops_punctuation_only_after_html_strip(
    tmp_path: Path,
) -> None:
    """Lines that are only punctuation after stripping trailing HTML are dropped.

    Source pattern: a paragraph whose continuation line is just ``.</p>``
    (an artefact of sphinx-design grid cards).  After ``</p>`` is stripped the
    remaining content is a bare ``.`` with no word characters — it should be
    silently discarded rather than emitted as a lone period.
    """
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    # Source pattern: a paragraph line followed by a ".</p>" continuation,
    # as produced by sphinx-design grid cards.  The ".</p>" line passes
    # _is_prose_line (it starts with "."), so _TRAILING_HTML_CLOSE_RE strips
    # "</p>", leaving a bare "." that should then be discarded.
    md_content = "\n".join(
        [
            "# ROCm Data Science Toolkit",
            "",
            "Install ROCm using the package manager for your distribution.",
            "Ubuntu and RHEL are officially supported Linux distributions.",
            ".</p>",
            "Follow the pre-installation checklist before running the installer.",
            "Verify the installation with rocm-smi after completing setup.",
            "The ROCm version must match the supported driver version.",
            "Check compatibility with your GPU model before upgrading.",
            "Documentation for each release is available on ROCm Docs.",
            "File issues on GitHub if you encounter installation problems.",
            "Pre-built packages are available for Ubuntu, RHEL, and SLES.",
        ]
    )
    (srcdir / "index.md").write_text(md_content, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    # The bare "." artifact must not appear as a standalone line.
    assert "\n.\n" not in output
    assert "\n. \n" not in output
    # Real prose must be preserved.
    assert "Ubuntu and RHEL" in output
    assert "Follow the pre-installation checklist" in output


def test_generate_llms_full_output_ends_with_newline(tmp_path: Path) -> None:
    """The output file always ends with a newline."""
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    raw = (outdir / "llms-full.txt").read_bytes()
    assert raw.endswith(b"\n")


# ---------------------------------------------------------------------------
# Fix #1 — gate counts emitted lines, not pre-filter prose-like lines
# ---------------------------------------------------------------------------


def test_gate_counts_emitted_lines_not_raw_prose(tmp_path: Path) -> None:
    """A file whose `_is_prose_line` count meets MIN_PROSE_LINES but whose
    actual emission falls below it is skipped under the new gate.

    Before the fix this file would pass the gate (it has 12 prose-shaped
    lines after the simple per-line check) but then emit nothing because all
    its content lives inside a `.. raw:: html` block that the state machine
    discards.  After the fix, the gate sees the empty emission and skips.
    """
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    rst_content = "\n".join(
        [
            ".. raw:: html",
            "",
            "   First line of HTML-only content.",
            "   Second line of HTML-only content.",
            "   Third line of HTML-only content.",
            "   Fourth line of HTML-only content.",
            "   Fifth line of HTML-only content.",
            "   Sixth line of HTML-only content.",
            "   Seventh line of HTML-only content.",
            "   Eighth line of HTML-only content.",
            "   Ninth line of HTML-only content.",
            "   Tenth line of HTML-only content.",
            "   Eleventh line of HTML-only content.",
            "   Twelfth line of HTML-only content.",
        ]
    )
    (srcdir / "raw_only.rst").write_text(rst_content, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    # The file produces no emittable content, so it must not appear at all.
    assert "raw_only.rst" not in output
    assert "HTML-only content" not in output


def test_gate_accepts_fenced_code_when_state_machine_keeps_it(
    tmp_path: Path,
) -> None:
    """A file that is mostly fenced code passes the gate when the state
    machine emits its content, even though `_is_prose_line` rejects fence
    interior lines individually.
    """
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    # Two short prose lines + a long fenced code block.  Under the old gate
    # the file would be rejected (only 2 prose-shaped lines).  Under the new
    # gate the fence interior is part of `kept`, so the gate passes.
    md_content = "\n".join(
        [
            "# Kernel example",
            "",
            "Short note.",
            "Another short note.",
            "",
            "```cpp",
            "void kernel_a() {}",
            "void kernel_b() {}",
            "void kernel_c() {}",
            "void kernel_d() {}",
            "void kernel_e() {}",
            "void kernel_f() {}",
            "void kernel_g() {}",
            "void kernel_h() {}",
            "void kernel_i() {}",
            "void kernel_j() {}",
            "```",
        ]
    )
    (srcdir / "kernels.md").write_text(md_content, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    assert "kernel_a" in output
    assert "kernel_j" in output


# ---------------------------------------------------------------------------
# Fix #3 — synthetic section heading uses the page's first `#` heading
# ---------------------------------------------------------------------------


def test_section_heading_uses_first_md_heading_when_present(
    tmp_path: Path,
) -> None:
    """When a Markdown file has a `#` heading, the section title in the
    aggregated output uses that heading text rather than the file path.
    The file path is recorded separately as a `_Source: ..._` line.
    """
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    md_content = "\n".join(
        [
            "# Installation guide",
            "",
            "Install ROCm via the package manager for your distribution.",
            "Ubuntu and RHEL are officially supported Linux distributions.",
            "Follow the pre-installation checklist before installing.",
            "Verify the installation with rocm-smi after completing setup.",
            "The ROCm version must match the supported driver version.",
            "Check compatibility with your GPU model before upgrading.",
            "Documentation for each release is available on ROCm Docs.",
            "File issues on GitHub if you encounter installation problems.",
            "Pre-built packages are available for Ubuntu, RHEL, and SLES.",
            "Container images are also published on Docker Hub.",
        ]
    )
    (srcdir / "install.md").write_text(md_content, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    # The synthetic section heading uses the file's own `#` heading.
    assert "## Installation guide" in output
    # The file path is recorded as metadata, not as the heading.
    assert "_Source: `install.md`_" in output
    # The path no longer appears as an H1 heading.
    assert "# install.md" not in output


def test_section_heading_falls_back_to_path_when_no_md_heading(
    tmp_path: Path,
) -> None:
    """When a file has no `#` heading (typical of `.rst` files), the section
    title falls back to the file path so each section is still labelled.
    """
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    rst_content = "\n".join(
        [
            "Setup notes",
            "===========",
            "",
            "Configure the device before use.",
            "Set the visible devices via HIP_VISIBLE_DEVICES.",
            "Confirm the runtime with rocminfo before launching workloads.",
            "Reserve memory using hipMalloc and release it with hipFree.",
            "Use hipDeviceSynchronize to wait for outstanding work.",
            "Check error codes returned by every HIP API call.",
            "Run rocm-smi to inspect device utilisation.",
            "Build the example with hipcc and link against the runtime.",
            "Profile with rocprof to identify hotspots.",
            "Adjust block and grid dimensions to match the workload.",
        ]
    )
    (srcdir / "setup.rst").write_text(rst_content, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    # Fallback: section heading is the relative file path.
    assert "## setup.rst" in output


def test_section_heading_ignores_md_heading_inside_code_fence(
    tmp_path: Path,
) -> None:
    """A `#` inside a fenced code block is not treated as the page heading.

    Source files sometimes show shell prompts (``# install rocm``) inside a
    fence.  Those must not become the page's section title.
    """
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    md_content = "\n".join(
        [
            "```bash",
            "# install rocm",
            "apt install rocm",
            "```",
            "",
            "# Real page heading",
            "",
            "Install ROCm via the package manager for your distribution.",
            "Ubuntu and RHEL are officially supported Linux distributions.",
            "Follow the pre-installation checklist before installing.",
            "Verify the installation with rocm-smi after completing setup.",
            "The ROCm version must match the supported driver version.",
            "Check compatibility with your GPU model before upgrading.",
            "Documentation for each release is available on ROCm Docs.",
            "File issues on GitHub if you encounter installation problems.",
            "Pre-built packages are available for Ubuntu, RHEL, and SLES.",
            "Container images are also published on Docker Hub.",
        ]
    )
    (srcdir / "fenced.md").write_text(md_content, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    assert "## Real page heading" in output
    assert "## install rocm" not in output


# ---------------------------------------------------------------------------
# Fix #4 — additional regression coverage for the rstrip-chain replacement
# ---------------------------------------------------------------------------


def test_llms_txt_header_preserves_trailing_dashes_in_content(
    tmp_path: Path,
) -> None:
    """Trailing `-` characters in real `llms.txt` content are preserved.

    The old `.rstrip().rstrip("-").rstrip()` chain would eat any trailing
    dashes from the last non-blank line — including legitimate ones (e.g.
    a hyphenated word at end of file).  The replacement only drops a literal
    trailing `\\n---` separator line.
    """
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    # Header content whose last line ends with real dashes.
    (srcdir / "llms.txt").write_text("# Project rocm-docs-\n", encoding="utf-8")
    # A doc file so the run produces output.
    prose = "\n".join(
        [f"Sentence number {i} for padding the file." for i in range(12)]
    )
    (srcdir / "index.md").write_text(prose, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    # The trailing dash on the header line must survive intact.
    assert output.startswith("# Project rocm-docs-")


def test_llms_txt_header_strips_trailing_hr_separator(tmp_path: Path) -> None:
    """A trailing `\\n---` separator at the end of `llms.txt` is removed so
    the appended section's own `---` does not double up.
    """
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    (srcdir / "llms.txt").write_text(
        "# Header\n\nIntro.\n\n---\n", encoding="utf-8"
    )
    prose = "\n".join([f"Padding sentence {i}." for i in range(12)])
    (srcdir / "index.md").write_text(prose, encoding="utf-8")

    app = _make_app(srcdir, outdir)
    generate_llms_full(app, None)

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    # The single appended separator is `\n\n---\n\n`; with the trailing one
    # stripped from the header, the output should never contain two `---`
    # markers back-to-back.
    assert "---\n\n---" not in output
    # The "Intro." sentence must survive (i.e. content was not over-stripped).
    assert "Intro." in output


def test_unreadable_file_does_not_raise(tmp_path: Path) -> None:
    """A doc file whose read raises is logged and skipped, not propagated.

    Regression test for the original `except Exception` clause that referenced
    an undefined `e` and would have raised `NameError` on the first failure.
    """
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    srcdir.mkdir()
    outdir.mkdir()

    # Create one valid file so the run still produces output.
    prose = "\n".join([f"Valid sentence {i} of padding." for i in range(12)])
    (srcdir / "valid.md").write_text(prose, encoding="utf-8")

    # Create a `.md` path whose read will raise — simulate via monkey patch.
    bad = srcdir / "bad.md"
    bad.write_text("placeholder", encoding="utf-8")

    real_read_text = Path.read_text

    def fake_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self.name == "bad.md":
            raise OSError("simulated read failure")
        return real_read_text(self, *args, **kwargs)

    app = _make_app(srcdir, outdir)
    with unittest.mock.patch.object(Path, "read_text", fake_read_text):
        generate_llms_full(app, None)  # must not raise

    output = (outdir / "llms-full.txt").read_text(encoding="utf-8")
    # The valid file's content is present; the bad file is skipped silently.
    assert "Valid sentence 0" in output
    assert "bad.md" not in output
