"""
Tests for dashboard grouping-related backend behavior.
"""

from robotframework_docgen.dashboard import _generate_dashboard_html


def _minimal_site_config():
    return {
        "name": "Robot Framework Libraries",
        "description": "Test dashboard",
    }


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

