---
myst:
    html_meta:
        "description": "Setting article info in ROCm documentation"
        "keywords": "Documentation settings, Display document information, Display article metadata, Display document metadata"
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
