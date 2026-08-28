---
myst:
    html_meta:
        "description": "Configure the version banner in ROCm documentation, including the automatic old-version notice and custom announcements"
        "keywords": "banner, announcement, version notice, old version, ROCm docs core user guide"
---

# Version banner

`rocm-docs-core` can display a banner across the top of every page to tell
readers that they are not on the latest documentation. The banner appears
automatically based on the version being built, and its link points to the same
page on the latest version. You can also replace it with your own announcement.

## Automatic banner

For projects using the `rocm` theme flavor, the banner is added automatically
based on the version type that `rocm-docs-core` detects from the build branch.
No configuration is required.

| Version type      | When it applies                              | Banner message                                                |
| ----------------- | -------------------------------------------- | ------------------------------------------------------------- |
| Old release       | A `docs-X.Y.Z` branch that is not the latest | This is not the latest version of ROCm documentation.         |
| Release candidate | The current release-candidate branch         | This page contains changes for a test release of ROCm.        |
| Development        | The development branch (for example `develop`) | This page contains proposed changes for a future release.     |

No banner is shown when the build is the latest release, because there is
nothing newer to point to.

The banner is only added for the `rocm` flavor. Other flavors do not get an
automatic banner, but they can set a custom one (see
[](#custom-announcement)).

## Link to the matching page on latest

Each automatic banner links to the latest version of the **current page**, not
the documentation root. From
`.../projects/HIP/en/docs-6.2.2/reference/cpp_language_extensions.html`, the
banner links to
`.../projects/HIP/en/latest/reference/cpp_language_extensions.html`, preserving
the project and page path.

This works in two layers:

- The link ships with a fixed `.../en/latest/` href as a fallback for when
  JavaScript is unavailable.
- At runtime, `bannerLatestLink.js` rewrites the href of any link carrying the
  `data-rocm-banner-latest-link` attribute to the matching page under `latest`,
  based on the current URL. If the page does not exist on the latest version,
  Read the Docs serves its own 404 for that version.

## Custom announcement

To show your own banner, set `announcement` in `html_theme_options` in
`conf.py`. Because the automatic banner uses a default, any value you set takes
precedence, including on the `rocm` flavor:

```python
html_theme_options = {
    "announcement": "Read the <a href='https://rocm.docs.amd.com/'>ROCm documentation portal</a> for more.",
}
```

The value is raw HTML, so you can include links and inline markup.

### Opting a custom link into the latest-page rewrite

A custom announcement link is left untouched by `bannerLatestLink.js`, so it
always points where you set it. To have your own link rewritten to the matching
page on the latest version, add the `data-rocm-banner-latest-link` attribute to
it:

```python
html_theme_options = {
    "announcement": (
        "You are viewing an archived page. See the "
        "<a data-rocm-banner-latest-link "
        "href='https://rocm.docs.amd.com/en/latest/'>latest version</a>."
    ),
}
```

The `href` you provide is used as the no-JavaScript fallback, and the script
upgrades it to the current page under `latest` at runtime.
