## v0.17.1 (2023-06-26)

### Fix

- **projects.py**: use formatted string for doc latest url

## v0.17.0 (2023-06-26)

### Feat

- add announcement for unreleased and old branches

### Fix

- **header.html**: remove "docs-" from theme repo branch in header
- update banner

### Refactor

- **header.html**: test rtd embed flyout div
- **theme.py**: remove unnecessary open mode param UP015 for ruff
- remove trailing whitespaces
- refactor theme announcement logic
- move banner logic to projects.py
- include latest version url in announcement if not on latest

## v0.16.0 (2023-06-22)

### Feat

- Updating announcement banner

## v0.15.0 (2023-06-20)

### Feat

- **projects**: expose project urls to html templates

### Fix

- **projects.yaml**: remove hardcoding of rocm to develop

## v0.14.0 (2023-06-16)

### Feat

- **header.html**: write to header in italics if future release or release candidate
- **header.html**: include the version number in the top level header if the branch contains it
- **rdcMisc.js**: toggle light/dark mode caption when changing themes

### Refactor

- **header.html**: make the added part in italics for top level header
- **_toc.yml.in**: correct toc typo
- move theme mode captions to separate js file
- **rdcMisc.js**: use 4 spaces for tabs in rdcMisc

## v0.13.4 (2023-06-07)

### Fix

- **__init__.py**: stop searching CMakeLists.txt for version string

## v0.13.3 (2023-06-01)

### Fix

- New email address

## v0.13.2 (2023-05-31)

### Fix

- **custom.css**: force navbar text to left align
- Fix footer interaction with flyout nav
- CSS fixes around announcement banner

## v0.13.1 (2023-05-29)

### Refactor

- **doxygen.py**: remove extra print statement when copying over doxygen styling files
- **left-side-menu**: rename main doc link to ROCm Documentation Home

## v0.13.0 (2023-05-27)

### Feat

- **left-side-menu.html**: dynamically change homepage link for develop branch
- add link to ROCm docs home to top of TOC

### Fix

- **header.html**: fix link to amd.com

### Refactor

- include master branch for left side menu
- update development_branches
- include dev branch names in left-side-menu
- move yaml file to data folder
- add yaml with development branches
- dynamically change branch in left side menu

## v0.12.0 (2023-05-24)

### Feat

- Add announcement banner.

### Fix

- announcement URL and phrasing

## v0.11.1 (2023-05-23)

### Fix

- **header.html**: point docs repos to library repos
- **core.py**: use round to nearest minute for read time
- versioning script mismatch

## v0.11.0 (2023-05-17)

### Feat

- Nav bar links to project GitHub
- **projects**: allow overriding toc template path
- **projects**: mapping between project versions
- **projects**: allow overriding and disabling external mappings from conf.py
- **intersphinx**: Support intersphinx base urls in toc.yml
- **intersphinx**: support single strings for project
- **intersphinx**: add version replacement in the yaml
- **intersphinx**: Allow overriding branch name via environment variable
- fetch intersphinx config from a remote file

### Fix

- **rocm_footer.css**: Fix overlap with sidebar
- **renameVersionLinks.js**: Wait for RTD injection

### Refactor

- Still get PR branch using pygithub
- Use RTD environment variables
- Remove edit button, simplify get_branch
- **__init__.py**: remove deprecated and unused method
- **projects**: rename external_intersphinx to projects
- **doxygen**: Copy only doxygen folder from data

## v0.10.3 (2023-05-15)

### Fix

- **article-info**: hotfix non-html builds breaking

## v0.10.2 (2023-05-15)

### Fix

- Fix python typing, formatting, PEP8

## v0.10.1 (2023-05-11)

### Fix

- **sidebar**: fix rtd version selector not appearing on the sidebar for small screens
- **sidebar**: fix page jump when sidebar is opened, animate header
- **header**: don't show scroll-bar on menu when its not needed
- **article-info**: Use app.outdir for html directory
- allow overriding path to external toc path
- **custom.css**: restore cookie settings button styling

### Refactor

- **core.py**: fix mypy errors
- **article-info**: Simplify article-info handling

## v0.10.0 (2023-05-09)

### Feat

- Bring into compliance with AMD styling

### Fix

- Fix header on narrow screens
- Remove left side menu & buttons
- Fix lengths on shorter breadcrumbs
- Add zero width spaces when testing width
- deprecate disable_main_doc_link
- fix breadcrumbs and scrolling
- update ROCm Documentation url
- Tighten secondary nav
- Improve transitioning on resize

### Refactor

- Add links to header
- Merge remote-tracking branch 'upstream/develop' into HEAD

## v0.9.2 (2023-05-05)

### Fix

- check for existing article info before inserting

## v0.9.1 (2023-05-04)

### Fix

- **core.py**: use older version of pretty format in git log command

## v0.9.0 (2023-05-03)

### Feat

- **core.py**: set default publish date as time article was last modified
- **core.py**: set default read time by counting visible words in html output

### Refactor

- add back linkify
- merge with develop branch
- get file modification time using git
- import article info via importlib.resources
- convert myst_enable_extensions to set and add configunion helper
- **core.py**: explicitly cast to list

## v0.8.0 (2023-05-02)

### Feat

- Rename versioned doc links with version number

### Fix

- Remove unintended CSS changes

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
