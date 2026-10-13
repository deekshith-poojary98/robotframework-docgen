"""
Tests for dashboard grouping-related backend behavior.
"""

from robotframework_docgen.dashboard import (
    _generate_dashboard_html,
    _generate_dashboard_js,
    _generate_search_index,
    _normalize_entry_kind,
)
from robotframework_docgen.generator import DocumentationGenerator


def _minimal_site_config():
    return {
        "name": "Robot Framework Libraries",
        "description": "Test dashboard",
    }


def test_normalize_entry_kind():
    assert _normalize_entry_kind({"kind": "resource"}) == "resource"
    assert _normalize_entry_kind({"kind": "library"}) == "library"
    assert _normalize_entry_kind({"source_type": "RESOURCE"}) == "resource"
    assert _normalize_entry_kind({"source_type": "SUITE"}) == "resource"
    assert _normalize_entry_kind({}) == "library"


def test_dashboard_omits_unknown_version_badge():
    """Version Unknown must not appear on library cards."""
    libraries_metadata = [
        {
            "name": "Lib1",
            "url": "Lib1/index.html",
            "keyword_count": 5,
            "version": "Unknown",
            "group": "API Keywords",
            "kind": "library",
        },
        {
            "name": "Lib2",
            "url": "Lib2/index.html",
            "keyword_count": 3,
            "version": "",
            "group": "UI Helpers",
            "kind": "resource",
        },
        {
            "name": "Lib3",
            "url": "Lib3/index.html",
            "keyword_count": 2,
            "version": "1.2.3",
            "group": "API Keywords",
            "kind": "library",
        },
    ]

    html = _generate_dashboard_html(libraries_metadata, _minimal_site_config())

    assert "Version: Unknown" not in html
    assert "Version Unknown" not in html
    assert "Version</span>: 1.2.3" in html
    assert 'data-version="1.2.3"' in html
    assert 'data-version=""' in html
    assert 'data-group-display="API Keywords"' in html
    assert 'data-group-display="UI Helpers"' in html
    assert 'data-kind="library"' in html
    assert 'data-kind="resource"' in html
    assert 'id="view-libraries-btn"' in html
    assert 'id="view-resources-btn"' in html
    assert 'id="view-groups-btn"' in html

    js = _generate_dashboard_js()
    assert "available_groups: 'Available Groups'" in js
    assert "available_resources: 'Available Resources'" in js
    assert "search_groups: 'Search groups...'" in js
    assert "no_groups_found: 'No groups found.'" in js
    assert "function filterGroups()" in js
    assert "function matchesSubstring(" in js
    assert "data-group-label" in js
    assert "matchesSubstring(libraryName, searchQuery)" in js
    assert "libraryDescription" not in js.split("function filterLibraries()")[1].split("function ")[0]
    assert "function updateSectionTitle()" in js
    assert "data-group-display" in js
    assert "view-resources-btn" in js
    assert "currentView === 'resources'" in js
    assert "resourceCount" in js
    assert "formatGroupEntryMeta" in js
    assert "currentView === 'groups'" in js
    assert "search_groups" in js
    assert "Name,Type,Keywords" in js
    assert "<th>Type</th>" in js
    assert "cardKind(card) === 'resource' ? 'Resource' : 'Library'" in js
    assert "Library Name,Version,Keywords" not in js
    assert "<th>Version</th>" not in js


def test_dashboard_splits_library_and_resource_stats():
    libraries_metadata = [
        {"name": "PyLib", "url": "PyLib/index.html", "keyword_count": 5, "kind": "library"},
        {"name": "Helpers", "url": "Helpers/index.html", "keyword_count": 3, "kind": "resource"},
        {"name": "Pages", "url": "Pages/index.html", "keyword_count": 2, "kind": "resource"},
    ]

    html = _generate_dashboard_html(libraries_metadata, _minimal_site_config())

    assert '<div class="stat-value">1</div>' in html
    assert 'data-i18n="libraries">Libraries</div>' in html
    assert '<div class="stat-value">2</div>' in html
    assert 'data-i18n="resources">Resources</div>' in html
    assert 'badge-kind">Library</span>' in html
    assert 'badge-kind">Resource</span>' in html


def test_dashboard_includes_group_stat_card_when_groups_present():
    """Dashboard should show a Groups stat card when at least one group exists."""
    libraries_metadata = [
        {"name": "Lib1", "url": "Lib1/index.html", "keyword_count": 5, "group": "Core"},
        {"name": "Lib2", "url": "Lib2/index.html", "keyword_count": 3, "group": "Core"},
        {"name": "Lib3", "url": "Lib3/index.html", "keyword_count": 7, "group": "API"},
        {"name": "Lib4", "url": "Lib4/index.html", "keyword_count": 2},  # ungrouped
    ]

    html = _generate_dashboard_html(libraries_metadata, _minimal_site_config())

    # Two distinct named groups: "Core" and "API"
    assert "Groups" in html
    assert '<div class="stat-value">2</div>' in html


def test_search_index_anchor_matches_keyword_page():
    """Dashboard search must link to the same id the keyword page renders."""
    keyword_name = "Fill ${e_type} email"
    index = _generate_search_index(
        [
            {
                "name": "MailLib",
                "url": "MailLib/index.html",
                "keywords": [{"name": keyword_name, "doc": ""}],
            }
        ]
    )
    keyword_entry = next(item for item in index if item["type"] == "keyword")
    anchor = DocumentationGenerator.keyword_anchor_id(keyword_name)
    assert keyword_entry["url"] == f"MailLib/index.html#{anchor}"
    assert "${" not in keyword_entry["url"]


def test_dashboard_omits_group_stat_card_when_no_groups_present():
    """Dashboard should not show a Groups stat card when no groups are defined."""
    libraries_metadata = [
        {"name": "Lib1", "url": "Lib1/index.html", "keyword_count": 5},
        {"name": "Lib2", "url": "Lib2/index.html", "keyword_count": 3},
    ]

    html = _generate_dashboard_html(libraries_metadata, _minimal_site_config())

    # The word "Groups" may appear in other UI (e.g. view toggle),
    # so specifically check that no Groups stat card label is rendered.
    assert '<div class="stat-label">Groups</div>' not in html
    assert '<div class="stat-label" data-i18n="groups">Groups</div>' not in html
