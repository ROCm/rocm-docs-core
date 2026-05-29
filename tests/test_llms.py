"""Tests for rocm_docs.llms — llms-full.txt generation."""

from __future__ import annotations

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
        # Lines starting with "<" (raw HTML tags)
        '<div class="note">',
        # sphinx-tags badge
        ":img-top: image.png",
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
