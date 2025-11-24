"""Enhanced TOC injection for Doxygen pages with advanced features.

This enhanced version provides:
- Better integration with existing rocm_docs structure
- Configurable TOC position and styling
- Support for multiple TOC extraction strategies
- Better error handling and logging
"""

from __future__ import annotations

from typing import Any, Literal

import json
import os
from pathlib import Path

import bs4
from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.util import logging
from sphinx.util.display import progress_message

logger = logging.getLogger(__name__)


class DoxygenTOCInjector:
    """Handles injection of Sphinx TOC into Doxygen pages."""
    
    def __init__(self, app: Sphinx):
        """Initialize the injector with Sphinx app context."""
        self.app = app
        self.sphinx_outdir = Path(app.outdir)
        self.doxygen_dir: Path | None = None
        self.toc_html: str | None = None
        
        if hasattr(app.config, "doxygen_html") and app.config.doxygen_html:
            self.doxygen_dir = self.sphinx_outdir / app.config.doxygen_html
    
    def should_inject(self) -> bool:
        """Check if TOC injection should be performed."""
        if self.app.builder.format != "html":
            logger.debug("Not HTML builder, skipping TOC injection")
            return False
        
        if not self.app.config.doxygen_toc_enabled:
            logger.debug("doxygen_toc_enabled is False")
            return False
        
        if self.doxygen_dir is None:
            logger.debug("No doxygen_html directory configured")
            return False
        
        if not self.doxygen_dir.exists():
            logger.warning(f"Doxygen directory not found: {self.doxygen_dir}")
            return False
        
        return True
    
    def extract_toc(self) -> bool:
        """Extract TOC from Sphinx pages.
        
        Returns:
            True if TOC was successfully extracted, False otherwise
        """
        # Try multiple extraction strategies
        strategies = [
            self._extract_from_index,
            self._extract_from_any_page,
            self._extract_from_template,
        ]
        
        for strategy in strategies:
            self.toc_html = strategy()
            if self.toc_html:
                logger.info(f"TOC extracted using {strategy.__name__}")
                return True
        
        logger.warning("Could not extract TOC from Sphinx pages")
        return False
    
    def _extract_from_index(self) -> str | None:
        """Try to extract TOC from index.html."""
        index_path = self.sphinx_outdir / "index.html"
        if not index_path.exists():
            return None
        
        return self._extract_sidebar_from_file(index_path)
    
    def _extract_from_any_page(self) -> str | None:
        """Try to extract TOC from any Sphinx HTML page."""
        for html_file in self.sphinx_outdir.glob("*.html"):
            # Skip special pages
            if html_file.name in ["genindex.html", "search.html", "404.html"]:
                continue
            
            sidebar = self._extract_sidebar_from_file(html_file)
            if sidebar:
                return sidebar
        
        return None
    
    def _extract_from_template(self) -> str | None:
        """Try to extract TOC structure from external_toc configuration."""
        # This is a fallback that generates a simple TOC from the toc structure
        if not hasattr(self.app.config, "external_toc_path"):
            return None
        
        toc_path = Path(self.app.srcdir) / self.app.config.external_toc_path
        if not toc_path.exists():
            return None
        
        try:
            import yaml
            with open(toc_path, encoding="utf-8") as f:
                toc_data = yaml.safe_load(f)
            
            return self._generate_toc_html_from_structure(toc_data)
        except Exception as e:
            logger.debug(f"Could not generate TOC from structure: {e}")
            return None
    
    def _extract_sidebar_from_file(self, html_file: Path) -> str | None:
        """Extract sidebar HTML from a file."""
        with open(html_file, encoding="utf-8") as f:
            soup = bs4.BeautifulSoup(f, "html.parser")
        
        # Try different sidebar selectors in order of preference
        selectors = [
            ("div", {"class": "bd-sidebar-primary"}),
            ("aside", {"class": "bd-sidebar"}),
            ("nav", {"class": "bd-links"}),
            ("div", {"id": "bd-docs-nav"}),
            ("nav", {"class": "bd-docs-nav"}),
        ]
        
        for tag_name, attrs in selectors:
            sidebar = soup.find(tag_name, attrs)
            if sidebar and isinstance(sidebar, bs4.Tag):
                return str(sidebar)
        
        return None
    
    def _generate_toc_html_from_structure(self, toc_data: Any) -> str:
        """Generate a simple HTML TOC from the YAML structure."""
        def build_list(items: list | dict, level: int = 0) -> str:
            if isinstance(items, dict):
                items = [items]
            
            html = '<ul class="bd-sidenav">\n'
            
            for item in items:
                if isinstance(item, str):
                    html += f'<li><a href="{item}.html">{item}</a></li>\n'
                elif isinstance(item, dict):
                    title = item.get("title", item.get("file", ""))
                    file = item.get("file", "")
                    
                    if file:
                        html += f'<li><a href="{file}.html">{title}</a>'
                    else:
                        html += f'<li><span>{title}</span>'
                    
                    if "entries" in item:
                        html += build_list(item["entries"], level + 1)
                    
                    html += '</li>\n'
            
            html += '</ul>\n'
            return html
        
        toc_html = '<div class="bd-sidebar-primary">\n'
        toc_html += '<nav class="bd-links">\n'
        
        if isinstance(toc_data, dict):
            if "root" in toc_data:
                toc_html += build_list(toc_data.get("subtrees", []))
            elif "entries" in toc_data:
                toc_html += build_list(toc_data["entries"])
        
        toc_html += '</nav>\n</div>\n'
        
        return toc_html
    
    def inject_to_all_pages(self) -> int:
        """Inject TOC into all Doxygen HTML pages.
        
        Returns:
            Number of pages successfully modified
        """
        if not self.doxygen_dir:
            return 0
        
        doxygen_files = list(self.doxygen_dir.rglob("*.html"))
        
        if not doxygen_files:
            logger.info(f"No Doxygen HTML files found in {self.doxygen_dir}")
            return 0
        
        success_count = 0
        
        with progress_message(f"Injecting TOC into {len(doxygen_files)} Doxygen pages"):
            for html_file in doxygen_files:
                try:
                    if self._inject_to_file(html_file):
                        success_count += 1
                except Exception as e:
                    logger.warning(f"Failed to inject TOC into {html_file.name}: {e}")
        
        logger.info(f"Successfully injected TOC into {success_count}/{len(doxygen_files)} pages")
        return success_count
    
    def _inject_to_file(self, html_file: Path) -> bool:
        """Inject TOC into a single file.
        
        Returns:
            True if injection was successful, False otherwise
        """
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        soup = bs4.BeautifulSoup(content, "html.parser")
        
        # Skip if TOC already exists
        if soup.find("div", class_="rocm-docs-toc-wrapper"):
            return False
        
        # Calculate relative path
        relative_depth = len(html_file.relative_to(self.doxygen_dir).parts) - 1
        path_prefix = "../" * relative_depth if relative_depth > 0 else "./"
        
        # Prepare TOC
        toc_soup = bs4.BeautifulSoup(self.toc_html, "html.parser")
        self._adjust_paths(toc_soup, path_prefix)
        
        # Get configuration
        position = self.app.config.doxygen_toc_position
        style = self.app.config.doxygen_toc_style
        
        # Inject based on position
        if position == "left":
            self._inject_left_sidebar(soup, toc_soup, style, path_prefix)
        elif position == "right":
            self._inject_right_sidebar(soup, toc_soup, style, path_prefix)
        else:  # "auto"
            self._inject_auto(soup, toc_soup, style, path_prefix)
        
        # Write back
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(str(soup))
        
        return True
    
    def _inject_left_sidebar(
        self,
        soup: bs4.BeautifulSoup,
        toc_soup: bs4.BeautifulSoup,
        style: str,
        path_prefix: str,
    ) -> None:
        """Inject TOC as a left sidebar."""
        body = soup.find("body")
        if not body or not isinstance(body, bs4.Tag):
            return
        
        # Create wrapper
        wrapper = soup.new_tag("div", **{"class": "rocm-docs-container"})
        
        # Create TOC sidebar
        toc_wrapper = soup.new_tag("div", **{
            "class": f"rocm-docs-toc-wrapper rocm-docs-toc-{style}",
            "id": "rocm-docs-toc"
        })
        toc_wrapper.append(toc_soup)
        
        # Create content wrapper
        content = soup.new_tag("div", **{"class": "rocm-docs-content"})
        for child in list(body.children):
            content.append(child.extract())
        
        # Assemble
        wrapper.append(toc_wrapper)
        wrapper.append(content)
        body.append(wrapper)
        
        self._add_styles(soup, "left", style, path_prefix)
    
    def _inject_right_sidebar(
        self,
        soup: bs4.BeautifulSoup,
        toc_soup: bs4.BeautifulSoup,
        style: str,
        path_prefix: str,
    ) -> None:
        """Inject TOC as a right sidebar."""
        body = soup.find("body")
        if not body or not isinstance(body, bs4.Tag):
            return
        
        wrapper = soup.new_tag("div", **{"class": "rocm-docs-container"})
        
        content = soup.new_tag("div", **{"class": "rocm-docs-content"})
        for child in list(body.children):
            content.append(child.extract())
        
        toc_wrapper = soup.new_tag("div", **{
            "class": f"rocm-docs-toc-wrapper rocm-docs-toc-{style}",
            "id": "rocm-docs-toc"
        })
        toc_wrapper.append(toc_soup)
        
        wrapper.append(content)
        wrapper.append(toc_wrapper)
        body.append(wrapper)
        
        self._add_styles(soup, "right", style, path_prefix)
    
    def _inject_auto(
        self,
        soup: bs4.BeautifulSoup,
        toc_soup: bs4.BeautifulSoup,
        style: str,
        path_prefix: str,
    ) -> None:
        """Auto-detect best position and inject TOC."""
        # Default to left for now
        self._inject_left_sidebar(soup, toc_soup, style, path_prefix)
    
    def _adjust_paths(self, toc_soup: bs4.BeautifulSoup, path_prefix: str) -> None:
        """Adjust all links to be relative to the doxygen page."""
        for link in toc_soup.find_all("a", href=True):
            href = link["href"]
            
            # Skip absolute and external URLs
            if href.startswith(("http://", "https://", "//", "/", "#")):
                continue
            
            link["href"] = path_prefix + href
        
        # Also adjust image sources if any
        for img in toc_soup.find_all("img", src=True):
            src = img["src"]
            if not src.startswith(("http://", "https://", "//", "/")):
                img["src"] = path_prefix + src
    
    def _add_styles(
        self,
        soup: bs4.BeautifulSoup,
        position: str,
        style: str,
        path_prefix: str,
    ) -> None:
        """Add CSS styles for the TOC."""
        head = soup.find("head")
        if not head or not isinstance(head, bs4.Tag):
            return
        
        # Add CSS link for Sphinx styles if available
        css_link = soup.new_tag(
            "link",
            rel="stylesheet",
            href=f"{path_prefix}_static/styles/pydata-sphinx-theme.css",
            type="text/css"
        )
        head.append(css_link)
        
        # Add inline styles
        style_tag = soup.new_tag("style")
        style_tag.string = self._get_css_styles(position, style)
        head.append(style_tag)
        
        # Add toggle button script if collapsible
        if style == "collapsible":
            self._add_toggle_script(soup)
    
    def _get_css_styles(self, position: str, style: str) -> str:
        """Generate CSS styles based on configuration."""
        base_css = """
        .rocm-docs-container {
            display: flex;
            max-width: 100%;
            margin: 0 auto;
            gap: 20px;
        }
        
        .rocm-docs-content {
            flex: 1;
            min-width: 0;
            padding: 20px;
        }
        
        .rocm-docs-toc-wrapper {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 20px;
        }
        """
        
        if style == "fixed":
            base_css += """
            .rocm-docs-toc-wrapper {
                flex: 0 0 300px;
                max-width: 300px;
                position: sticky;
                top: 20px;
                height: calc(100vh - 40px);
                overflow-y: auto;
            }
            """
        elif style == "floating":
            base_css += """
            .rocm-docs-toc-wrapper {
                flex: 0 0 300px;
                max-width: 300px;
                max-height: calc(100vh - 40px);
                overflow-y: auto;
            }
            """
        elif style == "collapsible":
            base_css += """
            .rocm-docs-toc-wrapper {
                flex: 0 0 300px;
                max-width: 300px;
                position: sticky;
                top: 20px;
                height: calc(100vh - 40px);
                overflow-y: auto;
                transition: transform 0.3s ease;
            }
            
            .rocm-docs-toc-wrapper.collapsed {
                transform: translateX(-280px);
            }
            
            #rocm-toc-toggle {
                position: absolute;
                right: 10px;
                top: 10px;
                cursor: pointer;
                background: #007bff;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            """
        
        # Responsive styles
        base_css += """
        @media (max-width: 768px) {
            .rocm-docs-container {
                flex-direction: column;
            }
            
            .rocm-docs-toc-wrapper {
                position: static !important;
                max-width: 100% !important;
                height: auto !important;
                flex: 1;
            }
        }
        
        /* TOC link styles */
        .rocm-docs-toc-wrapper a {
            color: #007bff;
            text-decoration: none;
            display: block;
            padding: 4px 0;
        }
        
        .rocm-docs-toc-wrapper a:hover {
            text-decoration: underline;
            background: rgba(0, 123, 255, 0.1);
        }
        
        .rocm-docs-toc-wrapper ul {
            list-style: none;
            padding-left: 15px;
        }
        
        .rocm-docs-toc-wrapper > nav > ul {
            padding-left: 0;
        }
        """
        
        return base_css
    
    def _add_toggle_script(self, soup: bs4.BeautifulSoup) -> None:
        """Add JavaScript for collapsible TOC."""
        toc_wrapper = soup.find("div", id="rocm-docs-toc")
        if toc_wrapper and isinstance(toc_wrapper, bs4.Tag):
            button = soup.new_tag("button", id="rocm-toc-toggle")
            button.string = "☰"
            toc_wrapper.insert(0, button)
        
        script = soup.new_tag("script")
        script.string = """
        document.addEventListener('DOMContentLoaded', function() {
            var toggle = document.getElementById('rocm-toc-toggle');
            var toc = document.getElementById('rocm-docs-toc');
            
            if (toggle && toc) {
                toggle.addEventListener('click', function() {
                    toc.classList.toggle('collapsed');
                });
            }
        });
        """
        
        body = soup.find("body")
        if body and isinstance(body, bs4.Tag):
            body.append(script)


def _inject_toc_to_doxygen_pages(app: Sphinx, _: Config) -> None:
    """Main entry point for TOC injection."""
    injector = DoxygenTOCInjector(app)
    
    if not injector.should_inject():
        return
    
    if not injector.extract_toc():
        return
    
    injector.inject_to_all_pages()


def setup(app: Sphinx) -> dict[str, Any]:
    """Set up the enhanced doxygen_toc extension."""
    # Configuration values
    app.add_config_value(
        "doxygen_toc_enabled",
        default=True,
        rebuild="html",
        types=bool,
    )
    
    app.add_config_value(
        "doxygen_toc_position",
        default="left",
        rebuild="html",
        types=str,
    )
    
    app.add_config_value(
        "doxygen_toc_style",
        default="fixed",
        rebuild="html",
        types=str,
    )
    
    # Connect to build-finished event
    app.connect("build-finished", _inject_toc_to_doxygen_pages, priority=1001)
    
    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
        "version": "1.0.0",
    }
