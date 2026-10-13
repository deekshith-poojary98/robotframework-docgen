"""
Dashboard generation for multi-library documentation.

This module generates a dashboard UI that provides:
- Homepage listing all libraries
- Global keyword search across all libraries
- Navigation between libraries
"""

import json
import importlib.resources
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Mapping, Optional
from functools import lru_cache

from robotframework_docgen.generator import DocumentationGenerator
from robotframework_docgen.theme import (
    logo_url_for_theme,
    on_accent_for_theme,
    resolve_theme_tokens,
)


def generate_dashboard(
    output_base_dir: Path,
    libraries_metadata: List[Dict[str, Any]],
    site_config: Dict[str, Any]
) -> None:
    """
    Generate dashboard files after all libraries are processed.
    
    Args:
        output_base_dir: Base output directory (e.g., output/)
        libraries_metadata: List of library metadata dictionaries
        site_config: Site-wide configuration from config.json
    """
    # Create assets directory
    assets_dir = output_base_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate search index
    search_index = _generate_search_index(libraries_metadata)
    search_index_path = assets_dir / "search-index.json"
    search_index_path.write_text(json.dumps(search_index, indent=2), encoding="utf-8")
    
    # Generate CSS (honors site theme / theme_file)
    css_path = assets_dir / "style.css"
    css_path.write_text(_generate_dashboard_css(site_config), encoding="utf-8")
    
    # Generate JavaScript
    js_path = assets_dir / "app.js"
    js_path.write_text(_generate_dashboard_js(), encoding="utf-8")
    
    search_js_path = assets_dir / "search.js"
    search_js_path.write_text(_generate_search_js(), encoding="utf-8")
    
    # Generate dashboard homepage
    index_path = output_base_dir / "index.html"
    index_path.write_text(
        _generate_dashboard_html(libraries_metadata, site_config),
        encoding="utf-8"
    )


def _generate_search_index(libraries_metadata: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Generate search index JSON for client-side keyword and library search."""
    search_index = []
    
    for lib_meta in libraries_metadata:
        library_name = lib_meta.get("name", "")
        library_url = lib_meta.get("url", "")
        library_description = lib_meta.get("description", "")
        library_author = lib_meta.get("author", "")
        library_maintainer = lib_meta.get("maintainer", "")
        library_license = lib_meta.get("license", "")
        library_group = lib_meta.get("group") or ""
        
        # Add library entry with metadata for filtering
        entry = {
            "type": "library",
            "name": library_name,
            "description": library_description,
            "url": library_url,
            "author": library_author,
            "maintainer": library_maintainer,
            "license": library_license,
        }
        # Include grouping info for potential future client-side uses
        if library_group:
            entry["group"] = library_group
        search_index.append(entry)
        
        # Add keyword entries
        for keyword in lib_meta.get("keywords", []):
            keyword_name = keyword.get("name", "")
            # Must match DocumentationGenerator.keyword_anchor_id. A space-only
            # slug leaves `${}` in the fragment, so embedded-argument keywords
            # never scroll into view from dashboard search.
            keyword_id = DocumentationGenerator.keyword_anchor_id(keyword_name)
            
            search_index.append({
                "type": "keyword",
                "library": library_name,
                "keyword": keyword_name,
                "url": f"{library_url}#{keyword_id}",
                "library_license": library_license  # Include for filtering keywords by library license
            })
    
    return search_index


def _dashboard_theme_override_css(site_config: Optional[Mapping[str, Any]]) -> str:
    """Resolve site theme tokens into a trailing ``:root`` override block."""
    css_vars = resolve_theme_tokens(site_config or {})
    if not css_vars:
        return ""
    rendered = dict(css_vars)
    on_accent = on_accent_for_theme(css_vars)
    if on_accent:
        rendered["--on-accent"] = on_accent
    lines = [":root {"]
    for var_name in sorted(rendered.keys()):
        lines.append(f"    {var_name}: {rendered[var_name]};")
    lines.append("}")
    return "\n".join(lines)


def _generate_dashboard_css(site_config: Optional[Mapping[str, Any]] = None) -> str:
    """Generate CSS for dashboard matching library design."""
    # TODO: Separate dashboard CSS into external asset file and load it here
    base = """/* Dashboard Styles - Matching Library Design */
:root {
    --bg: #0f172a;
    --bg-alt: #020617;
    --card: #020617;
    --accent: #38bdf8;
    --accent-soft: rgba(56, 189, 248, 0.15);
    --border: #1e293b;
    --text: #e5e7eb;
    --muted: #9ca3af;
    --on-accent: #0b1120;
    --hero-badge-bg: color-mix(in srgb, var(--accent) 10%, transparent);
    --hero-badge-text: var(--accent);
    --hero-badge-kind-bg: rgba(167, 139, 250, 0.12);
    --hero-badge-kind-text: #c4b5fd;
    --mono: "SF Mono", ui-monospace, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    --sans: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

* {
    box-sizing: border-box;
}

/* Thin scrollbars (Firefox + WebKit/Blink) */
* {
    scrollbar-width: thin;
    scrollbar-color: color-mix(in srgb, var(--accent) 35%, transparent) transparent;
}

*::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}

*::-webkit-scrollbar-track {
    background: transparent;
}

*::-webkit-scrollbar-thumb {
    background: color-mix(in srgb, var(--accent) 30%, transparent);
    border-radius: 3px;
}

*::-webkit-scrollbar-thumb:hover {
    background: color-mix(in srgb, var(--accent) 50%, transparent);
}

html {
    background-color: var(--bg-alt);
}

body {
    margin: 0;
    font-family: var(--sans);
    background-color: var(--bg-alt);
    background-image: radial-gradient(circle at top, color-mix(in srgb, var(--border) 85%, var(--accent) 15%) 0, var(--bg-alt) 55%);
    background-attachment: fixed;
    background-repeat: no-repeat;
    background-size: 100% 100%;
    color: var(--text);
    line-height: 1.6;
    min-height: 100vh;
}

.skip-link {
    position: absolute;
    left: -999px;
    top: 0;
    background: var(--accent);
    color: var(--on-accent);
    padding: 0.5rem 0.75rem;
    z-index: 100;
    border-radius: 0 0 6px 0;
    font-weight: 600;
}

.skip-link:focus {
    left: 0;
}

.visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}

a {
    color: var(--accent);
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

header {
    position: sticky;
    top: 0;
    z-index: 30;
    backdrop-filter: blur(16px);
    background: linear-gradient(to right, color-mix(in srgb, var(--bg) 95%, transparent), color-mix(in srgb, var(--bg) 80%, transparent));
    border-bottom: 1px solid var(--border);
    padding: 0.9rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 2rem;
}

header .brand {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex: 1;
}

header .brand .brand-logo {
    height: 32px;
    width: auto;
    display: block;
}

header .header-right {
    display: flex;
    align-items: center;
    gap: 1rem;
}

header .language-selector {
    position: relative;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

header .language-selector .language-icon {
    position: absolute;
    left: 0.6rem;
    color: var(--muted);
    pointer-events: none;
    z-index: 1;
    width: 16px;
    height: 16px;
}

header .language-selector select {
    padding: 0.5rem 0.75rem 0.5rem 2rem;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: color-mix(in srgb, var(--card) 92%, transparent);
    color: var(--text);
    font-size: 0.85rem;
    font-family: var(--sans);
    cursor: pointer;
    transition: all 0.3s ease;
    backdrop-filter: blur(8px);
    appearance: none;
    width: auto;
}

header .language-selector select:focus {
    outline: none;
    border-color: var(--accent);
    background: color-mix(in srgb, var(--card) 96%, transparent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 10%, transparent);
}

header .language-selector select:hover {
    border-color: var(--accent-soft);
}

header .keyword-search {
    display: flex;
    align-items: center;
    position: relative;
    min-width: 400px;
    width: 400px;
}

header .keyword-search .search-icon {
    position: absolute;
    left: 0.75rem;
    color: var(--muted);
    pointer-events: none;
    z-index: 1;
    width: 18px;
    height: 18px;
}

header .keyword-search input {
    width: 100%;
    padding: 0.6rem 0.75rem 0.6rem 2.5rem;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: color-mix(in srgb, var(--card) 92%, transparent);
    color: var(--text);
    font-size: 0.9rem;
    font-family: var(--sans);
    transition: all 0.3s ease;
    backdrop-filter: blur(8px);
}

header .keyword-search input:focus {
    outline: none;
    border-color: var(--accent);
    background: color-mix(in srgb, var(--card) 96%, transparent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 10%, transparent);
}

header .keyword-search input::placeholder {
    color: var(--muted);
    font-size: 0.85rem;
}

header .keyword-search-results {
    position: absolute;
    top: calc(100% + 0.5rem);
    left: 0;
    right: 0;
    max-height: 450px;
    overflow-y: auto;
    background: color-mix(in srgb, var(--card) 98%, transparent);
    border: 1px solid var(--border);
    border-radius: 12px;
    box-shadow: 0 12px 32px rgba(0,0,0,0.4), 0 0 0 1px color-mix(in srgb, var(--accent) 10%, transparent);
    display: none;
    z-index: 100;
    backdrop-filter: blur(20px);
    padding: 0.5rem;
}

header .keyword-search-results.active {
    display: block;
}

header .keyword-search-results .search-result-item {
    padding: 0.875rem 1rem;
    margin-bottom: 0.25rem;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
    border: 1px solid transparent;
    background: color-mix(in srgb, var(--bg) 50%, transparent);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
}

header .keyword-search-results .search-result-item:last-child {
    margin-bottom: 0;
}

header .keyword-search-results .search-result-item:hover,
header .keyword-search-results .search-result-item.highlighted {
    background: var(--accent-soft);
    border-color: color-mix(in srgb, var(--accent) 30%, transparent);
    transform: translateX(2px);
}

header .keyword-search-results .result-title {
    color: var(--accent);
    text-decoration: none;
    font-weight: 600;
    font-size: 0.95rem;
    display: inline-block;
    line-height: 1.4;
    transition: color 0.2s ease;
    flex: 1;
}

header .keyword-search-results .search-result-item:hover .result-title {
    color: color-mix(in srgb, var(--accent) 75%, white);
}

header .keyword-search-results .library-name {
    color: var(--muted);
    font-size: 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.375rem;
    white-space: nowrap;
    flex-shrink: 0;
}

header .keyword-search-results .library-name::before {
    content: '📚';
    font-size: 0.75rem;
    opacity: 0.7;
}

header h1 {
    font-size: 1.05rem;
    margin: 0;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text);
}

.dashboard-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 1.75rem 2.4rem 3rem;
}

.dashboard-header {
    margin-bottom: 2.5rem;
}

.dashboard-header h2 {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
    color: var(--text);
    font-weight: 600;
    background: linear-gradient(135deg, var(--text) 0%, var(--accent) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.dashboard-header p {
    color: var(--muted);
    margin-top: 0;
    max-width: 40rem;
    font-size: 1.05rem;
}

.dashboard-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2.5rem;
}

.stat-card {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    transition: all 0.3s ease;
}

.stat-card:hover {
    background: var(--card);
    border-color: var(--accent-soft);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px color-mix(in srgb, var(--accent) 10%, transparent);
}

.stat-card .stat-value {
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--accent);
    margin-bottom: 0.5rem;
    line-height: 1;
}

.stat-card .stat-label {
    font-size: 0.9rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.search-container {
    margin-bottom: 2rem;
    position: relative;
    max-width: 600px;
}

.search-wrapper {
    position: relative;
    display: flex;
    align-items: center;
}

.search-icon {
    position: absolute;
    left: 1rem;
    color: var(--muted);
    pointer-events: none;
    z-index: 1;
}

.search-input {
    width: 100%;
    padding: 0.75rem 1rem 0.75rem 2.75rem;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: color-mix(in srgb, var(--card) 92%, transparent);
    color: var(--text);
    font-size: 0.95rem;
    font-family: var(--sans);
    transition: all 0.3s ease;
    backdrop-filter: blur(8px);
}

.search-input:focus {
    outline: none;
    border-color: var(--accent);
    background: color-mix(in srgb, var(--card) 96%, transparent);
    box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 10%, transparent);
}

.search-input::placeholder {
    color: var(--muted);
}

.search-result-item {
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
    background: color-mix(in srgb, var(--bg) 70%, transparent);
    border-radius: 10px;
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent);
    transition: all 0.2s ease;
    backdrop-filter: blur(8px);
    display: flex;
    align-items: flex-start;
    gap: 1rem;
}

.search-result-item:hover {
    background: color-mix(in srgb, var(--bg) 90%, transparent);
    transform: translateX(4px);
    box-shadow: 0 4px 12px color-mix(in srgb, var(--accent) 10%, transparent);
}

.search-result-library {
    border-left-color: #10b981;
}

.search-result-keyword {
    border-left-color: var(--accent);
}

.result-icon {
    flex-shrink: 0;
    margin-top: 0.125rem;
    color: var(--accent);
}

.search-result-library .result-icon {
    color: #10b981;
}

.result-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.result-title {
    color: var(--accent);
    text-decoration: none;
    font-weight: 600;
    font-size: 1rem;
    transition: color 0.2s ease;
}

.search-result-library .result-title {
    color: #10b981;
}

.result-title:hover {
    text-decoration: underline;
}

.result-description {
    color: var(--muted);
    font-size: 0.9rem;
    line-height: 1.5;
    margin-top: 0.25rem;
}

.search-result-item .library-name {
    color: var(--muted);
    font-size: 0.85rem;
    margin-top: 0.25rem;
}

.result-type {
    display: inline-block;
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    background: color-mix(in srgb, var(--accent) 10%, transparent);
    color: var(--accent);
    font-weight: 500;
    margin-top: 0.25rem;
    width: fit-content;
}

.search-result-library .result-type {
    background: rgba(16,185,129,0.1);
    color: #10b981;
}

.libraries-section {
    margin-top: 3rem;
}

.view-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.15rem;
    border-radius: 999px;
    background: color-mix(in srgb, var(--bg) 80%, transparent);
    border: 1px solid var(--border);
}

.view-toggle-btn {
    position: relative;
    border: none;
    background: transparent;
    color: var(--muted);
    font-size: 0.8rem;
    font-weight: 500;
    padding: 0.35rem 0.75rem;
    border-radius: 999px;
    cursor: pointer;
    transition: background 0.2s ease, color 0.2s ease;
}

.view-toggle-btn.view-toggle-btn-active {
    background: var(--accent-soft);
    color: var(--accent);
}

.groups-grid {
    margin-top: 1rem;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 1.5rem;
}

.group-card-title {
    margin: 0 0 0.5rem 0;
    font-size: 1.3rem;
    font-weight: 600;
    color: var(--text);
    cursor: pointer;
}

.group-card:hover .group-card-title {
    color: var(--accent);
}

.group-card-meta {
    font-size: 0.85rem;
    color: var(--muted);
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    align-items: center;
}

.group-card-meta strong {
    color: var(--accent);
}


.group-context {
    margin-top: 1rem;
    margin-bottom: 0.5rem;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
}

.group-breadcrumb {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.85rem;
    color: var(--muted);
}

.group-breadcrumb-root {
    padding: 0;
    border: none;
    background: transparent;
    color: var(--accent);
    cursor: pointer;
    font-size: 0.85rem;
}

.group-breadcrumb-name {
    color: var(--text);
    font-weight: 500;
}

.group-meta {
    font-size: 0.8rem;
    color: var(--muted);
    display: flex;
    align-items: center;
    gap: 0.35rem;
}

.group-back-btn {
    border-radius: 999px;
    border: 1px solid var(--border);
    background: color-mix(in srgb, var(--bg) 85%, transparent);
    color: var(--muted);
    font-size: 0.8rem;
    padding: 0.35rem 0.75rem;
    cursor: pointer;
    transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.group-back-btn:hover {
    background: var(--bg);
    border-color: var(--accent-soft);
    color: var(--accent);
}

.libraries-section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
    gap: 1rem;
}

.header-controls {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    flex-wrap: wrap;
}

.libraries-section-title {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text);
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.libraries-section-title::before {
    content: '';
    width: 4px;
    height: 24px;
    background: var(--accent);
    border-radius: 2px;
}

.sort-controls {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.sort-label {
    color: var(--muted);
    font-size: 0.9rem;
    font-weight: 500;
}

.sort-select,
.export-select,
.filters-toggle-btn {
    padding: 0.5rem 0.75rem;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: color-mix(in srgb, var(--card) 92%, transparent);
    color: var(--text);
    font-size: 0.9rem;
    font-family: var(--sans);
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    backdrop-filter: blur(8px);
    height: auto;
    line-height: 1.5;
    box-sizing: border-box;
}

.controls-disabled .sort-select,
.controls-disabled .export-select,
.controls-disabled .filters-toggle-btn {
    cursor: not-allowed;
    opacity: 0.6;
    pointer-events: auto;
}

.sort-select,
.export-select {
    min-width: 140px;
}

.filters-toggle-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    appearance: none;
    -webkit-appearance: none;
    -moz-appearance: none;
    text-align: left;
    min-width: 110px;
}

.sort-select:focus,
.export-select:focus,
.filters-toggle-btn:focus {
    outline: none;
    border-color: var(--accent);
    background: color-mix(in srgb, var(--card) 96%, transparent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 10%, transparent);
}

.sort-select:hover,
.export-select:hover,
.filters-toggle-btn:hover {
    border-color: var(--accent-soft);
    background: color-mix(in srgb, var(--card) 96%, transparent);
}

.filters-toggle-btn svg {
    width: 18px;
    height: 18px;
    color: var(--accent);
    flex-shrink: 0;
}

.filters-toggle-btn .filters-toggle-icon {
    width: 16px;
    height: 16px;
    transition: transform 0.2s ease;
    color: var(--accent);
    margin-left: 0.25rem;
}

.filters-toggle-btn.active .filters-toggle-icon {
    transform: rotate(180deg);
}

.export-controls {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.filters-container {
    margin-bottom: 1.5rem;
    padding: 0;
    background: transparent;
    border: none;
}

.filters-header {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    margin-bottom: 0.75rem;
    padding: 0.5rem 0;
}

.clear-filters-btn {
    padding: 0.4rem 0.75rem;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: rgba(239,68,68,0.1);
    color: #ef4444;
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    font-family: var(--sans);
}

.clear-filters-btn:hover {
    background: rgba(239,68,68,0.2);
    border-color: #ef4444;
}

.filters-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 0.75rem;
    max-height: 500px;
    overflow: hidden;
    transition: max-height 0.3s ease, opacity 0.2s ease, margin-top 0.3s ease;
    opacity: 1;
    margin-top: 0.5rem;
}

.filters-container.collapsed .filters-grid {
    max-height: 0;
    opacity: 0;
    margin-top: 0;
    overflow: hidden;
}

.filter-group {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
}

.filter-label {
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.filter-select {
    padding: 0.5rem 0.75rem;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: color-mix(in srgb, var(--card) 92%, transparent);
    color: var(--text);
    font-size: 0.9rem;
    font-family: var(--sans);
    cursor: pointer;
    transition: all 0.2s ease;
    backdrop-filter: blur(8px);
}

.filter-select:focus {
    outline: none;
    border-color: var(--accent);
    background: color-mix(in srgb, var(--card) 96%, transparent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 10%, transparent);
}

.filter-select:hover {
    border-color: var(--accent-soft);
}

.libraries-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 2rem;
}

.library-card {
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 2rem;
    background: var(--bg);
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}

.library-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--accent), transparent);
    opacity: 0;
    transition: opacity 0.3s ease;
}

.library-card:hover {
    background: var(--card);
    border-color: var(--accent-soft);
    transform: translateY(-4px);
    box-shadow: 0 12px 32px var(--accent-soft);
}

.library-card:hover::before {
    opacity: 1;
}

.library-card h2 {
    margin: 0 0 1rem 0;
    font-size: 1.75rem;
    font-weight: 600;
}

.library-card h2 a {
    color: var(--text);
    text-decoration: none;
    transition: color 0.2s ease;
}

.library-card h2 a:hover {
    color: var(--accent);
}

.library-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin: 0.25rem 0 0.75rem 0;
}

.library-meta {
    color: var(--muted);
    font-size: 0.85rem;
    margin: 0.75rem 0;
    display: block;
}

.library-description {
    color: var(--muted);
    margin: 1rem 0;
    line-height: 1.6;
    font-size: 0.95rem;
}

.library-stats {
    margin-top: 1.5rem;
    padding-top: 1.25rem;
    border-top: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--muted);
    font-size: 0.9rem;
    font-weight: 500;
}

.library-stats svg {
    width: 18px;
    height: 18px;
    color: var(--accent);
    flex-shrink: 0;
}

.library-meta-header {
    margin-top: 1.25rem;
    padding-top: 1.25rem;
    border-top: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    cursor: pointer;
    user-select: none;
    transition: color 0.2s ease;
}

.library-meta-header:hover {
    color: var(--accent);
}

.library-meta-header .meta-toggle {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--muted);
}

.library-meta-header:hover .meta-toggle {
    color: var(--accent);
}

.library-meta-header .meta-toggle-icon {
    width: 16px;
    height: 16px;
    transition: transform 0.2s ease;
    color: var(--accent);
}

.library-meta-header.collapsed .meta-toggle-icon {
    transform: rotate(-90deg);
}

.library-meta-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-top: 0.75rem;
    max-height: 500px;
    overflow: hidden;
    transition: max-height 0.3s ease, opacity 0.2s ease, margin-top 0.3s ease;
    opacity: 1;
}

.library-meta-list.collapsed {
    max-height: 0;
    opacity: 0;
    margin-top: 0;
    overflow: hidden;
}

.library-meta-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    color: var(--muted);
    font-size: 0.85rem;
}

.library-meta-item svg {
    width: 16px;
    height: 16px;
    color: var(--accent);
    flex-shrink: 0;
    opacity: 0.8;
}

.library-meta-item .meta-label {
    font-weight: 500;
    color: var(--text);
    min-width: 80px;
}

.library-meta-item .meta-value {
    color: var(--muted);
}

.badge {
    font-size: 0.75rem;
    padding: 0.35rem 0.75rem;
    border-radius: 999px;
    border: 1px solid color-mix(in srgb, var(--accent) 40%, var(--border) 60%);
    background: var(--hero-badge-bg);
    color: var(--hero-badge-text);
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    margin-right: 0.5rem;
    font-weight: 500;
    transition: all 0.2s ease;
}

.badge:hover {
    background: color-mix(in srgb, var(--accent) 20%, transparent);
    border-color: color-mix(in srgb, var(--accent) 50%, var(--border) 50%);
}

.badge.badge-kind {
    border-color: color-mix(in srgb, var(--hero-badge-kind-text) 45%, transparent);
    color: var(--hero-badge-kind-text);
    background: var(--hero-badge-kind-bg);
}

.badge.badge-group {
    border-color: color-mix(in srgb, var(--accent) 40%, transparent);
    background: var(--accent-soft);
    color: var(--accent);
}

.no-results {
    padding: 2rem;
    text-align: center;
    color: var(--muted);
    display: none;
    font-style: italic;
}

.no-results.active {
    display: block;
}

footer {
    border-top: 1px solid var(--border);
    padding: 1.2rem 2.4rem 1.6rem;
    margin-top: 3rem;
    text-align: center;
    color: var(--muted);
    font-size: 0.9rem;
}

footer a {
    color: var(--accent);
    text-decoration: none;
}

footer a:hover {
    text-decoration: underline;
}

@media (max-width: 768px) {
    header {
        flex-direction: column;
        gap: 1rem;
        padding: 1rem;
    }
    
    header .header-right {
        width: 100%;
        flex-direction: column;
        gap: 1rem;
    }
    
    header .language-selector {
        width: 100%;
        align-self: flex-end;
    }
    
    header .language-selector select {
        width: 100%;
    }
    
    header .keyword-search {
        width: 100%;
        min-width: auto;
    }
    
    .dashboard-container {
        padding: 1rem 1.5rem 2rem;
    }
    
    .dashboard-stats {
        grid-template-columns: 1fr;
        gap: 1rem;
    }
    
    .stat-card .stat-value {
        font-size: 2rem;
    }
    
    .libraries-grid {
        grid-template-columns: 1fr;
        gap: 1.5rem;
    }
    
    .dashboard-header h2 {
        font-size: 1.75rem;
    }
    
    .libraries-section-title {
        font-size: 1.25rem;
    }
    
    .libraries-section-header {
        flex-direction: column;
        align-items: flex-start;
    }
    
    .header-controls {
        width: 100%;
        flex-direction: column;
        gap: 1rem;
    }
    
    .sort-controls {
        width: 100%;
    }
    
    .sort-select {
        width: 100%;
        min-width: auto;
    }
    
    .export-controls,
    .export-select {
        width: 100%;
        min-width: auto;
    }
    
    .filters-grid {
        grid-template-columns: 1fr;
    }
}
"""
    override = _dashboard_theme_override_css(site_config)
    if override:
        return base + "\n\n/* Theme overrides from site.theme / site.theme_file */\n" + override + "\n"
    return base


def _generate_dashboard_js() -> str:
    """Generate JavaScript for dashboard functionality."""
    # TODO: Separate dashboard JavaScript into external asset file and load it here
    return """// Dashboard JavaScript
// Translation dictionary
const translations = {
    en: {
        site_name: '',
        dashboard_title: 'Documentation Dashboard',
        site_description: '',
        libraries: 'Libraries',
        library: 'library',
        resources: 'Resources',
        resource: 'resource',
        total_keywords: 'Total Keywords',
        search_keywords: 'Search keywords...',
        search_libraries: 'Search libraries...',
        search_resources: 'Search resources...',
        search_groups: 'Search groups...',
        no_libraries_found: 'No libraries found.',
        no_resources_found: 'No resources found.',
        no_groups_found: 'No groups found.',
        available_libraries: 'Available Libraries',
        available_resources: 'Available Resources',
        available_groups: 'Available Groups',
        sort_by: 'Sort by:',
        sort_name_asc: 'Name (A–Z)',
        sort_keywords_desc: 'Keyword count (desc)',
        export_as: 'Export as',
        filters: 'Filters',
        clear_all: 'Clear All',
        author: 'Author:',
        maintainer: 'Maintainer:',
        license: 'License:',
        rf_version: 'RF Version:',
        python: 'Python:',
        version: 'Version',
        all_authors: 'All Authors',
        all_maintainers: 'All Maintainers',
        all_licenses: 'All Licenses',
        all_versions: 'All Versions',
        generated_by: 'Generated by',
        last_updated: 'Last updated',
        keyword: 'keyword',
        keywords: 'keywords',
        groups: 'Groups',
        back_to_groups: '← Back to Groups',
        metadata: 'Metadata'
    },
    es: {
        site_name: '',
        dashboard_title: 'Panel de Documentación',
        site_description: '',
        libraries: 'Bibliotecas',
        library: 'biblioteca',
        resources: 'Recursos',
        resource: 'recurso',
        total_keywords: 'Palabras Clave Totales',
        search_keywords: 'Buscar palabras clave...',
        search_libraries: 'Buscar bibliotecas...',
        search_resources: 'Buscar recursos...',
        search_groups: 'Buscar grupos...',
        no_libraries_found: 'No se encontraron bibliotecas.',
        no_resources_found: 'No se encontraron recursos.',
        no_groups_found: 'No se encontraron grupos.',
        available_libraries: 'Bibliotecas Disponibles',
        available_resources: 'Recursos Disponibles',
        available_groups: 'Grupos Disponibles',
        sort_by: 'Ordenar por:',
        sort_name_asc: 'Nombre (A–Z)',
        sort_keywords_desc: 'Cantidad de palabras clave (desc)',
        export_as: 'Exportar como',
        filters: 'Filtros',
        clear_all: 'Limpiar Todo',
        author: 'Autor:',
        maintainer: 'Mantenedor:',
        license: 'Licencia:',
        rf_version: 'Versión RF:',
        python: 'Python:',
        version: 'Versión',
        all_authors: 'Todos los Autores',
        all_maintainers: 'Todos los Mantenedores',
        all_licenses: 'Todas las Licencias',
        all_versions: 'Todas las Versiones',
        generated_by: 'Generado por',
        last_updated: 'Última actualización',
        keyword: 'palabra clave',
        keywords: 'palabras clave',
        groups: 'Grupos',
        back_to_groups: '← Volver a Grupos',
        metadata: 'Metadatos'
    },
    fr: {
        site_name: '',
        dashboard_title: 'Tableau de Bord de Documentation',
        site_description: '',
        libraries: 'Bibliothèques',
        library: 'bibliothèque',
        resources: 'Ressources',
        resource: 'ressource',
        total_keywords: 'Mots-clés Totaux',
        search_keywords: 'Rechercher des mots-clés...',
        search_libraries: 'Rechercher des bibliothèques...',
        search_resources: 'Rechercher des ressources...',
        search_groups: 'Rechercher des groupes...',
        no_libraries_found: 'Aucune bibliothèque trouvée.',
        no_resources_found: 'Aucune ressource trouvée.',
        no_groups_found: 'Aucun groupe trouvé.',
        available_libraries: 'Bibliothèques Disponibles',
        available_resources: 'Ressources Disponibles',
        available_groups: 'Groupes Disponibles',
        sort_by: 'Trier par:',
        sort_name_asc: 'Nom (A–Z)',
        sort_keywords_desc: 'Nombre de mots-clés (desc)',
        export_as: 'Exporter comme',
        filters: 'Filtres',
        clear_all: 'Tout Effacer',
        author: 'Auteur:',
        maintainer: 'Mainteneur:',
        license: 'Licence:',
        rf_version: 'Version RF:',
        python: 'Python:',
        version: 'Version',
        all_authors: 'Tous les Auteurs',
        all_maintainers: 'Tous les Mainteneurs',
        all_licenses: 'Toutes les Licences',
        all_versions: 'Toutes les Versions',
        generated_by: 'Généré par',
        last_updated: 'Dernière mise à jour',
        keyword: 'mot-clé',
        keywords: 'mots-clés',
        groups: 'Groupes',
        back_to_groups: '← Retour aux groupes',
        metadata: 'Métadonnées'
    },
    de: {
        site_name: '',
        dashboard_title: 'Dokumentations-Dashboard',
        site_description: '',
        libraries: 'Bibliotheken',
        library: 'Bibliothek',
        resources: 'Ressourcen',
        resource: 'Ressource',
        total_keywords: 'Gesamt-Schlüsselwörter',
        search_keywords: 'Schlüsselwörter suchen...',
        search_libraries: 'Bibliotheken suchen...',
        search_resources: 'Ressourcen suchen...',
        search_groups: 'Gruppen suchen...',
        no_libraries_found: 'Keine Bibliotheken gefunden.',
        no_resources_found: 'Keine Ressourcen gefunden.',
        no_groups_found: 'Keine Gruppen gefunden.',
        available_libraries: 'Verfügbare Bibliotheken',
        available_resources: 'Verfügbare Ressourcen',
        available_groups: 'Verfügbare Gruppen',
        sort_by: 'Sortieren nach:',
        sort_name_asc: 'Name (A–Z)',
        sort_keywords_desc: 'Schlüsselwortanzahl (abst)',
        export_as: 'Exportieren als',
        filters: 'Filter',
        clear_all: 'Alle Löschen',
        author: 'Autor:',
        maintainer: 'Wartung:',
        license: 'Lizenz:',
        rf_version: 'RF-Version:',
        python: 'Python:',
        version: 'Version',
        all_authors: 'Alle Autoren',
        all_maintainers: 'Alle Wartungen',
        all_licenses: 'Alle Lizenzen',
        all_versions: 'Alle Versionen',
        generated_by: 'Erstellt von',
        last_updated: 'Zuletzt aktualisiert',
        keyword: 'Schlüsselwort',
        keywords: 'Schlüsselwörter',
        groups: 'Gruppen',
        back_to_groups: '← Zurück zu Gruppen',
        metadata: 'Metadaten'
    },
    zh: {
        site_name: '',
        dashboard_title: '文档仪表板',
        site_description: '',
        libraries: '库',
        library: '库',
        resources: '资源',
        resource: '资源',
        total_keywords: '总关键字',
        search_keywords: '搜索关键字...',
        search_libraries: '搜索库...',
        search_resources: '搜索资源...',
        search_groups: '搜索分组...',
        no_libraries_found: '未找到库。',
        no_resources_found: '未找到资源。',
        no_groups_found: '未找到分组。',
        available_libraries: '可用库',
        available_resources: '可用资源',
        available_groups: '可用分组',
        sort_by: '排序方式:',
        sort_name_asc: '名称 (A–Z)',
        sort_keywords_desc: '关键字数量 (降序)',
        export_as: '导出为',
        filters: '筛选器',
        clear_all: '清除全部',
        author: '作者:',
        maintainer: '维护者:',
        license: '许可证:',
        rf_version: 'RF 版本:',
        python: 'Python:',
        version: '版本',
        all_authors: '所有作者',
        all_maintainers: '所有维护者',
        all_licenses: '所有许可证',
        all_versions: '所有版本',
        generated_by: '由生成',
        last_updated: '最后更新',
        keyword: '关键字',
        keywords: '关键字',
        groups: '分组',
        back_to_groups: '← 返回分组',
        metadata: '元数据'
    },
    ja: {
        site_name: '',
        dashboard_title: 'ドキュメントダッシュボード',
        site_description: '',
        libraries: 'ライブラリ',
        library: 'ライブラリ',
        resources: 'リソース',
        resource: 'リソース',
        total_keywords: '総キーワード数',
        search_keywords: 'キーワードを検索...',
        search_libraries: 'ライブラリを検索...',
        search_resources: 'リソースを検索...',
        search_groups: 'グループを検索...',
        no_libraries_found: 'ライブラリが見つかりません。',
        no_resources_found: 'リソースが見つかりません。',
        no_groups_found: 'グループが見つかりません。',
        available_libraries: '利用可能なライブラリ',
        available_resources: '利用可能なリソース',
        available_groups: '利用可能なグループ',
        sort_by: '並び替え:',
        sort_name_asc: '名前 (A–Z)',
        sort_keywords_desc: 'キーワード数 (降順)',
        export_as: 'エクスポート',
        filters: 'フィルター',
        clear_all: 'すべてクリア',
        author: '作成者:',
        maintainer: 'メンテナー:',
        license: 'ライセンス:',
        rf_version: 'RF バージョン:',
        python: 'Python:',
        version: 'バージョン',
        all_authors: 'すべての作成者',
        all_maintainers: 'すべてのメンテナー',
        all_licenses: 'すべてのライセンス',
        all_versions: 'すべてのバージョン',
        generated_by: '生成元',
        last_updated: '最終更新',
        keyword: 'キーワード',
        keywords: 'キーワード',
        groups: 'グループ',
        back_to_groups: '← グループに戻る',
        metadata: 'メタデータ'
    },
    pt: {
        site_name: '',
        dashboard_title: 'Painel de Documentação',
        site_description: '',
        libraries: 'Bibliotecas',
        library: 'biblioteca',
        resources: 'Recursos',
        resource: 'recurso',
        total_keywords: 'Total de Palavras-chave',
        search_keywords: 'Pesquisar palavras-chave...',
        search_libraries: 'Pesquisar bibliotecas...',
        search_resources: 'Pesquisar recursos...',
        search_groups: 'Pesquisar grupos...',
        no_libraries_found: 'Nenhuma biblioteca encontrada.',
        no_resources_found: 'Nenhum recurso encontrado.',
        no_groups_found: 'Nenhum grupo encontrado.',
        available_libraries: 'Bibliotecas Disponíveis',
        available_resources: 'Recursos Disponíveis',
        available_groups: 'Grupos Disponíveis',
        sort_by: 'Ordenar por:',
        sort_name_asc: 'Nome (A–Z)',
        sort_keywords_desc: 'Contagem de palavras-chave (desc)',
        export_as: 'Exportar como',
        filters: 'Filtros',
        clear_all: 'Limpar Tudo',
        author: 'Autor:',
        maintainer: 'Mantenedor:',
        license: 'Licença:',
        rf_version: 'Versão RF:',
        python: 'Python:',
        version: 'Versão',
        all_authors: 'Todos os Autores',
        all_maintainers: 'Todos os Mantenedores',
        all_licenses: 'Todas as Licenças',
        all_versions: 'Todas as Versões',
        generated_by: 'Gerado por',
        last_updated: 'Última atualização',
        keyword: 'palavra-chave',
        keywords: 'palavras-chave',
        groups: 'Grupos',
        back_to_groups: '← Voltar para Grupos',
        metadata: 'Metadados'
    },
    ru: {
        site_name: '',
        dashboard_title: 'Панель Документации',
        site_description: '',
        libraries: 'Библиотеки',
        library: 'библиотека',
        resources: 'Ресурсы',
        resource: 'ресурс',
        total_keywords: 'Всего Ключевых Слов',
        search_keywords: 'Поиск ключевых слов...',
        search_libraries: 'Поиск библиотек...',
        search_resources: 'Поиск ресурсов...',
        search_groups: 'Поиск групп...',
        no_libraries_found: 'Библиотеки не найдены.',
        no_resources_found: 'Ресурсы не найдены.',
        no_groups_found: 'Группы не найдены.',
        available_libraries: 'Доступные Библиотеки',
        available_resources: 'Доступные Ресурсы',
        available_groups: 'Доступные Группы',
        sort_by: 'Сортировать по:',
        sort_name_asc: 'Имя (А–Я)',
        sort_keywords_desc: 'Количество ключевых слов (убыв)',
        export_as: 'Экспортировать как',
        filters: 'Фильтры',
        clear_all: 'Очистить Все',
        author: 'Автор:',
        maintainer: 'Сопровождающий:',
        license: 'Лицензия:',
        rf_version: 'Версия RF:',
        python: 'Python:',
        version: 'Версия',
        all_authors: 'Все Авторы',
        all_maintainers: 'Все Сопровождающие',
        all_licenses: 'Все Лицензии',
        all_versions: 'Все Версии',
        generated_by: 'Создано',
        last_updated: 'Последнее обновление',
        keyword: 'ключевое слово',
        keywords: 'ключевые слова',
        groups: 'Группы',
        back_to_groups: '← Назад к группам',
        metadata: 'Метаданные'
    },
    it: {
        site_name: '',
        dashboard_title: 'Dashboard Documentazione',
        site_description: '',
        libraries: 'Librerie',
        library: 'libreria',
        resources: 'Risorse',
        resource: 'risorsa',
        total_keywords: 'Parole Chiave Totali',
        search_keywords: 'Cerca parole chiave...',
        search_libraries: 'Cerca librerie...',
        search_resources: 'Cerca risorse...',
        search_groups: 'Cerca gruppi...',
        no_libraries_found: 'Nessuna libreria trovata.',
        no_resources_found: 'Nessuna risorsa trovata.',
        no_groups_found: 'Nessun gruppo trovato.',
        available_libraries: 'Librerie Disponibili',
        available_resources: 'Risorse Disponibili',
        available_groups: 'Gruppi Disponibili',
        sort_by: 'Ordina per:',
        sort_name_asc: 'Nome (A–Z)',
        sort_keywords_desc: 'Conteggio parole chiave (disc)',
        export_as: 'Esporta come',
        filters: 'Filtri',
        clear_all: 'Cancella Tutto',
        author: 'Autore:',
        maintainer: 'Manutentore:',
        license: 'Licenza:',
        rf_version: 'Versione RF:',
        python: 'Python:',
        version: 'Versione',
        all_authors: 'Tutti gli Autori',
        all_maintainers: 'Tutti i Manutentori',
        all_licenses: 'Tutte le Licenze',
        all_versions: 'Tutte le Versioni',
        generated_by: 'Generato da',
        last_updated: 'Ultimo aggiornamento',
        keyword: 'parola chiave',
        keywords: 'parole chiave',
        groups: 'Gruppi',
        back_to_groups: '← Torna ai gruppi',
        metadata: 'Metadati'
    },
    ko: {
        site_name: '',
        dashboard_title: '문서 대시보드',
        site_description: '',
        libraries: '라이브러리',
        library: '라이브러리',
        resources: '리소스',
        resource: '리소스',
        total_keywords: '총 키워드',
        search_keywords: '키워드 검색...',
        search_libraries: '라이브러리 검색...',
        search_resources: '리소스 검색...',
        search_groups: '그룹 검색...',
        no_libraries_found: '라이브러리를 찾을 수 없습니다.',
        no_resources_found: '리소스를 찾을 수 없습니다.',
        no_groups_found: '그룹을 찾을 수 없습니다.',
        available_libraries: '사용 가능한 라이브러리',
        available_resources: '사용 가능한 리소스',
        available_groups: '사용 가능한 그룹',
        sort_by: '정렬 기준:',
        sort_name_asc: '이름 (A–Z)',
        sort_keywords_desc: '키워드 수 (내림차순)',
        export_as: '내보내기',
        filters: '필터',
        clear_all: '모두 지우기',
        author: '작성자:',
        maintainer: '유지보수자:',
        license: '라이선스:',
        rf_version: 'RF 버전:',
        python: 'Python:',
        version: '버전',
        all_authors: '모든 작성자',
        all_maintainers: '모든 유지보수자',
        all_licenses: '모든 라이선스',
        all_versions: '모든 버전',
        generated_by: '생성자',
        last_updated: '마지막 업데이트',
        keyword: '키워드',
        keywords: '키워드',
        groups: '그룹',
        back_to_groups: '← 그룹으로 돌아가기',
        metadata: '메타데이터'
    }
};

// Translation function
function translatePage(lang) {
    const t = translations[lang] || translations.en;
    
    // Translate elements with data-i18n attribute (skip if translation is empty)
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (t[key] !== undefined && t[key] !== '') {
            el.textContent = t[key];
        }
    });
    
    // Translate placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (t[key] !== undefined && t[key] !== '') {
            el.placeholder = t[key];
        }
    });
    
    // Translate option elements
    document.querySelectorAll('option[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (t[key] !== undefined && t[key] !== '') {
            el.textContent = t[key];
        }
    });
    
    // Translate keyword count in library stats
    document.querySelectorAll('[data-i18n-keyword-count]').forEach(el => {
        const count = parseInt(el.getAttribute('data-i18n-keyword-count'), 10);
        const keywordText = count === 1 ? t.keyword : t.keywords;
        el.textContent = `${count} ${keywordText}`;
    });
    
    // Store language preference
    localStorage.setItem('dashboard_language', lang);
}

    // Initialize language on page load
    document.addEventListener('DOMContentLoaded', function() {
    // Restore language preference or default to English
    let currentLanguage = localStorage.getItem('dashboard_language') || 'en';
    const langSelector = document.getElementById('language-selector');
    if (langSelector) {
        langSelector.value = currentLanguage;
        translatePage(currentLanguage);
        
        // Listen for language changes
        langSelector.addEventListener('change', function(e) {
            currentLanguage = e.target.value;
            translatePage(currentLanguage);
            // Re-render group cards in the new language (counts text)
            if (Object.keys(groupStats).length > 0) {
                renderGroupCards();
                // If currently inside a group view, refresh the header meta too
                if (currentView === 'group-libraries' && activeGroupKey) {
                    updateGroupContext(activeGroupKey);
                }
            }
            if (typeof updateSectionTitle === 'function') {
                updateSectionTitle();
            }
        });
    }
    
    // Initialize library search functionality (filters library cards)
    const searchInput = document.getElementById('global-search');
    const noResults = document.getElementById('no-results');
    const librariesGrid = document.getElementById('libraries-grid');
    let libraryCards = librariesGrid ? Array.from(librariesGrid.querySelectorAll('.library-card')) : [];

    // View and grouping state
    let currentView = 'libraries'; // 'libraries' | 'resources' | 'groups' | 'group-libraries'
    let activeGroupKey = null; // normalized group key or null

    function cardKind(card) {
        const kind = (card.getAttribute('data-kind') || 'library').toLowerCase();
        return kind === 'resource' ? 'resource' : 'library';
    }

    function normalizePersistedView(view) {
        if (view === 'all') return 'libraries';
        return view;
    }
    
    // Sort libraries function
    function sortLibraries(sortBy) {
        if (!librariesGrid || libraryCards.length === 0) return;
        
        libraryCards.sort((a, b) => {
            if (sortBy === 'name-asc') {
                const nameA = a.getAttribute('data-library-name') || '';
                const nameB = b.getAttribute('data-library-name') || '';
                return nameA.localeCompare(nameB);
            } else if (sortBy === 'keywords-desc') {
                const countA = parseInt(a.getAttribute('data-keyword-count') || '0', 10);
                const countB = parseInt(b.getAttribute('data-keyword-count') || '0', 10);
                return countB - countA; // Descending order
            }
            return 0;
        });
        
        // Re-append sorted cards
        libraryCards.forEach(card => {
            librariesGrid.appendChild(card);
        });
    }
    
    // Initialize sort dropdown
    const sortSelect = document.getElementById('library-sort');
    if (sortSelect) {
        // Restore last sort preference from localStorage
        const savedSort = localStorage.getItem('dashboard_sort');
        if (savedSort) {
            sortSelect.value = savedSort;
        }

        // Prevent native dropdown opening when disabled via view state
        sortSelect.addEventListener('mousedown', function(e) {
            if (currentView === 'groups') {
                e.preventDefault();
            }
        });
        
        sortSelect.addEventListener('change', function(e) {
            // Disable sort interaction when showing group cards
            if (currentView === 'groups') {
                e.preventDefault();
                // Reset to last saved value to avoid visual change
                const stored = localStorage.getItem('dashboard_sort');
                if (stored) {
                    sortSelect.value = stored;
                }
                return;
            }
            const sortValue = e.target.value;
            sortLibraries(sortValue);
            // Save to localStorage
            localStorage.setItem('dashboard_sort', sortValue);
        });
        
        // Initial sort (use saved preference or default to name A-Z)
        sortLibraries(sortSelect.value);
    }
    
    // Substring match only (case-insensitive). No fuzzy matching.
    function matchesSubstring(haystack, needle) {
        if (!needle) return true;
        return String(haystack || '').toLowerCase().includes(needle);
    }

    function filterGroups() {
        if (!groupsGrid) return 0;
        const searchQuery = searchInput ? searchInput.value.trim().toLowerCase() : '';
        let visibleCount = 0;
        groupsGrid.querySelectorAll('.group-card').forEach(card => {
            const key = (card.getAttribute('data-group-key') || '').toLowerCase();
            const label = (card.getAttribute('data-group-label') || '').toLowerCase();
            const matchesSearch = (
                !searchQuery ||
                matchesSubstring(label, searchQuery) ||
                (key !== '__ungrouped__' && matchesSubstring(key, searchQuery))
            );
            card.style.display = matchesSearch ? '' : 'none';
            if (matchesSearch) visibleCount++;
        });
        return visibleCount;
    }

    // Filter libraries function
    function filterLibraries() {
        // Groups tab: search group cards by name (substring only)
        if (currentView === 'groups') {
            const visibleGroups = filterGroups();
            if (noResults) {
                const t = translations[currentLanguage] || translations.en;
                noResults.setAttribute('data-i18n', 'no_groups_found');
                noResults.textContent = t.no_groups_found || 'No groups found.';
                if (visibleGroups === 0) {
                    noResults.classList.add('active');
                } else {
                    noResults.classList.remove('active');
                }
            }
            return;
        }

        if (!librariesGrid || libraryCards.length === 0) return;
        
        // Get filter values
        const filterAuthor = (document.getElementById('filter-author')?.value || '').toLowerCase();
        const filterMaintainer = (document.getElementById('filter-maintainer')?.value || '').toLowerCase();
        const filterLicense = (document.getElementById('filter-license')?.value || '').toLowerCase();
        const filterRobotFramework = (document.getElementById('filter-robot-framework')?.value || '').toLowerCase();
        const filterPython = (document.getElementById('filter-python')?.value || '').toLowerCase();
        const filterGroup = (document.getElementById('filter-group')?.value || '').toLowerCase();
        
        // Check if any filters are active
        const hasActiveFilters = filterAuthor || filterMaintainer || filterLicense || filterRobotFramework || filterPython || filterGroup;
        const clearBtn = document.getElementById('clear-filters');
        if (clearBtn) {
            clearBtn.style.display = hasActiveFilters ? 'block' : 'none';
        }
        
        // Get search query
        const searchQuery = searchInput ? searchInput.value.trim().toLowerCase() : '';
        
        // Filter library cards
        let visibleCount = 0;
        libraryCards.forEach(card => {
            // Check search match (name substring only — no fuzzy, no description)
            let matchesSearch = true;
            if (searchQuery.length > 0) {
                const libraryName = card.getAttribute('data-library-name') || '';
                matchesSearch = matchesSubstring(libraryName, searchQuery);
            }
            
            // Check filter matches
            const cardAuthor = (card.getAttribute('data-author') || '').toLowerCase();
            const cardMaintainer = (card.getAttribute('data-maintainer') || '').toLowerCase();
            const cardLicense = (card.getAttribute('data-license') || '').toLowerCase();
            const cardRobotFramework = (card.getAttribute('data-robot-framework') || '').toLowerCase();
            const cardPython = (card.getAttribute('data-python') || '').toLowerCase();
            const cardGroup = (card.getAttribute('data-group') || '').toLowerCase();
            
            const matchesAuthor = !filterAuthor || cardAuthor === filterAuthor;
            const matchesMaintainer = !filterMaintainer || cardMaintainer === filterMaintainer;
            const matchesLicense = !filterLicense || cardLicense === filterLicense;
            const matchesRobotFramework = !filterRobotFramework || cardRobotFramework === filterRobotFramework;
            const matchesPython = !filterPython || cardPython === filterPython;
            const matchesFilterGroup = !filterGroup || cardGroup === filterGroup;

            // Check group match when in group-libraries view
            const matchesGroup = (
                currentView !== 'group-libraries' ||
                !activeGroupKey ||
                (activeGroupKey === '__ungrouped__' && !cardGroup) ||
                (activeGroupKey === cardGroup)
            );

            // Libraries / Resources tabs filter by entry kind
            const kind = cardKind(card);
            const matchesKind = (
                currentView === 'groups' ||
                currentView === 'group-libraries' ||
                (currentView === 'libraries' && kind === 'library') ||
                (currentView === 'resources' && kind === 'resource')
            );
            
            // Show card if it matches all criteria
            if (matchesSearch && matchesAuthor && matchesMaintainer && matchesLicense && matchesRobotFramework && matchesPython && matchesFilterGroup && matchesGroup && matchesKind) {
                card.style.display = '';
                visibleCount++;
            } else {
                card.style.display = 'none';
            }
        });
        
        // Show/hide no results message
        if (noResults) {
            const t = translations[currentLanguage] || translations.en;
            if (currentView === 'resources') {
                noResults.setAttribute('data-i18n', 'no_resources_found');
                noResults.textContent = t.no_resources_found || 'No resources found.';
            } else {
                noResults.setAttribute('data-i18n', 'no_libraries_found');
                noResults.textContent = t.no_libraries_found || 'No libraries found.';
            }
            if (visibleCount === 0) {
                noResults.classList.add('active');
            } else {
                noResults.classList.remove('active');
            }
        }
    }
    
    // Initialize filters
    const filterSelects = ['filter-group', 'filter-author', 'filter-maintainer', 'filter-license', 'filter-robot-framework', 'filter-python'];
    filterSelects.forEach(filterId => {
        const filterSelect = document.getElementById(filterId);
        if (filterSelect) {
            // Restore saved filter from localStorage
            const savedFilter = localStorage.getItem(`dashboard_filter_${filterId}`);
            if (savedFilter) {
                filterSelect.value = savedFilter;
            }
            
            filterSelect.addEventListener('change', function(e) {
                const filterValue = e.target.value;
                // Save to localStorage
                if (filterValue) {
                    localStorage.setItem(`dashboard_filter_${filterId}`, filterValue);
                } else {
                    localStorage.removeItem(`dashboard_filter_${filterId}`);
                }
                filterLibraries();
            });
        }
    });
    
    // Clear filters button
    const clearFiltersBtn = document.getElementById('clear-filters');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', function() {
            filterSelects.forEach(filterId => {
                const filterSelect = document.getElementById(filterId);
                if (filterSelect) {
                    filterSelect.value = '';
                    localStorage.removeItem(`dashboard_filter_${filterId}`);
                }
            });
            clearFiltersBtn.style.display = 'none';
            filterLibraries();
        });
    }
    
    // Build filters container HTML
    function buildFiltersContainer() {
        if (!window.filterData) return '';
        
        const filterData = window.filterData;
        const buildFilterHTML = (label, filterId, options) => {
            if (!options || options.length === 0) return '';
            let allLabel = `All ${label}s`;
            if (label.includes('Version')) allLabel = 'All Versions';
            if (label === 'Python') allLabel = 'All Python versions';
            if (label === 'Group') allLabel = 'All Groups';
            const optionsHTML = options.map(opt => 
                `<option value="${opt.toLowerCase()}">${opt}</option>`
            ).join('');
            return `
                <div class="filter-group">
                    <label for="${filterId}" class="filter-label">${label}</label>
                    <select id="${filterId}" class="filter-select">
                        <option value="">${allLabel}</option>
                        ${optionsHTML}
                    </select>
                </div>
            `;
        };
        
        return `
            <div class="filters-container">
                <div class="filters-header">
                    <button id="clear-filters" class="clear-filters-btn" style="display: none;" data-i18n="clear_all">Clear All</button>
                </div>
                <div class="filters-grid">
                    ${buildFilterHTML('Group', 'filter-group', filterData.groups)}
                    ${buildFilterHTML('Author', 'filter-author', filterData.authors)}
                    ${buildFilterHTML('Maintainer', 'filter-maintainer', filterData.maintainers)}
                    ${buildFilterHTML('License', 'filter-license', filterData.licenses)}
                    ${buildFilterHTML('RF Version', 'filter-robot-framework', filterData.robotFrameworks)}
                    ${buildFilterHTML('Python', 'filter-python', filterData.pythons)}
                </div>
            </div>
        `;
    }
    
    // Initialize filter functionality (called when filters panel is opened)
    function initializeFilters(filtersContainer) {
        const filterSelects = ['filter-group', 'filter-author', 'filter-maintainer', 'filter-license', 'filter-robot-framework', 'filter-python'];
        filterSelects.forEach(filterId => {
            const filterSelect = document.getElementById(filterId);
            if (filterSelect) {
                const savedFilter = localStorage.getItem(`dashboard_filter_${filterId}`);
                if (savedFilter) {
                    filterSelect.value = savedFilter;
                }
                filterSelect.addEventListener('change', function(e) {
                    const filterValue = e.target.value;
                    if (filterValue) {
                        localStorage.setItem(`dashboard_filter_${filterId}`, filterValue);
                    } else {
                        localStorage.removeItem(`dashboard_filter_${filterId}`);
                    }
                    filterLibraries();
                    updateClearFiltersButton();
                });
            }
        });

        const clearFiltersBtn = document.getElementById('clear-filters');
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', function() {
                filterSelects.forEach(filterId => {
                    const select = document.getElementById(filterId);
                    if (select) {
                        select.value = '';
                        localStorage.removeItem(`dashboard_filter_${filterId}`);
                    }
                });
                clearFiltersBtn.style.display = 'none';
                filterLibraries();
            });
        }

        function updateClearFiltersButton() {
            if (!clearFiltersBtn) return;
            const hasActiveFilters = filterSelects.some(filterId => {
                const select = document.getElementById(filterId);
                return select && select.value;
            });
            clearFiltersBtn.style.display = hasActiveFilters ? 'block' : 'none';
        }

        updateClearFiltersButton();
    }
    
    // Initialize filters toggle
    const filtersToggleBtn = document.getElementById('filters-toggle-btn');
    let filtersContainer = null;
    
    if (filtersToggleBtn) {
        filtersToggleBtn.addEventListener('click', function() {
            // Only allow filters when libraries are visible
            if (currentView === 'groups') {
                return;
            }
            const librariesSection = document.querySelector('.libraries-section');
            if (!librariesSection) return;
            
            if (!filtersContainer) {
                // Create and inject filters container
                const filtersHTML = buildFiltersContainer();
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = filtersHTML;
                filtersContainer = tempDiv.firstElementChild;
                librariesSection.insertBefore(filtersContainer, document.getElementById('libraries-grid'));
                
                // Initialize filter functionality
                initializeFilters(filtersContainer);
                
                // Show container (it's already visible since we don't add collapsed class)
                filtersToggleBtn.classList.add('active');
            } else {
                // Remove container from DOM
                filtersContainer.remove();
                filtersContainer = null;
                filtersToggleBtn.classList.remove('active');
            }
        });
    }
    
    // Initial filter application
    filterLibraries();

    // ===== Grouping and view toggle =====
    const viewLibrariesBtn = document.getElementById('view-libraries-btn') || document.getElementById('view-all-btn');
    const viewResourcesBtn = document.getElementById('view-resources-btn');
    const viewGroupsBtn = document.getElementById('view-groups-btn');
    const viewToggleEl = document.getElementById('view-toggle');
    const groupsGrid = document.getElementById('groups-grid');
    const groupContextEl = document.getElementById('group-context');
    const groupBreadcrumbRoot = document.getElementById('group-breadcrumb-root');
    const groupBreadcrumbName = document.getElementById('group-breadcrumb-name');
    const groupMetaLibraries = document.getElementById('group-meta-libraries');
    const groupMetaKeywords = document.getElementById('group-meta-keywords');
    const groupBackBtn = document.getElementById('group-back-btn');
    const headerControls = document.querySelector('.libraries-section-header .header-controls');

    const hasLibraryCards = libraryCards.some(card => cardKind(card) === 'library');
    const hasResourceCards = libraryCards.some(card => cardKind(card) === 'resource');
    if (viewLibrariesBtn) {
        viewLibrariesBtn.style.display = hasLibraryCards ? '' : 'none';
    }
    if (viewResourcesBtn) {
        viewResourcesBtn.style.display = hasResourceCards ? '' : 'none';
    }
    // Default to Resources when the dashboard only has resource entries.
    if (!hasLibraryCards && hasResourceCards) {
        currentView = 'resources';
    }

    const groupStats = {};

    function computeGroupStats() {
        if (!libraryCards || libraryCards.length === 0) return;

        let hasNamedGroups = false;

        libraryCards.forEach(card => {
            const rawGroup = (card.getAttribute('data-group') || '').trim();
            const keywordCount = parseInt(card.getAttribute('data-keyword-count') || '0', 10);

            let key;
            let label;
            if (!rawGroup) {
                key = '__ungrouped__';
                label = 'Ungrouped';
            } else {
                key = rawGroup.toLowerCase();
                // Prefer original casing from data-group-display (preserves API/UI acronyms).
                const displayLabel = (card.getAttribute('data-group-display') || '').trim();
                if (displayLabel) {
                    label = displayLabel;
                } else {
                    label = rawGroup
                        .split(/\\s+/)
                        .filter(Boolean)
                        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                        .join(' ');
                }
                hasNamedGroups = true;
            }

            if (!groupStats[key]) {
                groupStats[key] = {
                    label,
                    libraryCount: 0,
                    resourceCount: 0,
                    keywordCount: 0,
                };
            }

            if (cardKind(card) === 'resource') {
                groupStats[key].resourceCount += 1;
            } else {
                groupStats[key].libraryCount += 1;
            }
            groupStats[key].keywordCount += keywordCount;
        });

        // If no named groups, hide or disable grouped view toggle
        if (!hasNamedGroups && viewToggleEl) {
            viewToggleEl.style.display = 'none';
        }
    }

    function formatKindCount(count, singular, plural) {
        if (!count) return '';
        const label = count === 1 ? singular : plural;
        return `<span><strong>${count}</strong> ${label}</span>`;
    }

    function formatGroupEntryMeta(info, t) {
        const parts = [];
        const libPart = formatKindCount(
            info.libraryCount || 0,
            t.library || 'library',
            t.libraries || 'libraries'
        );
        const resPart = formatKindCount(
            info.resourceCount || 0,
            t.resource || 'resource',
            t.resources || 'resources'
        );
        if (libPart) parts.push(libPart);
        if (resPart) parts.push(resPart);
        // Fallback if kind metadata is missing on older dashboards.
        if (!parts.length) {
            const total = (info.libraryCount || 0) + (info.resourceCount || 0);
            parts.push(formatKindCount(total, t.library || 'library', t.libraries || 'libraries'));
        }
        return parts.join('<span>•</span>');
    }

    function formatGroupEntryText(info, t) {
        const parts = [];
        if (info.libraryCount) {
            const word = info.libraryCount === 1
                ? (t.library || 'library')
                : (t.libraries || 'libraries');
            parts.push(`${info.libraryCount} ${word}`);
        }
        if (info.resourceCount) {
            const word = info.resourceCount === 1
                ? (t.resource || 'resource')
                : (t.resources || 'resources');
            parts.push(`${info.resourceCount} ${word}`);
        }
        if (!parts.length) {
            const total = (info.libraryCount || 0) + (info.resourceCount || 0);
            const word = total === 1
                ? (t.library || 'library')
                : (t.libraries || 'libraries');
            parts.push(`${total} ${word}`);
        }
        return parts.join(' • ');
    }

    function renderGroupCards() {
        if (!groupsGrid) return;

        const keys = Object.keys(groupStats).filter(k => k !== '__ungrouped__');
        const hasNamedGroups = keys.length > 0;

        let html = '';
        const tForGroups = translations[currentLanguage] || translations.en;

        if (hasNamedGroups) {
            keys.sort((a, b) => groupStats[a].label.localeCompare(groupStats[b].label));
            keys.forEach(key => {
                const info = groupStats[key];
                const entryMeta = formatGroupEntryMeta(info, tForGroups);
                const kwWord = info.keywordCount === 1
                    ? (tForGroups.keyword || 'keyword')
                    : (tForGroups.keywords || 'keywords');
                html += `
                    <div class="library-card group-card" data-group-key="${key}" data-group-label="${escapeHtml(String(info.label || '').toLowerCase())}">
                        <h2><span class="group-card-title">${info.label}</span></h2>
                        <div class="library-stats">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                            </svg>
                            <span class="group-card-meta">
                                ${entryMeta}
                                <span>•</span>
                                <span><strong>${info.keywordCount}</strong> ${kwWord}</span>
                            </span>
                        </div>
                    </div>
                `;
            });
        }

        if (groupStats['__ungrouped__']) {
            const info = groupStats['__ungrouped__'];
            const entryMeta = formatGroupEntryMeta(info, tForGroups);
            const kwWord = info.keywordCount === 1
                ? (tForGroups.keyword || 'keyword')
                : (tForGroups.keywords || 'keywords');
            html += `
                <div class="library-card group-card group-card-ungrouped" data-group-key="__ungrouped__" data-group-label="${escapeHtml(String(info.label || '').toLowerCase())}">
                    <h2><span class="group-card-title">${info.label}</span></h2>
                    <div class="library-stats">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                        </svg>
                        <span class="group-card-meta">
                            ${entryMeta}
                            <span>•</span>
                            <span><strong>${info.keywordCount}</strong> ${kwWord}</span>
                        </span>
                    </div>
                </div>
            `;
        }

        groupsGrid.innerHTML = html;

        groupsGrid.querySelectorAll('.group-card').forEach(card => {
            card.addEventListener('click', () => {
                const key = card.getAttribute('data-group-key');
                if (!key) return;
                enterGroupLibrariesView(key);
            });
        });

        if (currentView === 'groups') {
            filterLibraries();
        }
    }

    function updateGroupContext(key) {
        if (!groupContextEl || !groupStats[key]) return;
        const info = groupStats[key];

        groupBreadcrumbName.textContent = info.label;
        const tForGroup = translations[currentLanguage] || translations.en;
        if (groupMetaLibraries) {
            groupMetaLibraries.textContent = formatGroupEntryText(info, tForGroup);
        }
        if (groupMetaKeywords) {
            const keywordText = info.keywordCount === 1
                ? (tForGroup.keyword || 'keyword')
                : (tForGroup.keywords || 'keywords');
            groupMetaKeywords.textContent = `${info.keywordCount} ${keywordText}`;
        }
    }

    function setView(view) {
        currentView = normalizePersistedView(view);

        if (viewLibrariesBtn) {
            viewLibrariesBtn.classList.toggle('view-toggle-btn-active', currentView === 'libraries');
        }
        if (viewResourcesBtn) {
            viewResourcesBtn.classList.toggle('view-toggle-btn-active', currentView === 'resources');
        }
        if (viewGroupsBtn) {
            viewGroupsBtn.classList.toggle(
                'view-toggle-btn-active',
                currentView === 'groups' || currentView === 'group-libraries'
            );
        }

        if (groupsGrid) {
            groupsGrid.style.display = currentView === 'groups' ? 'grid' : 'none';
        }

        if (librariesGrid) {
            librariesGrid.style.display = (
                currentView === 'libraries' ||
                currentView === 'resources' ||
                currentView === 'group-libraries'
            ) ? 'grid' : 'none';
        }

        if (groupContextEl) {
            groupContextEl.style.display = currentView === 'group-libraries' ? 'flex' : 'none';
        }

        // Visually indicate disabled controls when showing group cards
        if (headerControls) {
            headerControls.classList.toggle('controls-disabled', currentView === 'groups');
        }

        // Update search placeholder for the active kind tab
        if (searchInput) {
            const t = translations[currentLanguage] || translations.en;
            const labelEl = document.getElementById('global-search-label');
            if (currentView === 'resources') {
                searchInput.setAttribute('data-i18n-placeholder', 'search_resources');
                searchInput.placeholder = t.search_resources || 'Search resources...';
                if (labelEl) labelEl.textContent = t.search_resources || 'Search resources...';
            } else if (currentView === 'groups') {
                searchInput.setAttribute('data-i18n-placeholder', 'search_groups');
                searchInput.placeholder = t.search_groups || 'Search groups...';
                if (labelEl) labelEl.textContent = t.search_groups || 'Search groups...';
            } else {
                searchInput.setAttribute('data-i18n-placeholder', 'search_libraries');
                searchInput.placeholder = t.search_libraries || 'Search libraries...';
                if (labelEl) labelEl.textContent = t.search_libraries || 'Search libraries...';
            }
        }

        // Persist current dashboard view state
        try {
            const state = {
                view: currentView,
                groupKey: activeGroupKey,
            };
            localStorage.setItem('dashboard_view_state', JSON.stringify(state));
        } catch (e) {
            // Ignore storage errors
        }

        if (currentView === 'libraries' || currentView === 'resources') {
            activeGroupKey = null;
        }

        updateSectionTitle();
        filterLibraries();
    }

    function updateSectionTitle() {
        const titleEl = document.querySelector('.libraries-section-title');
        if (!titleEl) return;
        const t = translations[currentLanguage] || translations.en;
        if (currentView === 'groups') {
            titleEl.removeAttribute('data-i18n');
            titleEl.textContent = t.available_groups || 'Available Groups';
        } else if (currentView === 'resources') {
            titleEl.setAttribute('data-i18n', 'available_resources');
            titleEl.textContent = t.available_resources || 'Available Resources';
        } else if (currentView === 'group-libraries' && activeGroupKey && groupStats[activeGroupKey]) {
            titleEl.removeAttribute('data-i18n');
            titleEl.textContent = groupStats[activeGroupKey].label;
        } else {
            titleEl.setAttribute('data-i18n', 'available_libraries');
            titleEl.textContent = t.available_libraries || 'Available Libraries';
        }
    }

    function enterGroupsView() {
        if (!Object.keys(groupStats).length) return;
        activeGroupKey = null;
        if (noResults) {
            noResults.classList.remove('active');
        }
        setView('groups');
    }

    function enterGroupLibrariesView(key) {
        activeGroupKey = key;
        updateGroupContext(key);
        setView('group-libraries');
    }

    function backToGroups() {
        activeGroupKey = null;
        setView('groups');
    }

    // Initialize grouping
    computeGroupStats();
    if (Object.keys(groupStats).length > 0) {
        renderGroupCards();
    } else if (viewGroupsBtn) {
        viewGroupsBtn.style.display = 'none';
    }

    if (viewLibrariesBtn) {
        viewLibrariesBtn.addEventListener('click', () => setView('libraries'));
    }
    if (viewResourcesBtn) {
        viewResourcesBtn.addEventListener('click', () => setView('resources'));
    }
    if (viewGroupsBtn) {
        viewGroupsBtn.addEventListener('click', () => enterGroupsView());
    }

    if (groupBreadcrumbRoot) {
        groupBreadcrumbRoot.addEventListener('click', () => backToGroups());
    }
    if (groupBackBtn) {
        groupBackBtn.addEventListener('click', () => backToGroups());
    }
    
    // Export functionality
    function exportToCSV() {
        const visibleCards = libraryCards.filter(card => card.style.display !== 'none');
        if (visibleCards.length === 0) {
            alert('No libraries to export');
            return;
        }
        
        const csvRows = ['Name,Type,Keywords,Author,Maintainer,License,RF Version,Python,Description'];
        
        visibleCards.forEach(card => {
            const name = card.querySelector('h2 a')?.textContent || '';
            const type = cardKind(card) === 'resource' ? 'Resource' : 'Library';
            const keywords = card.getAttribute('data-keyword-count') || '0';
            const author = card.getAttribute('data-author') || '';
            const maintainer = card.getAttribute('data-maintainer') || '';
            const license = card.getAttribute('data-license') || '';
            const rfVersion = card.getAttribute('data-robot-framework') || '';
            const python = card.getAttribute('data-python') || '';
            // Get description from data attribute first, fallback to element text
            const description = card.getAttribute('data-description-text') || card.querySelector('.library-description')?.textContent?.trim() || '';
            
            // Escape CSV values
            const escapeCSV = (val) => {
                if (!val) return '';
                const str = String(val);
                if (str.includes(',') || str.includes('"') || str.includes('\\n')) {
                    return '"' + str.replace(/"/g, '""') + '"';
                }
                return str;
            };
            
            csvRows.push([
                escapeCSV(name),
                escapeCSV(type),
                escapeCSV(keywords),
                escapeCSV(author),
                escapeCSV(maintainer),
                escapeCSV(license),
                escapeCSV(rfVersion),
                escapeCSV(python),
                escapeCSV(description)
            ].join(','));
        });
        
        const csvContent = csvRows.join('\\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', 'libraries-export.csv');
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    function exportToExcel() {
        const visibleCards = libraryCards.filter(card => card.style.display !== 'none');
        if (visibleCards.length === 0) {
            alert('No libraries to export');
            return;
        }
        
        // Generate Excel-compatible CSV with UTF-8 BOM for proper Excel opening
        const csvRows = ['Name,Type,Keywords,Author,Maintainer,License,RF Version,Python,Description'];
        
        visibleCards.forEach(card => {
            const name = card.querySelector('h2 a')?.textContent || '';
            const type = cardKind(card) === 'resource' ? 'Resource' : 'Library';
            const keywords = card.getAttribute('data-keyword-count') || '0';
            const author = card.getAttribute('data-author') || '';
            const maintainer = card.getAttribute('data-maintainer') || '';
            const license = card.getAttribute('data-license') || '';
            const rfVersion = card.getAttribute('data-robot-framework') || '';
            const python = card.getAttribute('data-python') || '';
            // Get description from data attribute first, fallback to element text
            const description = card.getAttribute('data-description-text') || card.querySelector('.library-description')?.textContent?.trim() || '';
            
            const escapeCSV = (val) => {
                if (!val) return '';
                const str = String(val);
                if (str.includes(',') || str.includes('"') || str.includes('\\n')) {
                    return '"' + str.replace(/"/g, '""') + '"';
                }
                return str;
            };
            
            csvRows.push([
                escapeCSV(name),
                escapeCSV(type),
                escapeCSV(keywords),
                escapeCSV(author),
                escapeCSV(maintainer),
                escapeCSV(license),
                escapeCSV(rfVersion),
                escapeCSV(python),
                escapeCSV(description)
            ].join(','));
        });
        
        // Add UTF-8 BOM for Excel compatibility
        const csvContent = '\\ufeff' + csvRows.join('\\n');
        const blob = new Blob([csvContent], { type: 'application/vnd.ms-excel;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', 'libraries-export.xlsx');
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    function exportToPDF() {
        const visibleCards = libraryCards.filter(card => card.style.display !== 'none');
        if (visibleCards.length === 0) {
            alert('No libraries to export');
            return;
        }
        
        // Create a print-friendly version
        const printWindow = window.open('', '_blank');
        if (!printWindow) {
            alert('Please allow popups to export as PDF');
            return;
        }
        
        const siteName = document.querySelector('.dashboard-header h2')?.textContent || 'Documentation Dashboard';
        const exportDate = new Date().toLocaleString();
        
        let htmlContent = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>Libraries Export - ${siteName}</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        padding: 20px;
                        color: #333;
                    }
                    h1 {
                        color: #38bdf8;
                        border-bottom: 2px solid #38bdf8;
                        padding-bottom: 10px;
                    }
                    table {
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 20px;
                    }
                    th, td {
                        border: 1px solid #ddd;
                        padding: 12px;
                        text-align: left;
                    }
                    th {
                        background-color: #38bdf8;
                        color: white;
                        font-weight: bold;
                    }
                    tr:nth-child(even) {
                        background-color: #f9f9f9;
                    }
                    .meta {
                        color: #666;
                        font-size: 0.9em;
                        margin-bottom: 20px;
                    }
                </style>
            </head>
            <body>
                <h1>${siteName}</h1>
                <div class="meta">Exported: ${exportDate} | Total Entries: ${visibleCards.length}</div>
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Type</th>
                            <th>Keywords</th>
                            <th>Author</th>
                            <th>Maintainer</th>
                            <th>License</th>
                            <th>RF Version</th>
                            <th>Python</th>
                            <th>Description</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        visibleCards.forEach(card => {
            const name = card.querySelector('h2 a')?.textContent || '';
            const type = cardKind(card) === 'resource' ? 'Resource' : 'Library';
            const keywords = card.getAttribute('data-keyword-count') || '0';
            const author = card.getAttribute('data-author') || '';
            const maintainer = card.getAttribute('data-maintainer') || '';
            const license = card.getAttribute('data-license') || '';
            const rfVersion = card.getAttribute('data-robot-framework') || '';
            const python = card.getAttribute('data-python') || '';
            // Get description from data attribute first, fallback to element text
            const description = card.getAttribute('data-description-text') || card.querySelector('.library-description')?.textContent?.trim() || '';
            
            const escapeHtml = (text) => {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            };
            
            htmlContent += `
                <tr>
                    <td>${escapeHtml(name)}</td>
                    <td>${escapeHtml(type)}</td>
                    <td>${escapeHtml(keywords)}</td>
                    <td>${escapeHtml(author)}</td>
                    <td>${escapeHtml(maintainer)}</td>
                    <td>${escapeHtml(license)}</td>
                    <td>${escapeHtml(rfVersion)}</td>
                    <td>${escapeHtml(python)}</td>
                    <td>${escapeHtml(description)}</td>
                </tr>
            `;
        });
        
        htmlContent += `
                    </tbody>
                </table>
            </body>
            </html>
        `;
        
        printWindow.document.write(htmlContent);
        printWindow.document.close();
        
        // Wait for content to load, then trigger print
        setTimeout(() => {
            printWindow.print();
        }, 250);
    }
    
    // Export format dropdown
    const exportFormatSelect = document.getElementById('export-format');
    if (exportFormatSelect) {
        exportFormatSelect.addEventListener('change', function() {
            if (currentView === 'groups') {
                exportFormatSelect.value = '';
                return;
            }
            const format = exportFormatSelect.value;
            if (format === 'csv') {
                exportToCSV();
            } else if (format === 'excel') {
                exportToExcel();
            } else if (format === 'pdf') {
                exportToPDF();
            }
            // Reset so the same format can be chosen again
            exportFormatSelect.selectedIndex = 0;
        });
    }
    
    if (searchInput) {
        // Restore last search query from localStorage
        const savedSearch = localStorage.getItem('dashboard_search');
        if (savedSearch) {
            searchInput.value = savedSearch;
            // Trigger search to show results
            const event = new Event('input', { bubbles: true });
            searchInput.dispatchEvent(event);
        }
        
        searchInput.addEventListener('input', function(e) {
            const query = e.target.value.trim().toLowerCase();
            
            // Save search query to localStorage
            if (query.length > 0) {
                localStorage.setItem('dashboard_search', query);
            } else {
                localStorage.removeItem('dashboard_search');
            }
            
            // Re-get cards after sorting (in case DOM changed)
            libraryCards = librariesGrid ? Array.from(librariesGrid.querySelectorAll('.library-card')) : [];
            
            // Apply filters (which includes search)
            filterLibraries();
        });
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Initialize keyword search in header
    const keywordSearchInput = document.getElementById('keyword-search');
    const keywordSearchResults = document.getElementById('keyword-search-results');
    
    // Track keyboard navigation state
    let selectedResultIndex = -1;
    let currentResults = [];
    
    if (keywordSearchInput) {
        let searchTimeout;
        
        // Restore last keyword search from localStorage
        const savedKeywordSearch = localStorage.getItem('dashboard_keyword_search');
        if (savedKeywordSearch) {
            keywordSearchInput.value = savedKeywordSearch;
            // Trigger search to show results
            const event = new Event('input', { bubbles: true });
            keywordSearchInput.dispatchEvent(event);
        }
        
        keywordSearchInput.addEventListener('input', function(e) {
            const query = e.target.value.trim().toLowerCase();
            
            // Save keyword search to localStorage
            if (query.length > 0) {
                localStorage.setItem('dashboard_keyword_search', query);
            } else {
                localStorage.removeItem('dashboard_keyword_search');
            }
            
            clearTimeout(searchTimeout);
            
            if (query.length === 0) {
                keywordSearchResults.classList.remove('active');
                keywordSearchResults.innerHTML = '';
                selectedResultIndex = -1;
                currentResults = [];
                return;
            }
            
            // Debounce search
            searchTimeout = setTimeout(() => {
                // Load and search index for keywords only
                fetch('assets/search-index.json')
                    .then(response => response.json())
                    .then(index => {
                        // Only search keywords
                        const results = index.filter(item => {
                            if (item.type === 'keyword') {
                                return item.keyword.toLowerCase().includes(query);
                            }
                            return false;
                        }).slice(0, 10); // Limit to 10 results for dropdown
                        
                        currentResults = results;
                        selectedResultIndex = -1; // Reset selection
                        displayKeywordResults(results);
                    })
                    .catch(error => {
                        console.error('Error loading search index:', error);
                        keywordSearchResults.classList.add('active');
                        keywordSearchResults.innerHTML = '<div style="padding: 1.5rem 1rem; color: #ef4444; text-align: center; font-size: 0.9rem;">Error loading search index</div>';
                        currentResults = [];
                        selectedResultIndex = -1;
                    });
            }, 200);
        });
        
        // Keyboard navigation for search input
        keywordSearchInput.addEventListener('keydown', function(e) {
            if (!keywordSearchResults.classList.contains('active') || currentResults.length === 0) {
                return;
            }
            
            const resultItems = keywordSearchResults.querySelectorAll('.search-result-item');
            
            // Arrow down - move to next result
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectedResultIndex = (selectedResultIndex + 1) % resultItems.length;
                updateHighlight(resultItems);
                scrollToHighlighted(resultItems[selectedResultIndex]);
            }
            
            // Arrow up - move to previous result
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (selectedResultIndex <= 0) {
                    selectedResultIndex = resultItems.length - 1;
                } else {
                    selectedResultIndex--;
                }
                updateHighlight(resultItems);
                scrollToHighlighted(resultItems[selectedResultIndex]);
            }
            
            // Enter - open selected result
            if (e.key === 'Enter' && selectedResultIndex >= 0) {
                e.preventDefault();
                const selectedItem = resultItems[selectedResultIndex];
                const link = selectedItem.querySelector('a');
                if (link) {
                    window.location.href = link.href;
                }
            }
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!keywordSearchInput.contains(e.target) && !keywordSearchResults.contains(e.target)) {
                keywordSearchResults.classList.remove('active');
                selectedResultIndex = -1;
            }
        });
        
        // Global keyboard shortcuts
        document.addEventListener('keydown', function(e) {
            // Press '/' to focus keyword search (only if not already typing in an input)
            if (e.key === '/' && !e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey) {
                const activeElement = document.activeElement;
                const isInputFocused = activeElement && (
                    activeElement.tagName === 'INPUT' || 
                    activeElement.tagName === 'TEXTAREA' || 
                    activeElement.isContentEditable
                );
                
                // Only focus if not already typing in an input
                if (!isInputFocused) {
                    e.preventDefault();
                    keywordSearchInput.focus();
                    keywordSearchInput.select();
                }
            }
            
            // Press 'Escape' to close dropdown and blur search
            if (e.key === 'Escape') {
                // Close dropdown if open
                if (keywordSearchResults.classList.contains('active')) {
                    keywordSearchResults.classList.remove('active');
                    keywordSearchResults.innerHTML = '';
                    selectedResultIndex = -1;
                    currentResults = [];
                }
                // Always blur search input if it's focused
                if (document.activeElement === keywordSearchInput) {
                    keywordSearchInput.blur();
                }
            }
        });
        
        function updateHighlight(resultItems) {
            resultItems.forEach((item, index) => {
                if (index === selectedResultIndex) {
                    item.classList.add('highlighted');
                } else {
                    item.classList.remove('highlighted');
                }
            });
        }
        
        function scrollToHighlighted(element) {
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
    }
    
    function displayKeywordResults(results) {
        if (results.length === 0) {
            keywordSearchResults.classList.add('active');
            keywordSearchResults.innerHTML = '<div style="padding: 1.5rem 1rem; color: var(--muted); text-align: center; font-size: 0.9rem; font-style: italic;">No keywords found</div>';
            selectedResultIndex = -1;
            return;
        }
        
        keywordSearchResults.classList.add('active');
        keywordSearchResults.innerHTML = results.map(item => `
            <div class="search-result-item">
                <a href="${item.url}" class="result-title">${escapeHtml(item.keyword)}</a>
                <div class="library-name">${escapeHtml(item.library)}</div>
            </div>
        `).join('');
        
        // Reset selection when new results are displayed
        selectedResultIndex = -1;
    }

    // ===== Persist and restore dashboard view state across navigation =====

    // When user clicks a library card link, remember current dashboard view/group
    const libraryLinks = document.querySelectorAll('.library-card h2 a');
    libraryLinks.forEach(link => {
        link.addEventListener('click', () => {
            try {
                const state = {
                    view: currentView,
                    groupKey: activeGroupKey,
                };
                localStorage.setItem('dashboard_last_state', JSON.stringify(state));
            } catch (e) {
                // Ignore storage errors
            }
        });
    });

    // On load, first restore persistent dashboard view (for direct visits / new tabs)
    try {
        const persistedRaw = localStorage.getItem('dashboard_view_state');
        if (persistedRaw) {
            const persisted = JSON.parse(persistedRaw);
            const persistedView = normalizePersistedView(persisted && persisted.view);
            if (persistedView === 'groups' && Object.keys(groupStats).length > 0) {
                enterGroupsView();
            } else if (
                persistedView === 'group-libraries' &&
                persisted.groupKey &&
                groupStats[persisted.groupKey]
            ) {
                enterGroupLibrariesView(persisted.groupKey);
            } else if (persistedView === 'resources' && hasResourceCards) {
                setView('resources');
            } else if (persistedView === 'libraries' && hasLibraryCards) {
                setView('libraries');
            }
        }
    } catch (e) {
        // Fail silently if localStorage is unavailable or JSON is invalid
    }

    // Then, if navigating back from a library page, override with last dashboard state (one-time)
    try {
        const lastStateRaw = localStorage.getItem('dashboard_last_state');
        if (lastStateRaw) {
            const lastState = JSON.parse(lastStateRaw);
            localStorage.removeItem('dashboard_last_state');
            const lastView = normalizePersistedView(lastState && lastState.view);

            if (lastView === 'groups' && Object.keys(groupStats).length > 0) {
                enterGroupsView();
            } else if (
                lastView === 'group-libraries' &&
                lastState.groupKey &&
                groupStats[lastState.groupKey]
            ) {
                enterGroupLibrariesView(lastState.groupKey);
            } else if (lastView === 'resources' && hasResourceCards) {
                setView('resources');
            } else if (lastView === 'libraries' && hasLibraryCards) {
                setView('libraries');
            }
        }
    } catch (e) {
        // Fail silently if localStorage is unavailable or JSON is invalid
    }

    // Apply the active view so Libraries/Resources filtering takes effect on first paint.
    if (currentView === 'libraries' || currentView === 'resources') {
        setView(currentView);
    }
});
"""


def _generate_search_js() -> str:
    """Generate search-specific JavaScript (separate file for modularity)."""
    # TODO: Separate search-specific JavaScript into external asset file and load it here
    return """// Search functionality
// This file is loaded by dashboard pages for search functionality
"""


def _build_filter_html(label: str, filter_id: str, options: List[str]) -> str:
    """Build HTML for a filter dropdown."""
    if not options:
        return ''
    
    options_html = ''.join([f'<option value="{opt.lower()}">{opt}</option>' for opt in options])
    all_label = f"All {label}s" if label not in ["RF Version", "Python", "Group"] else (
        "All Versions" if label in ["RF Version"] else (
            "All Python versions" if label == "Python" else "All Groups"
        )
    )
    
    # Map label to i18n key
    i18n_key_map = {
        "Author": "author",
        "Maintainer": "maintainer",
        "License": "license",
        "RF Version": "rf_version",
        "Python": "python"
    }
    i18n_key = i18n_key_map.get(label, label.lower().replace(" ", "_"))
    all_i18n_key = "all_versions" if label in ["RF Version", "Python"] else f"all_{i18n_key}s"
    
    return f'''<div class="filter-group">
        <label class="filter-label" data-i18n="{i18n_key}">{label}</label>
        <select id="{filter_id}" class="filter-select">
            <option value="" data-i18n="{all_i18n_key}">{all_label}</option>
            {options_html}
        </select>
    </div>'''


def _normalize_entry_kind(entry: Dict[str, Any]) -> str:
    """Return ``library`` or ``resource`` for a dashboard metadata entry."""
    kind = (entry.get("kind") or "").strip().lower()
    if kind in {"library", "resource"}:
        return kind
    source_type = (entry.get("source_type") or "").strip().upper()
    if source_type in {"RESOURCE", "SUITE"}:
        return "resource"
    return "library"


@lru_cache(maxsize=1)
def _load_dashboard_template() -> str:
    """Load the dashboard HTML template from package resources."""
    try:
        # Python 3.9+ - use importlib.resources
        template_path = importlib.resources.files("robotframework_docgen") / "templates" / "dashboard.html"
        return template_path.read_text(encoding="utf-8")
    except (AttributeError, ModuleNotFoundError):
        # Python 3.8 fallback - try importlib_resources backport
        try:
            import importlib_resources  # type: ignore[import-untyped]
            template_path = importlib_resources.files("robotframework_docgen") / "templates" / "dashboard.html"
            return template_path.read_text(encoding="utf-8")
        except (ImportError, ModuleNotFoundError):
            template_path = Path(__file__).resolve().parent / "templates" / "dashboard.html"
            return template_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        # Fallback to local path
        template_path = Path(__file__).resolve().parent / "templates" / "dashboard.html"
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
        raise FileNotFoundError(
            f"Dashboard HTML template not found. Tried: {template_path}"
        )


def _generate_dashboard_html(
    libraries_metadata: List[Dict[str, Any]],
    site_config: Dict[str, Any]
) -> str:
    """Generate dashboard homepage HTML matching library design."""
    site_name = site_config.get("name", "Robot Framework Libraries")
    site_description = site_config.get("description", "Documentation for Robot Framework libraries")
    
    # Calculate statistics
    total_keywords = sum(lib.get("keyword_count", 0) for lib in libraries_metadata)
    library_count = sum(1 for lib in libraries_metadata if _normalize_entry_kind(lib) == "library")
    resource_count = sum(1 for lib in libraries_metadata if _normalize_entry_kind(lib) == "resource")
    # Count distinct named groups (ignore empty/None)
    distinct_groups = {
        (lib.get("group") or "").strip()
        for lib in libraries_metadata
        if (lib.get("group") or "").strip()
    }
    group_count = len(distinct_groups)
    
    # Collect unique values for filters
    unique_authors = set()
    unique_maintainers = set()
    unique_licenses = set()
    unique_robot_frameworks = set()
    unique_pythons = set()
    unique_groups = set()
    
    for lib in libraries_metadata:
        if lib.get("author"):
            unique_authors.add(lib.get("author"))
        if lib.get("maintainer"):
            unique_maintainers.add(lib.get("maintainer"))
        if lib.get("license"):
            unique_licenses.add(lib.get("license"))
        if lib.get("robot_framework"):
            unique_robot_frameworks.add(lib.get("robot_framework"))
        if lib.get("python"):
            unique_pythons.add(lib.get("python"))
        group_name = (lib.get("group") or "").strip()
        if group_name:
            unique_groups.add(group_name)
    
    # Sort filter options
    sorted_authors = sorted(unique_authors)
    sorted_maintainers = sorted(unique_maintainers)
    sorted_licenses = sorted(unique_licenses)
    sorted_robot_frameworks = sorted(unique_robot_frameworks)
    sorted_pythons = sorted(unique_pythons)
    sorted_groups = sorted(unique_groups)
    
    libraries_html = []
    for lib in libraries_metadata:
        lib_name = lib.get("name", "Unknown")
        lib_url = lib.get("url", "")
        lib_version = lib.get("version", "") or ""
        if lib_version.lower() == "unknown":
            lib_version = ""
        lib_description = lib.get("description", "")
        lib_keyword_count = lib.get("keyword_count", 0)
        lib_author = lib.get("author", "")
        lib_maintainer = lib.get("maintainer", "")
        lib_license = lib.get("license", "")
        lib_robot_framework = lib.get("robot_framework", "")
        lib_python = lib.get("python", "")
        lib_group = lib.get("group") or ""
        lib_kind = _normalize_entry_kind(lib)
        
        version_badge = f'<span class="badge"><span data-i18n="version">Version</span>: {lib_version}</span>' if lib_version else ''
        description_html = f'<div class="library-description">{lib_description}</div>' if lib_description else ''
        group_badge = f'<span class="badge badge-group">{lib_group}</span>' if lib_group else ''
        kind_label = "Resource" if lib_kind == "resource" else "Library"
        kind_badge = f'<span class="badge badge-kind">{kind_label}</span>'
        
        # Build metadata list
        meta_items = []
        if lib_author:
            meta_items.append(f'''
                <div class="library-meta-item">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                        <circle cx="12" cy="7" r="4"></circle>
                    </svg>
                    <span class="meta-label" data-i18n="author">Author:</span>
                    <span class="meta-value">{lib_author}</span>
                </div>
            ''')
        if lib_maintainer:
            meta_items.append(f'''
                <div class="library-meta-item">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path>
                        <circle cx="9" cy="7" r="4"></circle>
                        <path d="M22 21v-2a4 4 0 0 0-3-3.87"></path>
                        <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                    </svg>
                    <span class="meta-label" data-i18n="maintainer">Maintainer:</span>
                    <span class="meta-value">{lib_maintainer}</span>
                </div>
            ''')
        if lib_license:
            meta_items.append(f'''
                <div class="library-meta-item">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                        <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                    </svg>
                    <span class="meta-label" data-i18n="license">License:</span>
                    <span class="meta-value">{lib_license}</span>
                </div>
            ''')
        if lib_robot_framework:
            meta_items.append(f'''
                <div class="library-meta-item">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
                        <path d="M2 17l10 5 10-5"></path>
                        <path d="M2 12l10 5 10-5"></path>
                    </svg>
                    <span class="meta-label" data-i18n="rf_version">RF Version:</span>
                    <span class="meta-value">{lib_robot_framework}</span>
                </div>
            ''')
        if lib_python:
            meta_items.append(f'''
                <div class="library-meta-item">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path>
                    </svg>
                    <span class="meta-label" data-i18n="python">Python:</span>
                    <span class="meta-value">{lib_python}</span>
                </div>
            ''')
        
        if meta_items:
            meta_html = f'''
                <div class="library-meta-header collapsed" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.classList.toggle('collapsed');">
                    <span class="meta-toggle">
                        <svg class="meta-toggle-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="6 9 12 15 18 9"></polyline>
                        </svg>
                        <span data-i18n="metadata">Metadata</span>
                    </span>
                </div>
                <div class="library-meta-list collapsed">{"".join(meta_items)}</div>
            '''
        else:
            meta_html = ''
        
        libraries_html.append(f"""
            <div class="library-card" 
                 data-library-name="{lib_name.lower()}" 
                 data-library-description="{lib_description.lower() if lib_description else ''}" 
                 data-description-text="{lib_description if lib_description else ''}"
                 data-keyword-count="{lib_keyword_count}"
                 data-version="{lib_version}"
                 data-kind="{lib_kind}"
                 data-author="{lib_author.lower() if lib_author else ''}"
                 data-maintainer="{lib_maintainer.lower() if lib_maintainer else ''}"
                 data-license="{lib_license.lower() if lib_license else ''}"
                 data-robot-framework="{lib_robot_framework.lower() if lib_robot_framework else ''}"
                 data-python="{lib_python.lower() if lib_python else ''}"
                 data-group="{lib_group.lower() if lib_group else ''}"
                 data-group-display="{lib_group}">
                <h2>
                    <a href="{lib_url}">{lib_name}</a>
                </h2>
                <div class="library-badges">
                    {kind_badge}
                    {version_badge}
                    {group_badge}
                </div>
                {description_html}
                <div class="library-stats">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                    </svg>
                    <span data-i18n-keyword-count="{lib_keyword_count}">{lib_keyword_count} keyword{'' if lib_keyword_count == 1 else 's'}</span>
                </div>
                {meta_html}
            </div>
        """)
    
    # Build groups/library/resource stat cards
    library_stat_html = ''
    if library_count > 0:
        library_stat_html = f'''
            <div class="stat-card">
                <div class="stat-value">{library_count}</div>
                <div class="stat-label" data-i18n="libraries">Libraries</div>
            </div>
        '''
    resource_stat_html = ''
    if resource_count > 0:
        resource_stat_html = f'''
            <div class="stat-card">
                <div class="stat-value">{resource_count}</div>
                <div class="stat-label" data-i18n="resources">Resources</div>
            </div>
        '''
    if group_count > 0:
        group_stat_html = f'''
            <div class="stat-card">
                <div class="stat-value">{group_count}</div>
                <div class="stat-label" data-i18n="groups">Groups</div>
            </div>
        '''
    else:
        group_stat_html = ''
    
    # Load template
    template = _load_dashboard_template()
    logo_url = logo_url_for_theme(resolve_theme_tokens(site_config or {}))

    # Format template with variables
    return template.format(
        site_name=site_name,
        site_description=site_description,
        logo_url=logo_url,
        library_stat_html=library_stat_html,
        resource_stat_html=resource_stat_html,
        total_keywords=total_keywords,
        group_stat_html=group_stat_html,
        libraries_html=''.join(libraries_html),
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        filter_data_authors=json.dumps(sorted_authors),
        filter_data_maintainers=json.dumps(sorted_maintainers),
        filter_data_licenses=json.dumps(sorted_licenses),
        filter_data_robot_frameworks=json.dumps(sorted_robot_frameworks),
        filter_data_pythons=json.dumps(sorted_pythons),
        filter_data_groups=json.dumps(sorted_groups),
    )


def add_dashboard_navigation(html_content: str, dashboard_url: str = "../index.html") -> str:
    """
    Add navigation link to dashboard in library HTML pages.
    
    Args:
        html_content: Original HTML content of library page
        dashboard_url: Relative URL to dashboard (default: ../index.html)
    
    Returns:
        Modified HTML with dashboard navigation
    """
    import re
    
    # Create the dashboard link
    nav_link = f'<a class="nav-back" href="{dashboard_url}">← Back to Dashboard</a>'
    
    # Check if header exists and has a nav element
    if '<header' in html_content:
        # Look for existing <nav> inside header - match the nav tag and its content
        # Pattern: <nav>...content...</nav> inside header
        nav_pattern = r'(<nav[^>]*>)(.*?)(</nav>)'
        
        def insert_dashboard_link(match):
            nav_open = match.group(1)
            nav_content = match.group(2)
            nav_close = match.group(3)
            # Add dashboard link at the beginning of nav content
            return nav_open + nav_link + nav_content + nav_close
        
        # Replace the first nav found (should be in header)
        html_content = re.sub(nav_pattern, insert_dashboard_link, html_content, count=1, flags=re.DOTALL)
    else:
        # No header found, add navigation bar before body content
        nav_html = f'''<div class="dashboard-nav-container" style="background: color-mix(in srgb, var(--bg) 95%, transparent); padding: 0.75rem 2rem; border-bottom: 1px solid var(--border);">
    <a href="{dashboard_url}" style="color: var(--accent); text-decoration: none; font-weight: 500;">← Back to Dashboard</a>
</div>'''
        # Insert after <body> tag
        if '<body>' in html_content:
            html_content = html_content.replace('<body>', f'<body>{nav_html}', 1)
        elif '<body ' in html_content:
            html_content = re.sub(
                r'(<body[^>]*>)',
                rf'\1{nav_html}',
                html_content,
                count=1
            )
    
    return html_content

