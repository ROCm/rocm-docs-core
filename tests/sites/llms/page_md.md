---
myst:
  html_meta:
    "description lang=en": "A Markdown page with a code block and a table."
---

# Markdown page

Some prose on the Markdown page, mentioning the inline literal `hipMalloc` and
an [external link](https://rocm.docs.amd.com).

```cpp
__global__ void md_kernel(float* a) {
    int i = threadIdx.x;
    a[i] = 2.0f;
}
```

A nested list:

- First item
  - Nested item
- Second item

| Name | Value |
| ---- | ----- |
| foo  | 1     |
| bar  | 2     |

Inline math such as $a^2 + b^2 = c^2$ should be preserved.

A raw HTML table with merged cells (as produced by an HTML support-matrix
include) must be converted to a Markdown table:

<table class="rocm-docs-table table">
  <thead>
    <tr>
      <th class="head"><p>GPU</p></th>
      <th class="head"><p>Mode</p></th>
      <th class="head"><p>OS</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td rowspan="2"><p>HtmlMI300</p></td>
      <td><p>Passthrough</p></td>
      <td><p>Ubuntu</p></td>
    </tr>
    <tr>
      <td><p>SR-IOV</p></td>
      <td><p>RHEL</p></td>
    </tr>
  </tbody>
</table>
