## v1.13.0 (2025-01-06)

### Feat

- Update new url for Instinct docs

## v1.12.1 (2025-01-02)

### Fix

- scale down z-axis of multiple elements to preent covering flyout
- reducing sidebar z-index
- Replace copy_from_package with shutil.copytree

## v1.12.0 (2024-12-16)

### Feat

- Instinct documentation link in ROCm docs

## v1.11.0 (2024-12-05)

### Feat

- **projects.yaml**: Add tensile to intersphinx mapping

### Fix

- **article_info.py**: Remove svg if article info is empty
- **core.py**: Apply os list for article info fix for all article info option
- **article-info.html**: Only add apply to string if os list is not empty

### Refactor

- **article_info.py**: Apply mypy type check suggestions
- **article-info.html**: Add custom class to span with svgs in article info
- **core.py**: Split out article info logic into article_info.py
- Remove default author
- Modify markers in article-info.html
- **core.py**: Set default OS and date to empty
- **core.py**: Join article os info from list
- **core.py**: Set default article info os using all_article_info_os if not present

## v1.10.0 (2024-11-29)

### Feat

- Added Instinct flavor

## v1.9.2 (2024-11-28)

### Fix

- add "generic" to supported_flavors list

## v1.9.1 (2024-11-27)

### Fix

- add User-Agent headers to github request

## v1.9.0 (2024-11-22)

### Feat

- add generic theme flavor
- **projects.yaml**: add rocprof-sys, rocprof-comp, and rocJPEG

## v1.8.5 (2024-11-18)

### Fix

- reformat to pass 'black' linting check
- remove unnecessary space
- delete space
- add a check for MAX_RETRY

## v1.8.4 (2024-11-15)

### Fix

- resort import statements
- separate import time from other import statements as time is standard python library but others are third party
- sort import statement
- add retry loop around http request
- **header.jinja**: Replace http with https in repo URL

## v1.8.3 (2024-10-18)

### Fix

- **projects.yaml**: Update omniperf and omnitrace dev branch

## v1.8.2 (2024-09-24)

### Fix

- **theme.py**: Update path to favicon

## v1.8.1 (2024-09-17)

### Fix

- **projects.yaml**: Remove non-doc cross refs

## v1.8.0 (2024-09-16)

### Feat

- **custom.css**: Use light blue text for banner hyperlinks

### Fix

- **theme.py**: Fix phrasing of banner for old doc versions

## v1.7.2 (2024-08-21)

### Fix

- **projects.py**: Update pattern matching for old release announcement

## v1.7.1 (2024-08-19)

### Fix

- crop image from left side
- make cards brighter
- adjust padding back to 1
- change card font to san-serif and adjust padding
- change bg image to default one from ROCm/ROCm

## v1.7.0 (2024-08-14)

### Feat

- Add css classes for card banners

### Fix

- **projects.yaml**: Update doc dev branch for HIP to docs/develop

## v1.6.2 (2024-08-06)

### Fix

- **projects.yaml**: Update development branches for projects

### Refactor

- **Doxyfile**: Remove unused tags from Doxyfile
- **doxygen.py**: Fix warning for progress_message

## v1.6.1 (2024-07-25)

### Fix

- **project.yaml**: rocDecode and rocAL default to develop branch now

### Refactor

- Remove unused import
- Remove unused test code
- Remove SphinxTestApp
- Removed deprecated code
- **test_projects.py**: Format with black
- Update conf.py for site tests
- **test_doxygen.py**: Fix typo in doxygen dir

## v1.6.0 (2024-07-24)

### Feat

- **projects**: Add intersphinx links to github and files

### Refactor

- Set github version

## v1.5.1 (2024-07-23)

### Fix

- Update rocPyDecode link
- **projects.yaml**: Add llvm-project and rocpydecode

## v1.5.0 (2024-07-04)

### Feat

- **projects.yaml**: Add omniperf and omnitrace

## v1.4.1 (2024-06-27)

### Fix

- **header.jinja**: Make GitHub repo url for install docs point to install docs instead of ROCm home

### Refactor

- **core.py**: Apply ruff suggested fix
- **core.py**: Apply ruff suggested fix

## v1.4.0 (2024-06-06)

### Feat

- Add google site verification content to theme context
- Add template for google site verification content

### Refactor

- Get versions from data branch instead of header-versions branch

## v1.3.0 (2024-06-04)

### Feat

- **projects.yaml**: Add rocprofiler-sdk to projects
- **projects.yaml**: add rocminfo and rocm_bandwidth_test to projects list

## v1.2.1 (2024-06-03)

### Fix

- **custom.css**: Change line color at dark mode of multiline list

## v1.2.0 (2024-05-27)

### Feat

- **projects.yaml**: Add rocr_debug_agent to projects.yaml

## v1.1.3 (2024-05-22)

### Fix

- Get header version from URL instead of theme.conf

### Refactor

- **projects.py**: Use ROCm org when checking versions for banner
- **theme.py**: Point to ROCm org instead of RadeonOpenCompute for rocm-docs-core

## v1.1.2 (2024-05-16)

### Fix

- **projects.yaml**: add rocr-runtime
- **custom.css**: add bottom margin to images in rst files
- **404.html**: Remove relative link in 404.html page

## v1.1.1 (2024-04-26)

### Fix

- **core.py**: Update Sphinx API call to doc2path

### Refactor

- **core.py**: Format core.py with black
- Address mypy type warnings

## v1.1.0 (2024-04-24)

### Feat

- **theme.conf**: Update header latest version

### Fix

- **footer.html**: Bump year to 2024 in footer

### Refactor

- Correct major version for breaking change

## v1.0.0 (2024-04-17)

### BREAKING CHANGE

- This requires updating `.readthedocs.yaml` (`tools.python`)
  and re-generating `requirements.txt` for all dependent projects.

### Feat

- **theme.py**: Update banner announcement about docs.amd.com redirect

### Fix

- **layout.html**: Update google-site-verification metadata
- **header.jinja**: Update link to infinity hub
- Update rocm flavor header.jinja to Blogs
- **header.jinja**: Replace Lab Notes link with Blogs

### Refactor

- Fix mypy and isort errors
- Apply black formatting
- fixes for isort
- fixes for isort
- fixes for isort
- mypy fixes
- isort fixes
- Ruff fixes
- Fixes for ruff
- **projects.py**: Ignore mypy limitation for dynamic type checking
- **theme.py**: Modify new banner announcement message for latest
- Use type instead of instanceof
- Fix type hints and assertions to pass Python linting

## v0.38.1 (2024-04-10)

### Fix

- **extra_stylesheet.css**: Fix flexbox positioning for doxygen content

### Refactor

- Specify left instead of flex-end

## v0.38.0 (2024-03-26)

### Feat

- **theme.conf**: Update latest version for header

## v0.37.1 (2024-03-21)

### Fix

- **theme.conf**: Create point fix for 6.0.2

## v0.37.0 (2024-03-19)

### Feat

- **theme.py**: Remove banner on latest release

## v0.36.0 (2024-03-11)

### Feat

- **theme.conf**: Update latest header version

## v0.35.1 (2024-03-05)

### Fix

- **footer.jinja**: Fix license link for rocm flavor
- **header.jinja**: Update link to infinity hub

## v0.35.0 (2024-02-22)

### Feat

- **theme.py**: Update banner announcement about docs.amd.com redirect

### Fix

- Update rocm flavor header.jinja to Blogs
- **header.jinja**: Replace Lab Notes link with Blogs

### Refactor

- **theme.py**: Modify new banner announcement message for latest

## v0.34.2 (2024-02-15)

### Fix

- **left-side-menu.jinja**: Fix main doc link for rocm flavor left side menu

## v0.34.1 (2024-02-15)

### Fix

- Update left side menu

## v0.34.0 (2024-02-08)

### Feat

- **core.py**: Add html_image myst extension
- **core.py**: Enable dollarmath myst extension for inline latex math

## v0.33.2 (2024-02-06)

### Fix

- **left-side-menu.jinja**: Set main doc link for blogs flavor

## v0.33.1 (2024-02-05)

### Fix

- remove old folder
- Revert "fix: remove toc"
- remove toc
- remove duplicates
- merge conflicts
- **header.html**: Import version_list macro from header.jinja into header.html
- Change rocm-blogs flavor top level header to ROCm Blogs
- Change rocm-blogs second level header Lab Notes to ROCm Docs
- Remove version list from rocm-blogs header

## v0.33.0 (2024-01-26)

### Feat

- **theme.py**: Add rocm-blogs to lsit of supported flavors
- Add ROCm blogs flavor

### Fix

- **header.jinja**: New statement block for setting custom repo url

### Refactor

- **rocm-blogs/footer.jinja**: Refactor to pass Python linting

## v0.32.0 (2024-01-26)

### Feat

- **theme.conf**: Update header latest version

## v0.31.0 (2024-01-12)

### Feat

- **theme.conf**: Update header latest version
- Read versions for theme header from link instead of setting in theme.conf
- **projects.py**: Read header versions from link instead of hard-coding

### Fix

- Remove carriage return and newline when checking versions
- sync wordlist
- **header.jinja**: Fix support link in header for rocm-docs-core

### Refactor

- **theme.conf**: Add back header options to theme.conf to pass RTD PR build
- Use requests instead of urllib3
- **theme.py**: Set html_context in default_config_opts rather than theme_opts

## v0.30.3 (2023-12-20)

### Fix

- **dependabot.yml**: Change dependabot config

## v0.30.2 (2023-12-15)

### Fix

- adding linux and windows site fixes

## v0.30.1 (2023-12-06)

### Fix

- **flavors**: Fix the rocm-docs-home flavor

### Refactor

- Don't add a subproject link as its own project in projects.yaml
- Rename rocm-api-tools-list theme to rocm-docs-home

## v0.30.0 (2023-11-29)

### Feat

- Updating our links for installation subprojects

### Fix

- **theme.py**: Add list flavor to list of supported flavors

### Refactor

- Rename list theme to rocm-api-tools-list

## v0.29.0 (2023-11-24)

### Feat

- **projects.yaml**: Add linux install guide to projects.yaml
- Add new flavor - list theme
- Add all versions link to header
- Header name change to AMD ROCm Software
- **projects.yaml**: Add rocDecode to projects

## v0.28.0 (2023-11-16)

### Feat

- **doxygen.py**: Enable doxygen extended toc with forked doxysphinx

## v0.27.0 (2023-11-02)

### Feat

- **projects.yaml**: Add hip-vs
- **doxygen.py**: automatic setup of doxylink
- Update latest ROCm version in projects.py and theme.conf
- **doxygen,projects**: Make doxygen tagfile available
- **projects.py**: Allow to fetch project indices explicitly

### Fix

- **projects**: always resolve project references in TOC and templates
- **util.py**: Modify RTD regex to allow for .org sites
- **theme.py**: Partially handle not being in a git repository
- **doxygen.py**: Pass doxygen executable to doxysphinx

### Refactor

- **tests**: Move project tests to separate file

## v0.26.0 (2023-10-12)

### Feat

- Set latest version to 5.7.1

### Fix

- Reduce footer padding https://github.com/RadeonOpenCompute/rocm-docs-core/issues/394
- Increase z-index of content sidebar https://github.com/RadeonOpenCompute/rocm-docs-core/issues/396

## v0.25.0 (2023-10-03)

### Feat

- **projects.yaml**: add radeon

## v0.24.2 (2023-09-20)

### Fix

- **util.py**: Copy files relative to the source directory
- **doxygen.py**: Only continue if existing file is directory

### Refactor

- **theme.py**: Simplify 404 document handling

## v0.24.1 (2023-09-13)

### Fix

- **header.jinja**: only modify theme_repository_url if it ends with -docs

## v0.24.0 (2023-09-07)

### Feat

- **theme.conf**: update header version

## v0.23.0 (2023-09-05)

### Feat

- copy common 404.md source file to projects

### Refactor

- **theme.py**: copy theme util pages on builder init

## v0.22.1 (2023-09-05)

### Fix

- **projects.yaml**: add hipsparselt to projects yaml

## v0.22.0 (2023-08-31)

### Feat

- **projects.yaml**: add hiptensor to projects.yaml

### Fix

- **projects.yaml**: Add ROCmCMakeBuildTools to projects.yaml

## v0.21.0 (2023-08-29)

### Feat

- update latest version to 5.6.1

### Fix

- **projects.yaml**: add dev branch for rvs and rocal

## v0.20.0 (2023-07-28)

### Feat

- Add config option to specify doxygen exe
- Add reusable md rst linting
- Turn linting workflow into reusable

### Fix

- **core.py**: fix setting up the base url for the 404 page
- one-off indentation
- config handling style
- MD032
- MD031
- add missing mdlint config file

## v0.19.0 (2023-07-11)

### Feat

- Add "local" flavor for providing the flavor in the project
- Add support for theme "flavors"

### Refactor

- **projects.py,theme.py**: Decouple announcement strings from projects.py
- **projects.py**: Don't read projects.yaml again for release announcement
- **projects.py**: replace uses of _load_mapping with _create_mapping
- **projects.py**: Make Project creation more explicit

## v0.18.4 (2023-07-05)

### Fix

- **projects.yaml**: add rpp to projects.yaml

## v0.18.3 (2023-06-29)

### Fix

- **projects.yaml**: add more projects to yaml
- **projects.py**: use development_branch string instead of variable

## v0.18.2 (2023-06-28)

### Fix

- update latest version to 5.6.0

## v0.18.1 (2023-06-27)

### Fix

- **projects.py**: do not have an announcement stating the latest version

### Refactor

- **header.html**: revert flyout to default position for consistency

## v0.18.0 (2023-06-27)

### Feat

- add extrahead block with metadata in layout.html

### Fix

- update announcement for RC of ROCm
- map rocm version in projects.yaml to header.html version number

### Refactor

- use theme.conf for header version numbers
- place rocm latest version in projects.yaml

## v0.17.2 (2023-06-27)

### Fix

- hardcode the url for ROCm docs

### Refactor

- **util.py**: formatting fix for ruff; return result of regex on remote_url

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

- formatting fixes for ruff linting
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

### Fix

- Fix header on narrow screens
- Remove left side menu & buttons
- Fix lengths on shorter breadcrumbs
- Add zero width spaces when testing width

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

- Bring into compliance with AMD styling
- **core.py**: set default publish date as time article was last modified
- **core.py**: set default read time by counting visible words in html output

### Fix

- deprecate disable_main_doc_link
- fix breadcrumbs and scrolling
- update ROCm Documentation url
- Tighten secondary nav
- Improve transitioning on resize

### Refactor

- add back linkify
- merge with develop branch
- get file modification time using git
- import article info via importlib.resources

## v0.8.0 (2023-05-02)

### Feat

- Rename versioned doc links with version number

### Fix

- Remove unintended CSS changes

### Refactor

- convert myst_enable_extensions to set and add configunion helper
- **core.py**: explicitly cast to list

## v0.7.1 (2023-04-26)

### Fix

- docutil dependency

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
