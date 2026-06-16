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
