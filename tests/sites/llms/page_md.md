---
myst:
  html_meta:
    "description lang=en": "A Markdown page with a code block and a table."
---

# Markdown page

Some prose on the Markdown page.

```cpp
__global__ void md_kernel(float* a) {
    int i = threadIdx.x;
    a[i] = 2.0f;
}
```

| Name | Value |
| ---- | ----- |
| foo  | 1     |
| bar  | 2     |
