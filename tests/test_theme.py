"""Theme token resolution and HTML injection."""

from pathlib import Path

import pytest

from robotframework_docgen.config_validation import validate_single_lib_config
from robotframework_docgen.generator import DocumentationGenerator
from robotframework_docgen.parser import KeywordInfo, LibraryInfo
from robotframework_docgen.theme import (
    ON_ACCENT_DARK,
    ON_ACCENT_LIGHT,
    RF_LOGO_ON_DARK_BG,
    RF_LOGO_ON_LIGHT_BG,
    is_valid_css_color,
    logo_url_for_theme,
    on_accent_for_theme,
    render_theme_override_css,
    resolve_theme_tokens,
    validate_theme_mapping,
)


def _minimal_library() -> LibraryInfo:
    return LibraryInfo(
        name="ThemeLib",
        version="1",
        scope="GLOBAL",
        description="<p>Hi</p>",
        keywords=[
            KeywordInfo(
                name="Ping",
                description="<p>Pong</p>",
                example="",
                parameters=[],
                return_type="None",
                line_number=1,
            )
        ],
    )


def test_valid_css_colors():
    assert is_valid_css_color("#38bdf8")
    assert is_valid_css_color("#fff")
    assert is_valid_css_color("rgba(56,189,248,0.15)")
    assert is_valid_css_color("steelblue")
    assert not is_valid_css_color("red; background:url(x)")
    assert not is_valid_css_color("url(javascript:alert(1))")


def test_resolve_preset_and_overrides():
    tokens = resolve_theme_tokens({"theme": "light"})
    assert tokens["--bg"] == "#f8fafc"
    assert tokens["--accent"] == "#0284c7"
    assert tokens["--badge-required"] == "#dc2626"
    assert tokens["--badge-default"] == "#16a34a"
    assert tokens["--arg-type"] == "#475569"

    tokens = resolve_theme_tokens(
        {"theme": {"preset": "light", "accent": "#16a34a"}}
    )
    assert tokens["--accent"] == "#16a34a"
    assert tokens["--bg"] == "#f8fafc"


def test_badge_and_arg_type_tokens_inject():
    html = DocumentationGenerator(
        _minimal_library(),
        config={
            "theme": {
                "badge_required": "#ef4444",
                "badge_required_bg": "rgba(239, 68, 68, 0.2)",
                "badge_required_text": "#fecaca",
                "badge_default": "#22c55e",
                "badge_default_bg": "rgba(34, 197, 94, 0.2)",
                "badge_default_text": "#bbf7d0",
                "badge_tag_bg": "#1e293b",
                "badge_tag_text": "#94a3b8",
                "badge_primary_bg": "rgba(56, 189, 248, 0.15)",
                "badge_primary_text": "#7dd3fc",
                "arg_type": "#a78bfa",
            }
        },
    ).generate_html()
    assert "--badge-required: #ef4444;" in html
    assert "--badge-required-bg: rgba(239, 68, 68, 0.2);" in html
    assert "--badge-required-text: #fecaca;" in html
    assert "--badge-default: #22c55e;" in html
    assert "--badge-default-bg: rgba(34, 197, 94, 0.2);" in html
    assert "--badge-default-text: #bbf7d0;" in html
    assert "--badge-tag-bg: #1e293b;" in html
    assert "--badge-tag-text: #94a3b8;" in html
    assert "--badge-primary-bg: rgba(56, 189, 248, 0.15);" in html
    assert "--badge-primary-text: #7dd3fc;" in html
    assert "--arg-type: #a78bfa;" in html
    assert "--arg-type-bg:" not in html
    assert "--arg-type-border:" not in html
    # Deprecated chip tokens are ignored (not injected) and don't fail validation.
    tokens = resolve_theme_tokens(
        {
            "theme": {
                "arg_type": "#a78bfa",
                "arg_type_bg": "#1e1b4b",
                "arg_type_border": "#4c1d95",
            }
        }
    )
    assert tokens["--arg-type"] == "#a78bfa"
    assert "--arg-type-bg" not in tokens
    assert "--arg-type-border" not in tokens
    assert validate_theme_mapping(
        {"arg_type_bg": "#1e1b4b", "arg_type_border": "#4c1d95"}
    ) == []
    assert "color: var(--badge-required-text);" in html
    assert "background: var(--badge-required-bg);" in html
    assert "color: var(--badge-default-text);" in html
    assert "background: var(--badge-default-bg);" in html
    assert "color: var(--badge-tag-text);" in html
    assert "background: var(--badge-tag-bg);" in html
    assert "color: var(--badge-primary-text);" in html
    assert "background: var(--badge-primary-bg);" in html
    assert "color: var(--arg-type);" in html


def test_code_bg_tokens_inject():
    html = DocumentationGenerator(
        _minimal_library(),
        config={
            "theme": {
                "code_bg": "#1e293b",
                "code_inline_bg": "rgba(56, 189, 248, 0.2)",
            }
        },
    ).generate_html()
    assert "--code-bg: #1e293b;" in html
    assert "--code-inline-bg: rgba(56, 189, 248, 0.2);" in html
    assert "background: var(--code-bg);" in html
    assert "background: var(--code-inline-bg);" in html
    light = resolve_theme_tokens({"theme": "light"})
    assert light["--code-bg"] == "#f1f5f9"
    assert light["--code-inline-bg"] == "rgba(2, 132, 199, 0.1)"


def test_rf_syntax_tokens_inject():
    html = DocumentationGenerator(
        _minimal_library(),
        config={
            "theme": {
                "rf_keyword": "#14b8a6",
                "rf_control": "#fb923c",
                "rf_setting": "#c084fc",
                "rf_variable": "#38bdf8",
                "rf_comment": "#4ade80",
                "rf_section": "#60a5fa",
                "rf_name": "#facc15",
                "rf_arg": "#fde047",
                "rf_string": "#fdba74",
                "rf_number": "#86efac",
            }
        },
    ).generate_html()
    assert "--rf-keyword: #14b8a6;" in html
    assert "--rf-control: #fb923c;" in html
    assert "--rf-setting: #c084fc;" in html
    assert "--rf-variable: #38bdf8;" in html
    assert "--rf-comment: #4ade80;" in html
    assert "--rf-section: #60a5fa;" in html
    assert "--rf-name: #facc15;" in html
    assert "--rf-arg: #fde047;" in html
    assert "--rf-string: #fdba74;" in html
    assert "--rf-number: #86efac;" in html
    assert "color: var(--rf-keyword);" in html
    assert "color: var(--rf-section);" in html
    light = resolve_theme_tokens({"theme": "light"})
    assert light["--rf-keyword"] == "#0f766e"
    assert light["--rf-section"] == "#1d4ed8"


def test_hero_badge_and_button_tokens_inject():
    html = DocumentationGenerator(
        _minimal_library(),
        config={
            "theme": {
                "hero_badge_bg": "#1e293b",
                "hero_badge_text": "#e2e8f0",
                "hero_badge_kind_bg": "rgba(56,189,248,0.15)",
                "hero_badge_kind_text": "#7dd3fc",
                "btn_primary_bg": "#38bdf8",
                "btn_primary_text": "#0b1120",
                "btn_ghost_bg": "transparent",
                "btn_ghost_text": "#94a3b8",
            }
        },
    ).generate_html()
    assert "--hero-badge-bg: #1e293b;" in html
    assert "--hero-badge-text: #e2e8f0;" in html
    assert "--hero-badge-kind-bg: rgba(56,189,248,0.15);" in html
    assert "--hero-badge-kind-text: #7dd3fc;" in html
    assert "--btn-primary-bg: #38bdf8;" in html
    assert "--btn-primary-text: #0b1120;" in html
    assert "--btn-ghost-bg: transparent;" in html
    assert "--btn-ghost-text: #94a3b8;" in html
    assert "background: var(--hero-badge-bg);" in html
    assert "color: var(--hero-badge-text);" in html
    assert "background: var(--hero-badge-kind-bg);" in html
    assert "color: var(--hero-badge-kind-text);" in html
    assert "color: var(--btn-primary-text);" in html
    assert "background: var(--btn-ghost-bg);" in html
    assert "color: var(--btn-ghost-text);" in html
    assert not validate_theme_mapping(
        {
            "hero_badge_bg": "#1e293b",
            "btn_primary_text": "#0b1120",
        }
    )


def test_theme_file(tmp_path: Path):
    theme_path = tmp_path / "brand.json"
    theme_path.write_text('{"accent": "#ef4444", "text": "#111827"}\n')
    tokens = resolve_theme_tokens(
        {"theme_file": "brand.json", "_config_dir": str(tmp_path)}
    )
    assert tokens == {"--accent": "#ef4444", "--text": "#111827"}


def test_theme_file_then_theme_object_wins(tmp_path: Path):
    theme_path = tmp_path / "brand.json"
    theme_path.write_text('{"accent": "#ef4444", "bg": "#000000"}\n')
    tokens = resolve_theme_tokens(
        {
            "theme_file": str(theme_path),
            "theme": {"accent": "#22c55e"},
            "_config_dir": str(tmp_path),
        }
    )
    assert tokens["--accent"] == "#22c55e"
    assert tokens["--bg"] == "#000000"


def test_render_theme_css():
    css = render_theme_override_css({"--accent": "#22c55e"})
    assert 'id="docgen-theme"' in css
    assert "--accent: #22c55e;" in css
    assert render_theme_override_css({}) == ""


def test_validation_rejects_bad_theme():
    errors = validate_theme_mapping({"accent": "not a color!!!"})
    assert any("accent" in e for e in errors)
    errors = validate_theme_mapping({"neon": "#fff"})
    assert any("unknown" in e for e in errors)
    errors = validate_single_lib_config({"theme": {"accent": "#gg0000"}})
    assert errors


def test_generator_injects_theme_override():
    html = DocumentationGenerator(
        _minimal_library(),
        config={"theme": {"accent": "#22c55e", "bg": "#111827"}},
    ).generate_html()
    assert 'id="docgen-theme"' in html
    assert "--accent: #22c55e;" in html
    assert "--bg: #111827;" in html
    assert "{{THEME_OVERRIDE}}" not in html


def test_generator_without_theme_has_empty_placeholder_removed():
    html = DocumentationGenerator(_minimal_library()).generate_html()
    assert "{{THEME_OVERRIDE}}" not in html
    assert 'id="docgen-theme"' not in html


def test_logo_url_for_light_and_dark_themes():
    assert logo_url_for_theme({}) == RF_LOGO_ON_DARK_BG
    assert logo_url_for_theme({"--bg": "#0f172a"}) == RF_LOGO_ON_DARK_BG
    assert logo_url_for_theme({"--bg": "#f8fafc"}) == RF_LOGO_ON_LIGHT_BG
    light = resolve_theme_tokens({"theme": "light"})
    assert logo_url_for_theme(light) == RF_LOGO_ON_LIGHT_BG


def test_generator_uses_light_logo_for_light_theme():
    html = DocumentationGenerator(
        _minimal_library(),
        config={"theme": "light"},
    ).generate_html()
    assert RF_LOGO_ON_LIGHT_BG in html
    assert "{{LOGO_URL}}" not in html
    dark_html = DocumentationGenerator(_minimal_library()).generate_html()
    assert RF_LOGO_ON_DARK_BG in dark_html


def test_logo_url_for_hsl_and_named_colors():
    assert logo_url_for_theme({"--bg": "hsl(260, 40%, 8%)"}) == RF_LOGO_ON_DARK_BG
    assert logo_url_for_theme({"--bg": "ivory"}) == RF_LOGO_ON_LIGHT_BG
    assert logo_url_for_theme({"--bg": "white"}) == RF_LOGO_ON_LIGHT_BG


def test_on_accent_tracks_accent_luminance():
    assert on_accent_for_theme({"--accent": "#0f172a"}) == ON_ACCENT_LIGHT
    assert on_accent_for_theme({"--accent": "#fef08a"}) == ON_ACCENT_DARK
    assert on_accent_for_theme({}) is None


def test_theme_css_injects_on_accent_for_dark_accent():
    css = render_theme_override_css({"--accent": "#0f172a", "--bg": "#f8fafc"})
    assert f"--on-accent: {ON_ACCENT_LIGHT};" in css


def test_generator_theme_chrome_uses_accent_vars_not_sky_blue():
    html = DocumentationGenerator(
        _minimal_library(),
        config={"theme": {"preset": "light", "accent": "#e11d48"}},
    ).generate_html()
    # Component chrome should follow --accent (defaults may still list sky blue).
    assert "outline: 2px solid color-mix(in srgb, var(--accent)" in html
    assert ".kwdoc code" in html and "background: var(--code-inline-bg);" in html
    assert ".badge.badge-tag" in html and "color: var(--muted);" in html
