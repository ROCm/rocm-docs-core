"""Inject Doxygen navigation into Sphinx pages' TOC.

This extension:
1. Finds Doxygen-generated HTML files
2. Extracts the list of available Doxygen pages (Classes, Functions, etc.)
3. Injects them into the Sphinx TOC on all Sphinx pages
4. Makes Doxygen pages visible in Sphinx navigation
"""

from __future__ import annotations

from typing import Any
from pathlib import Path

import bs4
from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.util import logging
from sphinx.util.display import progress_message

logger = logging.getLogger(__name__)


class DoxygenToSphinxTOCInjector:
    """Injects Doxygen navigation into Sphinx TOC."""
    
    def __init__(self, app: Sphinx):
        """Initialize the injector."""
        self.app = app
        self.sphinx_outdir = Path(app.outdir)
        self.doxygen_dir: Path | None = None
        self.doxygen_nav_html: str | None = None
        
        if hasattr(app.config, "doxygen_html") and app.config.doxygen_html:
            self.doxygen_dir = self.sphinx_outdir / app.config.doxygen_html
            logger.info(f"Doxygen directory set to: {self.doxygen_dir}")
    
    def should_inject(self) -> bool:
        """Check if injection should be performed."""
        if self.app.builder.format != "html":
            logger.info("Builder format is not HTML, skipping injection")
            return False
        
        if not getattr(self.app.config, "doxygen_toc_enabled", True):
            logger.info("doxygen_toc_enabled is False, skipping injection")
            return False
        
        if self.doxygen_dir is None:
            logger.warning("No doxygen_html directory configured - check docs_core.run_doxygen()")
            return False
        
        if not self.doxygen_dir.exists():
            logger.warning(f"Doxygen directory not found: {self.doxygen_dir}")
            return False
        
        return True
    
    def scan_doxygen_pages(self) -> bool:
        """Scan Doxygen directory for available pages and build navigation."""
        if not self.doxygen_dir:
            return False
        
        # Map of Doxygen files to display info
        doxygen_pages = [
            # (filename, display_name, icon)
            ("annotated.html", "Classes", "📚"),
            ("classes.html", "Class Index", "📇"),
            ("hierarchy.html", "Class Hierarchy", "🌲"),
            ("files.html", "Files", "📁"),
            ("namespaces.html", "Namespaces", "📦"),
            ("namespacemembers.html", "Namespace Members", "🔧"),
            ("modules.html", "Modules", "📦"),
            ("functions.html", "Functions", "⚙️"),
            ("functions_func.html", "Functions (detailed)", "⚙️"),
            ("globals.html", "Globals", "🌐"),
            ("globals_defs.html", "Macros", "🔤"),
            ("globals_type.html", "Typedefs", "📐"),
            ("globals_enum.html", "Enumerations", "🔢"),
            ("globals_eval.html", "Enumerator Values", "🔢"),
            ("deprecated.html", "Deprecated", "⚠️"),
        ]
        
        # Find which pages exist
        found_pages = []
        for filename, display_name, icon in doxygen_pages:
            file_path = self.doxygen_dir / filename
            if file_path.exists():
                # Calculate relative path from Sphinx root to Doxygen file
                rel_path = f"{self.app.config.doxygen_html}/{filename}"
                found_pages.append((rel_path, display_name, icon))
                logger.debug(f"Found Doxygen page: {filename}")
        
        if not found_pages:
            logger.warning(f"No Doxygen pages found in {self.doxygen_dir}")
            return False
        
        logger.info(f"Found {len(found_pages)} Doxygen pages to add to TOC")
        
        # Build the navigation HTML
        self.doxygen_nav_html = self._build_doxygen_nav(found_pages)
        return True
    
    def _build_doxygen_nav(self, pages: list) -> str:
        """Build HTML for Doxygen navigation section."""
        html = '<div class="doxygen-auto-nav">\n'
        
        # Add caption/header
        html += '<p aria-level="2" class="caption" role="heading">'
        html += '<span class="caption-text">Doxygen API</span>'
        html += '</p>\n'
        
        # Add list of pages
        html += '<ul class="nav bd-sidenav">\n'
        
        for rel_path, display_name, icon in pages:
            html += '<li class="toctree-l1 doxygen-auto-link">'
            html += f'<a class="reference internal" href="{rel_path}">'
            html += f'{icon} {display_name}'
            html += '</a>'
            html += '</li>\n'
        
        html += '</ul>\n'
        html += '</div>\n'
        
        return html
    
    def inject_to_sphinx_pages(self) -> int:
        """Inject Doxygen navigation into all Sphinx HTML pages."""
        if not self.doxygen_nav_html:
            logger.warning("No Doxygen navigation HTML to inject")
            return 0
        
        # Find all Sphinx HTML files (exclude Doxygen directory)
        sphinx_files = []
        for html_file in self.sphinx_outdir.rglob("*.html"):
            # Skip files in Doxygen directory
            if self.doxygen_dir and self.doxygen_dir in html_file.parents:
                continue
            
            # Skip special files
            if html_file.name in ["search.html", "genindex.html"]:
                continue
            
            sphinx_files.append(html_file)
        
        if not sphinx_files:
            logger.warning("No Sphinx HTML files found to inject into")
            return 0
        
        logger.info(f"Found {len(sphinx_files)} Sphinx HTML files")
        
        success_count = 0
        
        with progress_message(f"Injecting Doxygen nav into {len(sphinx_files)} Sphinx pages"):
            for html_file in sphinx_files:
                try:
                    if self._inject_to_file(html_file):
                        success_count += 1
                except Exception as e:
                    logger.warning(f"Failed to inject into {html_file.name}: {e}")
        
        logger.info(f"Successfully injected Doxygen nav into {success_count}/{len(sphinx_files)} Sphinx pages")
        return success_count
    
    def _inject_to_file(self, html_file: Path) -> bool:
        """Inject Doxygen navigation into a single Sphinx HTML file."""
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        soup = bs4.BeautifulSoup(content, "html.parser")
        
        # Find the Sphinx navigation
        nav = soup.find("nav", class_="bd-docs-nav")
        if not nav or not isinstance(nav, bs4.Tag):
            logger.debug(f"No bd-docs-nav found in {html_file.name}")
            return False
        
        # Check if already injected
        if nav.find("div", class_="doxygen-auto-nav"):
            logger.debug(f"Already injected in {html_file.name}")
            return False
        
        # Find the bd-toc-item div
        toc_item = nav.find("div", class_="bd-toc-item")
        if not toc_item or not isinstance(toc_item, bs4.Tag):
            logger.debug(f"No bd-toc-item found in {html_file.name}")
            return False
        
        # Parse the Doxygen navigation HTML
        doxygen_soup = bs4.BeautifulSoup(self.doxygen_nav_html, "html.parser")
        
        # Add a separator before Doxygen navigation
        separator = soup.new_tag("hr", **{"class": "doxygen-nav-separator"})
        toc_item.append(separator)
        
        # Append Doxygen navigation to the TOC
        for element in doxygen_soup.children:
            if isinstance(element, bs4.Tag):
                toc_item.append(element)
        
        # Add CSS for styling
        self._add_styles(soup)
        
        # Write modified content
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(str(soup))
        
        logger.debug(f"Successfully injected into {html_file.name}")
        return True
    
    def _add_styles(self, soup: bs4.BeautifulSoup) -> None:
        """Add CSS styles for the Doxygen navigation section."""
        head = soup.find("head")
        if not head or not isinstance(head, bs4.Tag):
            return
        
        # Check if styles already added
        if soup.find("style", id="doxygen-auto-nav-styles"):
            return
        
        style_tag = soup.new_tag("style", id="doxygen-auto-nav-styles")
        style_tag.string = """
        /* Doxygen Auto-Navigation Styles */
        
        .doxygen-nav-separator {
            margin: 20px 0;
            border: 0;
            border-top: 2px solid #dee2e6;
        }
        
        .doxygen-auto-nav {
            margin-top: 15px;
        }
        
        .doxygen-auto-nav .caption {
            font-weight: 700;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #ed1c24;  /* AMD red for Doxygen section */
            margin-bottom: 8px;
            padding: 4px 8px;
            border-left: 3px solid #ed1c24;
        }
        
        .doxygen-auto-link a {
            color: #0072ce;
            font-size: 14px;
        }
        
        .doxygen-auto-link a:hover {
            background: rgba(237, 28, 36, 0.05);
            color: #ed1c24;
        }
        
        /* Add a subtle icon indicator */
        .doxygen-auto-link {
            position: relative;
        }
        
        .doxygen-auto-link::before {
            content: '';
            position: absolute;
            left: -10px;
            top: 50%;
            transform: translateY(-50%);
            width: 3px;
            height: 60%;
            background: #ed1c24;
            opacity: 0;
            transition: opacity 0.2s;
        }
        
        .doxygen-auto-link:hover::before {
            opacity: 1;
        }
        """
        
        head.append(style_tag)


def _inject_doxygen_to_sphinx_toc(app: Sphinx, _: Config) -> None:
    """Main entry point for Doxygen to Sphinx TOC injection."""
    logger.info("=" * 70)
    logger.info("DOXYGEN TO SPHINX TOC INJECTION")
    logger.info("=" * 70)
    
    try:
        injector = DoxygenToSphinxTOCInjector(app)
        
        if not injector.should_inject():
            logger.info("Doxygen->Sphinx TOC injection skipped (conditions not met)")
            return
        
        if not injector.scan_doxygen_pages():
            logger.warning("No Doxygen pages found to inject")
            return
        
        count = injector.inject_to_sphinx_pages()
        if count > 0:
            logger.info(f"✓ Injected Doxygen navigation into {count} Sphinx pages")
            logger.info("=" * 70)
        else:
            logger.warning("No Sphinx pages were modified")
            
    except Exception as e:
        logger.error(f"Doxygen->Sphinx injection failed: {e}", exc_info=True)


def setup(app: Sphinx) -> dict[str, Any]:
    """Set up the doxygen_toc extension."""
    app.add_config_value("doxygen_toc_enabled", default=True, rebuild="html", types=bool)
    
    # Run AFTER build is finished, so all HTML files exist
    app.connect("build-finished", _inject_doxygen_to_sphinx_toc, priority=1001)
    
    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
        "version": "1.0.0",
    }
