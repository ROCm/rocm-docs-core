---
myst:
    html_meta:
        "description": "Setting article info in ROCm documentation"
        "keywords": "Documentation settings, Display document information, Display article metadata, Display document metadata"
article_info:
    os: [linux, windows]
    author: Author: AMD
    date: 2024-01-15
    read-time: 67 min read
---

# Article Info

Article info is disabled by default and must be enabled in `conf.py`.

## Settings

*Legend: `setting name (setting data type):` explanation*

- `setting_all_article_info (bool)`: Setting this value to true will enable article info for all pages and use default values. See possible settings for default values.

- `all_article_info_os (list[str])`: Determines which supported OS appear in the article info. Possible strings are `"linux"` and `"windows"`. Default value is `["linux"]`.

- `all_article_info_author (str)`: Determines the author. Default is empty string.

- `all_article_info_date (str)`: Determines date of publication. Default is the date the file was last modified in git.

- `all_article_info_read_time (str)`: Determines the read time. Default is calculated based on the number of words in the file.

- `article_pages (list[dict])`: Used for specific settings for a page. These override any of the general settings above (eg: `all_article_info_<field>`).

Example:

```python
article_pages = [
    {
        "file":"index",
        "os":["linux", "windows"],
        "author":"Author: AMD",
        "date":"2023-05-01",
        "read-time":"2 min read"
    },
    {"file":"developer_guide/commitizen"}
]
```

## Per-page metadata

Article info fields can also be set directly in a source file. This avoids
editing `conf.py` for individual pages. Per-page values override the global
`all_article_info_*` settings but are overridden by any entry for the same
page in `article_pages`.

When any page carries article info metadata, article info is rendered for
that page even if `setting_all_article_info` is `False` and the page is not
listed in `article_pages`.

**MyST Markdown** — use an `article_info` block in the YAML front matter:

```yaml
---
myst:
    html_meta:
        "description": "Page description"
article_info:
    os: [linux, windows]
    author: Author: AMD
    date: 2024-01-15
    read-time: 3 min read
---

# My Page Title
```

**RST** — use the `.. article-info::` directive (typically near the top of
the file, before the page body):

```rst
.. article-info::
   :os: linux windows
   :author: Author: AMD
   :date: 2024-01-15
   :read-time: 3 min read

My Page Title
=============
```

Supported fields:

| Field | Description |
|-------|-------------|
| `os` | OS list — `linux`, `windows`, or both. In RST: space-separated string. In MyST: YAML list. |
| `author` | Author string |
| `date` | Publication date (e.g. `2024-01-15`) |
| `read-time` | Read time string (e.g. `3 min read`) |

```{note}
Only one `article_info` definition per page is allowed. A build warning is
emitted and the duplicate ignored if the directive appears more than once, or
if it is used alongside front matter in a MyST file. Because MyST front matter
is processed before the document body, the front matter block always takes
priority in that case. For MyST files, prefer the front matter approach;
use the `.. article-info::` directive for RST files only.
```
