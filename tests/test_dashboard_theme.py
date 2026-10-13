"""Dashboard theme token injection."""

from pathlib import Path

from robotframework_docgen.dashboard import (
    _generate_dashboard_css,
    _generate_dashboard_html,
    generate_dashboard,
)
from robotframework_docgen.theme import RF_LOGO_ON_DARK_BG, RF_LOGO_ON_LIGHT_BG


def test_dashboard_css_default_has_no_theme_override_block():
    css = _generate_dashboard_css()
    assert "--bg: #0f172a;" in css
    assert "--accent: #38bdf8;" in css
    assert "--accent-soft: rgba(56, 189, 248, 0.15);" in css
    assert "--accent-soft: var(--accent-soft);" not in css
    assert "color-mix(in srgb, var(--card) 92%, transparent)" in css
    assert "Theme overrides from site.theme" not in css


def test_dashboard_css_applies_theme_object():
    css = _generate_dashboard_css(
        {
            "theme": {
                "bg": "#f0fdf4",
                "accent": "#16a34a",
                "hero_badge_bg": "#e8fcef",
                "hero_badge_text": "#14532d",
                "hero_badge_kind_bg": "rgba(22, 163, 74, 0.12)",
                "hero_badge_kind_text": "#16a34a",
            }
        }
    )
    assert "Theme overrides from site.theme" in css
    assert "--bg: #f0fdf4;" in css
    assert "--accent: #16a34a;" in css
    assert "--hero-badge-bg: #e8fcef;" in css
    assert "--hero-badge-kind-text: #16a34a;" in css
    assert "background: var(--hero-badge-bg);" in css
    assert "color: var(--hero-badge-kind-text);" in css
    # Override block must appear after defaults so it wins
    assert css.rfind("--bg: #f0fdf4;") > css.find("--bg: #0f172a;")


def test_dashboard_css_theme_file(tmp_path: Path):
    theme_path = tmp_path / "brand.json"
    theme_path.write_text(
        '{"bg": "#fff7ed", "accent": "#ea580c", "text": "#7c2d12"}\n',
        encoding="utf-8",
    )
    css = _generate_dashboard_css(
        {
            "theme_file": "brand.json",
            "_config_dir": str(tmp_path),
        }
    )
    assert "--bg: #fff7ed;" in css
    assert "--accent: #ea580c;" in css
    assert "--text: #7c2d12;" in css
    assert "--on-accent:" in css


def test_generate_dashboard_writes_themed_css(tmp_path: Path):
    generate_dashboard(
        tmp_path,
        [
            {
                "name": "DemoLib",
                "url": "DemoLib/index.html",
                "keywords": [],
                "description": "Demo",
                "version": "1.0",
                "keyword_count": 0,
                "kind": "library",
            }
        ],
        {
            "name": "Demo Site",
            "description": "Themed dashboard",
            "theme": {"accent": "#16a34a", "bg": "#f0fdf4"},
        },
    )
    css = (tmp_path / "assets" / "style.css").read_text(encoding="utf-8")
    assert "--accent: #16a34a;" in css
    assert "--bg: #f0fdf4;" in css
    assert (tmp_path / "index.html").exists()
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert RF_LOGO_ON_LIGHT_BG in html
    assert RF_LOGO_ON_DARK_BG not in html


def test_dashboard_logo_follows_background_luminance():
    light_html = _generate_dashboard_html([], {"theme": {"bg": "#fff1f2"}})
    dark_html = _generate_dashboard_html([], {"theme": {"bg": "#121417"}})
    default_html = _generate_dashboard_html([], {})
    assert RF_LOGO_ON_LIGHT_BG in light_html
    assert RF_LOGO_ON_DARK_BG in dark_html
    assert RF_LOGO_ON_DARK_BG in default_html
