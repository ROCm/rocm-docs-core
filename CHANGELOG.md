## v0.7.1 (2023-04-26)

## v0.7.0 (2023-04-26)

### Feat

- **core.py**: set specific page settings first before setting general settings
- **core.py**: add ability to set article info for all pages
- allow substitutions for author, date, and read time in article info
- add article info for linux and windows
- **core.py**: add article info with supported os info

### Fix

- **deps**: Fix search highlight in doxysphinx by updating sphinx version

### Refactor

- use consistent formatting for init and remove empty list from core
- **core.py**: move linkcheck configs to core from init

## v0.6.0 (2023-04-18)

### Feat

- use different link color based on theme
- increase font size

### Fix

- **header**: direct GitHub header link to ROCm

## v0.5.0 (2023-04-14)

### Feat

- **__init__.py**: add version numbers

### Fix

- ensure compatibility for 3.8 through 3.11
- **dependabot.yml**: remove extra spaces

## v0.4.0 (2023-04-13)

### BREAKING CHANGE

- users of the non-legacy API have to set `html_theme` to `rocm_docs_theme` to maintain the current behaviour.

### Fix

- **legacy**: fix builds without doxygen
- **extension**: no longer set the html_theme by default in the extension
- **legacy**: restore custom theme on readthedocs

## v0.3.0 (2023-04-13)

### Feat

- move automatic doxygen and doxysphinx to an extension
- move core settings to a sphinx extension

### Fix

- restore cookie permissions / analytics script

### Refactor

- various formatting and type fixes in util.py

## v0.2.2 (2023-04-13)

### Fix

- various stlysheet fixes

## v0.2.1 (2023-04-13)

### Fix

- update links in header and footer (#87)

## v0.0.1 (2023-03-13)
