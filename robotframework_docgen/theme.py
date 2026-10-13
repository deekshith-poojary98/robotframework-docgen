"""
Theme token resolution for Docgen HTML output.

Users override CSS custom properties via config ``theme`` / ``theme_file``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union


# Removed from the theme surface (arg type chips are plain text now).
# Still accepted in configs/theme files so older themes don't fail validation.
DEPRECATED_THEME_TOKENS = frozenset({"arg_type_bg", "arg_type_border"})

# Public config keys → CSS custom properties in libdoc.html :root
THEME_TOKENS = {
    "bg": "--bg",
    "bg_alt": "--bg-alt",
    "card": "--card",
    "border": "--border",
    "text": "--text",
    "muted": "--muted",
    "accent": "--accent",
    "accent_soft": "--accent-soft",
    # Argument / status badges (seed colors + explicit bg/text)
    "badge_required": "--badge-required",
    "badge_required_bg": "--badge-required-bg",
    "badge_required_text": "--badge-required-text",
    "badge_default": "--badge-default",
    "badge_default_bg": "--badge-default-bg",
    "badge_default_text": "--badge-default-text",
    "badge_tag_bg": "--badge-tag-bg",
    "badge_tag_text": "--badge-tag-text",
    "badge_primary_bg": "--badge-primary-bg",
    "badge_primary_text": "--badge-primary-text",
    # Argument / return type text (plain inline; no chip bg/border)
    "arg_type": "--arg-type",
    # Hero badges (Library / Version / Scope / keyword count)
    "hero_badge_bg": "--hero-badge-bg",
    "hero_badge_text": "--hero-badge-text",
    "hero_badge_kind_bg": "--hero-badge-kind-bg",
    "hero_badge_kind_text": "--hero-badge-kind-text",
    # Hero action buttons
    "btn_primary_bg": "--btn-primary-bg",
    "btn_primary_text": "--btn-primary-text",
    "btn_ghost_bg": "--btn-ghost-bg",
    "btn_ghost_text": "--btn-ghost-text",
    # Code surfaces
    "code_bg": "--code-bg",
    "code_inline_bg": "--code-inline-bg",
    # Robot Framework syntax highlighting
    "rf_keyword": "--rf-keyword",
    "rf_control": "--rf-control",
    "rf_setting": "--rf-setting",
    "rf_variable": "--rf-variable",
    "rf_comment": "--rf-comment",
    "rf_section": "--rf-section",
    "rf_name": "--rf-name",
    "rf_arg": "--rf-arg",
    "rf_string": "--rf-string",
    "rf_number": "--rf-number",
}

THEME_PRESETS: Dict[str, Dict[str, str]] = {
    # Empty preset keeps the built-in template defaults.
    "dark": {},
    "light": {
        "bg": "#f8fafc",
        "bg_alt": "#ffffff",
        "card": "#ffffff",
        "border": "#e2e8f0",
        "text": "#0f172a",
        "muted": "#64748b",
        "accent": "#0284c7",
        "accent_soft": "rgba(2, 132, 199, 0.12)",
        "badge_required": "#dc2626",
        "badge_default": "#16a34a",
        "arg_type": "#475569",
        "code_bg": "#f1f5f9",
        "code_inline_bg": "rgba(2, 132, 199, 0.1)",
        "rf_keyword": "#0f766e",
        "rf_control": "#c2410c",
        "rf_setting": "#7c3aed",
        "rf_variable": "#0369a1",
        "rf_comment": "#15803d",
        "rf_section": "#1d4ed8",
        "rf_name": "#a16207",
        "rf_arg": "#a16207",
        "rf_string": "#b45309",
        "rf_number": "#15803d",
    },
}

_COLOR_RE = re.compile(
    r"^(?:"
    r"#[0-9a-fA-F]{3}"
    r"|#[0-9a-fA-F]{6}"
    r"|#[0-9a-fA-F]{8}"
    r"|rgb\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*\)"
    r"|rgba\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*\)"
    r"|hsl\(\s*[\d.]+\s*,\s*[\d.]+%\s*,\s*[\d.]+%\s*\)"
    r"|hsla\(\s*[\d.]+\s*,\s*[\d.]+%\s*,\s*[\d.]+%\s*,\s*[\d.]+\s*\)"
    r"|[a-zA-Z]{3,30}"
    r")$"
)


def is_valid_css_color(value: str) -> bool:
    """Return True when ``value`` looks like a safe CSS color."""
    if not isinstance(value, str):
        return False
    candidate = value.strip()
    if not candidate or len(candidate) > 80:
        return False
    # Reject characters that could break out of a CSS declaration.
    if any(ch in candidate for ch in (";", "{", "}", "<", ">", "\n", "\r")):
        return False
    return bool(_COLOR_RE.match(candidate))


def validate_theme_mapping(
    theme: Any, label: str = "theme"
) -> List[str]:
    """Validate a theme object or preset name. Returns error messages."""
    errors: List[str] = []
    if theme is None:
        return errors

    if isinstance(theme, str):
        name = theme.strip()
        if not name:
            errors.append(f"{label} must be a non-empty string when used as a preset/path")
            return errors
        # Bare preset names are validated here; file paths are checked when resolved.
        suffix = Path(name).suffix.lower()
        if name in THEME_PRESETS or "/" in name or "\\" in name or suffix in {
            ".json",
            ".yaml",
            ".yml",
        }:
            return errors
        if suffix:
            return errors
        errors.append(
            f"{label}: unknown preset {name!r}; "
            f"expected one of {sorted(THEME_PRESETS)} or a JSON/YAML file path"
        )
        return errors

    if not isinstance(theme, dict):
        errors.append(f"{label} must be an object, preset name, or omitted")
        return errors

    unknown = sorted(
        k
        for k in theme.keys()
        if k not in THEME_TOKENS
        and k not in DEPRECATED_THEME_TOKENS
        and k != "preset"
    )
    if unknown:
        errors.append(
            f"{label}: unknown key(s): "
            + ", ".join(repr(k) for k in unknown)
            + f"; allowed: {sorted(THEME_TOKENS)!r} and 'preset'"
        )

    preset = theme.get("preset")
    if preset is not None:
        if not isinstance(preset, str) or preset.strip() not in THEME_PRESETS:
            errors.append(
                f"{label}.preset must be one of {sorted(THEME_PRESETS)}, got {preset!r}"
            )

    for key, value in theme.items():
        if key == "preset":
            continue
        if key not in THEME_TOKENS:
            continue
        if not isinstance(value, str) or not is_valid_css_color(value):
            errors.append(
                f"{label}.{key} must be a CSS color "
                f"(hex / rgb(a) / hsl(a) / named), got {value!r}"
            )
    return errors


def validate_theme_config(
    config: Mapping[str, Any], label: str = "config"
) -> List[str]:
    """Validate ``theme`` / ``theme_file`` fields on a config mapping."""
    errors: List[str] = []
    if "theme" in config:
        errors.extend(validate_theme_mapping(config.get("theme"), f"{label}.theme"))
    theme_file = config.get("theme_file")
    if theme_file is not None:
        if not isinstance(theme_file, str) or not theme_file.strip():
            errors.append(f"{label}.theme_file must be a non-empty string path")
    return errors


def _load_theme_file(path: Path) -> Dict[str, Any]:
    from robotframework_docgen.config_io import load_mapping_file

    return load_mapping_file(path)


def _coerce_theme_layer(
    theme: Union[str, Mapping[str, Any], None],
    base_dir: Path,
) -> Dict[str, str]:
    """Normalize one theme layer into token→color (no CSS var names yet)."""
    if theme is None:
        return {}

    if isinstance(theme, str):
        name = theme.strip()
        if name in THEME_PRESETS:
            return dict(THEME_PRESETS[name])
        path = Path(name)
        if not path.is_absolute():
            path = (base_dir / path).resolve()
        else:
            path = path.resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Theme file not found: {path}")
        loaded = _load_theme_file(path)
        return _coerce_theme_layer(loaded, path.parent)

    if not isinstance(theme, Mapping):
        return {}

    tokens: Dict[str, str] = {}
    preset = theme.get("preset")
    if isinstance(preset, str) and preset.strip() in THEME_PRESETS:
        tokens.update(THEME_PRESETS[preset.strip()])

    for key, css_name in THEME_TOKENS.items():
        del css_name  # unused here
        value = theme.get(key)
        if isinstance(value, str) and value.strip():
            tokens[key] = value.strip()
    return tokens


def resolve_theme_tokens(
    config: Optional[Mapping[str, Any]],
    base_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, str]:
    """
    Resolve config theme settings to ``{css_var: color}``.

    Precedence (later wins):
    1. ``theme_file``
    2. ``theme`` (preset name, path string, or object)
    """
    if not config:
        return {}

    root = Path(base_dir) if base_dir else Path(
        str(config.get("_config_dir") or ".")
    )
    if not root.is_absolute():
        root = root.resolve()

    merged: Dict[str, str] = {}

    theme_file = config.get("theme_file")
    if isinstance(theme_file, str) and theme_file.strip():
        path = Path(theme_file.strip())
        if not path.is_absolute():
            path = (root / path).resolve()
        loaded = _load_theme_file(path)
        merged.update(_coerce_theme_layer(loaded, path.parent))

    if "theme" in config:
        merged.update(_coerce_theme_layer(config.get("theme"), root))

    return {
        THEME_TOKENS[key]: value
        for key, value in merged.items()
        if key in THEME_TOKENS and is_valid_css_color(value)
    }


def render_theme_override_css(css_vars: Mapping[str, str]) -> str:
    """Render a ``<style>`` block that overrides ``:root`` theme variables."""
    if not css_vars:
        return ""
    rendered = dict(css_vars)
    on_accent = on_accent_for_theme(css_vars)
    if on_accent:
        rendered["--on-accent"] = on_accent
    lines = ["  <style id=\"docgen-theme\">", "    :root {"]
    for var_name in sorted(rendered.keys()):
        value = rendered[var_name]
        lines.append(f"      {var_name}: {value};")
    lines.extend(["    }", "  </style>"])
    return "\n".join(lines)


# Dark SVG is light-colored (for dark headers); plain SVG is dark-colored (for light headers).
RF_LOGO_ON_DARK_BG = (
    "https://docs.robotframework.org/img/robot-framework-dark.svg"
)
RF_LOGO_ON_LIGHT_BG = "https://docs.robotframework.org/img/robot-framework.svg"
ON_ACCENT_DARK = "#0b1120"
ON_ACCENT_LIGHT = "#f8fafc"

_RGB_RE = re.compile(
    r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)",
    re.IGNORECASE,
)
_HSL_RE = re.compile(
    r"hsla?\(\s*([\d.]+)\s*,\s*([\d.]+)%\s*,\s*([\d.]+)%",
    re.IGNORECASE,
)

# Common CSS named colors used in theme configs (sRGB 0–255).
_NAMED_COLORS: Dict[str, Tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "ivory": (255, 255, 240),
    "snow": (255, 250, 250),
    "linen": (250, 240, 230),
    "beige": (245, 245, 220),
    "whitesmoke": (245, 245, 245),
    "ghostwhite": (248, 248, 255),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "silver": (192, 192, 192),
    "tan": (210, 180, 140),
    "crimson": (220, 20, 60),
    "navy": (0, 0, 128),
    "maroon": (128, 0, 0),
    "purple": (128, 0, 128),
    "teal": (0, 128, 128),
    "olive": (128, 128, 0),
    "aqua": (0, 255, 255),
    "cyan": (0, 255, 255),
    "fuchsia": (255, 0, 255),
    "magenta": (255, 0, 255),
    "orange": (255, 165, 0),
    "coral": (255, 127, 80),
    "salmon": (250, 128, 114),
    "tomato": (255, 99, 71),
    "gold": (255, 215, 0),
    "khaki": (240, 230, 140),
    "lavender": (230, 230, 250),
    "steelblue": (70, 130, 180),
    "royalblue": (65, 105, 225),
    "dodgerblue": (30, 144, 255),
    "skyblue": (135, 206, 235),
    "lightblue": (173, 216, 230),
    "darkblue": (0, 0, 139),
    "darkgreen": (0, 100, 0),
    "darkslategray": (47, 79, 79),
    "darkslategrey": (47, 79, 79),
    "dimgray": (105, 105, 105),
    "dimgrey": (105, 105, 105),
}


def _hsl_to_rgb(h: float, s: float, lightness: float) -> Tuple[float, float, float]:
    """Convert HSL (h degrees, s/l percent) to sRGB 0–255."""
    h = h % 360.0
    s = max(0.0, min(100.0, s)) / 100.0
    lightness = max(0.0, min(100.0, lightness)) / 100.0
    c = (1.0 - abs(2.0 * lightness - 1.0)) * s
    x = c * (1.0 - abs((h / 60.0) % 2.0 - 1.0))
    m = lightness - c / 2.0
    if h < 60:
        rp, gp, bp = c, x, 0.0
    elif h < 120:
        rp, gp, bp = x, c, 0.0
    elif h < 180:
        rp, gp, bp = 0.0, c, x
    elif h < 240:
        rp, gp, bp = 0.0, x, c
    elif h < 300:
        rp, gp, bp = x, 0.0, c
    else:
        rp, gp, bp = c, 0.0, x
    return ((rp + m) * 255.0, (gp + m) * 255.0, (bp + m) * 255.0)


def _parse_rgb(color: str) -> Optional[Tuple[float, float, float]]:
    """Return ``(r, g, b)`` in 0–255 from hex/rgb/hsl/named CSS colors, else None."""
    if not isinstance(color, str):
        return None
    candidate = color.strip()
    if candidate.startswith("#"):
        hex_part = candidate[1:]
        if len(hex_part) == 3:
            hex_part = "".join(ch * 2 for ch in hex_part)
        if len(hex_part) in (6, 8):
            try:
                return (
                    int(hex_part[0:2], 16),
                    int(hex_part[2:4], 16),
                    int(hex_part[4:6], 16),
                )
            except ValueError:
                return None
        return None
    match = _RGB_RE.match(candidate)
    if match:
        try:
            return (
                float(match.group(1)),
                float(match.group(2)),
                float(match.group(3)),
            )
        except ValueError:
            return None
    match = _HSL_RE.match(candidate)
    if match:
        try:
            return _hsl_to_rgb(
                float(match.group(1)),
                float(match.group(2)),
                float(match.group(3)),
            )
        except ValueError:
            return None
    named = _NAMED_COLORS.get(candidate.lower())
    if named:
        return (float(named[0]), float(named[1]), float(named[2]))
    return None


def _relative_luminance(r: float, g: float, b: float) -> float:
    """WCAG relative luminance for sRGB channels in 0–255."""

    def channel(value: float) -> float:
        v = max(0.0, min(255.0, value)) / 255.0
        if v <= 0.04045:
            return v / 12.92
        return ((v + 0.055) / 1.055) ** 2.4

    return (
        0.2126 * channel(r)
        + 0.7152 * channel(g)
        + 0.0722 * channel(b)
    )


def is_light_background(css_vars: Mapping[str, str]) -> bool:
    """True when theme ``--bg`` (or ``--bg-alt``) is light enough for a dark logo."""
    bg = css_vars.get("--bg") or css_vars.get("--bg-alt")
    if not bg:
        return False
    rgb = _parse_rgb(bg)
    if rgb is None:
        return False
    return _relative_luminance(*rgb) > 0.45


def logo_url_for_theme(css_vars: Mapping[str, str]) -> str:
    """Pick the RF logo that stays visible on the themed header background."""
    if is_light_background(css_vars):
        return RF_LOGO_ON_LIGHT_BG
    return RF_LOGO_ON_DARK_BG


def on_accent_for_theme(css_vars: Mapping[str, str]) -> Optional[str]:
    """
    Choose readable text color for accent-filled buttons.

    Light accents get dark text; dark accents get light text.
    """
    accent = css_vars.get("--accent")
    if not accent:
        return None
    rgb = _parse_rgb(accent)
    if rgb is None:
        return None
    if _relative_luminance(*rgb) > 0.45:
        return ON_ACCENT_DARK
    return ON_ACCENT_LIGHT
