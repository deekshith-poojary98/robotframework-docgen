# Robotframework Docgen

[![PyPI version](https://badge.fury.io/py/robotframework-libdocgen.svg)](https://badge.fury.io/py/robotframework-libdocgen)
[![Python](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/downloads/)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/robotframework-libdocgen?period=total&units=international_system&left_color=gray&right_color=orange&left_text=downloads)](https://pepy.tech/project/robotframework-libdocgen)
[![CI Lint](https://github.com/deekshith-poojary98/robotframework-docgen/actions/workflows/lint.yaml/badge.svg)](https://github.com/deekshith-poojary98/robotframework-docgen/actions/workflows/lint.yaml)
[![CI Tests](https://github.com/deekshith-poojary98/robotframework-docgen/actions/workflows/test.yaml/badge.svg)](https://github.com/deekshith-poojary98/robotframework-docgen/actions/workflows/test.yaml)
[![Security Scan](https://github.com/deekshith-poojary98/robotframework-docgen/actions/workflows/security.yaml/badge.svg)](https://github.com/deekshith-poojary98/robotframework-docgen/actions/workflows/security.yaml)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/deekshith-poojary98/robotframework-docgen)

A powerful documentation generator for Robot Framework **Python libraries** and **`.resource` / `.robot` keyword files**. It extracts keywords, arguments, and docstrings into professional HTML or Markdown docs — with a multi-entry dashboard, theming, coverage checks, and keyword changelogs.

**View Sample Documentation:** 
- [Generated Documentation](https://deekshith-poojary98.github.io/robotframework-docgen/SingleLibrary/)
- [Dashboard](https://deekshith-poojary98.github.io/robotframework-docgen/)

## 🚀 Features

- **Keyword Extraction**: Python libraries (`@keyword` via Libdoc + AST) and Robot Framework `.resource` / `.robot` files; private / underscore helpers are skipped
- **Resources in Config**: Multi-entry mode accepts `libraries` and/or `resources` arrays (resources-only configs work)
- **Examples from Tests**: Harvests `[Documentation]` + call snippets from suites (`--examples-from` or `examples_from_tests`)
- **Keyword Changelog**: `docgen diff` compares versions for added/removed/changed signatures (sources or catalog JSON)
- **Doc Coverage Report**: `docgen coverage` flags missing docs, undeclared types, and undocumented args (`--fail-under` for CI)
- **Catalog Export**: `docgen catalog` (or `--export-catalog`) writes machine-readable KeywordMetadata JSON
- **Type Hints & Enums**: Argument types from signatures; Enum parameters list allowed members
- **Importing Section**: Library constructor / `__init__` docs from Libdoc when present
- **Tags & Source Links**: Keyword tags in the UI/search; optional GitHub `Source:L…` links via `github_url` / `github_file` / `github_branch` (disable with `source_links: false`)
- **Cross-keyword Links**: `[Keyword Name]` references in docs become in-page links
- **Multiple Output Formats**: HTML or Markdown
- **Multi-Library Dashboard**: Grouping, global keyword search, filtering, sorting, export, live `--serve`
- **Parallel Processing**: Concurrent generation for multi-entry configs
- **Markdown Integration**: Tables, images, code blocks, lists; Robot Framework ``code`` spans preserved
- **Syntax Highlighting**: Themeable Robot Framework highlighter (library keywords matched when known)
- **Config Validation**: JSON/YAML configs validated (unknown keys, source types, theme tokens) before generation
- **Custom Themes**: Full color theming for library docs **and** the dashboard (`theme` / `theme_file`, `light`/`dark` presets), including badges, buttons, and RF syntax colors
- **Multi-Language Support**: Dashboard available in 10 languages with instant translation

## 📦 Installation

```bash
pip install robotframework-libdocgen
```

**Dependencies:** Robot Framework >= 5.0.1, Markdown >= 3.4.0, Pygments >= 2.10.0, Rich >= 13.0.0, PyYAML >= 6.0

## 🔧 CLI Arguments

| Flag | Short | Description | Mode |
|------|-------|-------------|------|
| `--output` | `-o` | Output file path | Single-library only |
| `--format` | `-f` | Output format: `html` (default) or `markdown` | Both |
| `--config` | `-c` | Path to JSON or YAML configuration file (`.json` / `.yaml` / `.yml`) | Both |
| `--multi-lib` | - | Enable multi-library mode | Multi-library only |
| `--dashboard` | - | Generate interactive dashboard UI | Multi-library only |
| `--serve` | - | Start web server to serve dashboard | Requires `--dashboard` |
| `--host` | - | Server host IP (default: `localhost`) | With `--serve` |
| `--port` | - | Server port number (default: `8000`) | With `--serve` |
| `--dir` | `-d` | Output directory | Both |
| `--parallel` | - | Enable parallel processing | Multi-library only |
| `--workers` | - | Number of parallel workers | With `--parallel` |
| `--export-catalog` | - | Also write keyword catalog JSON while generating | Both |
| `--examples-from` | - | Suite path(s) for harvesting keyword usage examples (repeatable) | Both |

### Utility Commands

```bash
# Keyword changelog between two versions (files, dirs, configs, or catalog JSON)
docgen diff v1/ v2/
docgen diff old.py new.py -f markdown -o changelog.md
docgen diff old-catalog.json new-catalog.json -f json -o changelog.json

# Documentation coverage report (text / markdown / json)
docgen coverage my_library.py
docgen coverage sample_libs/ --fail-under 80 -f json -o coverage.json

# Machine-readable catalog export
docgen catalog helpers.resource -o catalog.json
docgen catalog sample_configs/lib/multi_lib_config.json -o catalogs/all.json

# Harvest usage examples while generating docs
docgen helpers.resource --examples-from tests/ -o helpers.html
docgen my_library.py -c config.json --export-catalog catalog.json
```

See [Catalog, Coverage & Diff](#-catalog-coverage--diff) for details.

## 📝 Quick Start

### Single-Library Mode

```bash
# Generate HTML documentation (default)
docgen your_library.py -o docs.html -c config.json

# Document a Robot Framework resource or suite file
docgen helpers.resource -o helpers.html
docgen auth_keywords.robot -f markdown -o auth.md

# Generate Markdown documentation
docgen your_library.py -f markdown -o README.md -c config.json

# With output directory
docgen your_library.py -d docs -o my_library.html -c config.json

# Default settings (no config)
docgen your_library.py
```

### Multi-Library Mode

```bash
# Generate documentation for multiple libraries
docgen -c sample_configs/lib/multi_lib_config.json --multi-lib

# With custom output directory
docgen -c sample_configs/lib/multi_lib_config.json --multi-lib -d docs

# With parallel processing (faster for many libraries)
docgen -c sample_configs/lib/multi_lib_config.json --multi-lib --parallel

# With custom number of workers
docgen -c sample_configs/lib/multi_lib_config.json --multi-lib --parallel --workers 4
```

**Output Structure:**
```
output/
├── Library1/
│   └── index.html
└── Library2/
    └── index.html
```

### Dashboard Mode

Generate an interactive dashboard with library listing, search, filtering, and more:

```bash
# Generate dashboard
docgen -c sample_configs/lib/multi_lib_config.json --dashboard

# Generate and serve dashboard locally
docgen -c sample_configs/lib/multi_lib_config.json --dashboard --serve

# Serve on custom host and port
docgen -c sample_configs/lib/multi_lib_config.json --dashboard --serve --host 0.0.0.0 --port 8080

# Combine with parallel processing
docgen -c sample_configs/lib/multi_lib_config.json --dashboard --parallel --serve
```

**Dashboard Features:**
- 📚 **Library Overview**: Browse all libraries with metadata and statistics
- 🔍 **Global Keyword Search**: Search keywords across all libraries with instant results
- 🎯 **Advanced Filtering**: Filter by author, maintainer, license, Robot Framework version, Python version
- 📊 **Sorting Options**: Sort libraries by name or keyword count
- 📥 **Export Functionality**: Export library data as CSV, Excel, or PDF
- 🌐 **Multi-Language**: Dashboard available in 10 languages (English, Spanish, French, German, Chinese, Japanese, Portuguese, Russian, Italian, Korean)
- ⌨️ **Keyboard Shortcuts**: `/` to focus search, `↑/↓` to navigate, `Enter` to open, `Esc` to close
- 💾 **State Persistence**: Remembers your search, sort, and language preferences

**Dashboard Output Structure:**
```
output/
├── index.html          # Dashboard homepage
├── assets/
│   ├── style.css       # Dashboard styles
│   ├── app.js          # Dashboard JavaScript
│   ├── search.js       # Search functionality
│   └── search-index.json  # Keyword search index
├── Library1/
│   └── index.html
└── Library2/
    └── index.html
```

## ⚙️ Configuration

Config files may be **JSON** (`.json`) or **YAML** (`.yaml` / `.yml`). The schema is the same for both.

### Single-Library Configuration

All fields are optional. Only provide what you need:

```json
{
  "github_url": "https://github.com/username/repo",
  "library_url": "https://example.com/library",
  "support_email": "support@example.com",
  "author": "Your Name",
  "maintainer": "Maintainer Name",
  "license": "MIT",
  "robot_framework": ">=7.0",
  "python": ">=3.11",
  "theme_file": "sample_configs/theme/graphite.json"
}
```

**Note:** Single-library configs should NOT contain `site`, `libraries`, or `resources` keys.

### Multi-Library Configuration

Requires a `site` object and at least one entry in `libraries` and/or `resources` (resources-only configs are valid):

```json
{
  "site": {
    "name": "My Libraries",
    "description": "Keyword documentation for our Robot Framework libraries",
    "github_url": "https://github.com/username/repo",
    "support_email": "support@example.com",
    "author": "Org / Team Name",
    "license": "MIT",
    "robot_framework": ">=7.0",
    "python": ">=3.11",
    "theme_file": "../theme/graphite.json"
  },
  "libraries": [
    {
      "name": "Library1",
      "source": "library1.py",
      "output_file": "index.html",
      "output_format": "html",
      "group": "Core Utilities",
      "library_url": "https://example.com/library1",
      "examples_from_tests": ["tests/library1/"]
    },
    {
      "name": "Library2",
      "source": "library2.py",
      "output_format": "markdown",
      "group": "Data"
    }
  ],
  "resources": [
    {
      "name": "HTTP Helpers",
      "source": "sample_libs/http_helpers.resource",
      "group": "Shared",
      "examples_from_tests": ["sample_libs/tests/"]
    }
  ]
}
```

- `libraries[].source` must be a `.py` file
- `resources[].source` must be a Robot source (`.resource`, `.robot`, …)
- Invalid keys, missing sources, and bad theme tokens fail fast with validation errors

**Configuration Priority (Multi-Library):**
1. Output filename: entry `output_file` > default (`index.html` or `index.md`)
2. Output format: entry `output_format` > CLI `-f/--format` > default (`html`)
3. Metadata / theme / examples: entry-specific config overrides `site` (and top-level fallbacks)

### Configuration Options

- **Metadata**: `author`, `maintainer`, `license`, `robot_framework`, `python`
- **Links**: `github_url` (enables "View on GitHub" and "Open an Issue" buttons), `library_url` (enables "Library Website" button), `support_email` (enables "Contact Support" button)
- **Source links**: with `github_url`, optional `github_file` (repo-relative path) and `github_branch` (default `main`) add per-keyword `Source:L…` links. Set `source_links: false` to keep GitHub / Issues buttons but hide those keyword links
- **Examples from tests**: `examples_from_tests` (string or list of suite/resource paths) — same as `--examples-from`
- **Theme**: see [Custom Themes](#-custom-themes) below
- **Dashboard**: `site.name` and `site.description` for branding; theming via `site.theme` / `site.theme_file`
- **Grouping**: optional `group` on each library/resource entry; entries without a group appear under **Ungrouped**

**Note:** In multi-library mode, `name` on an entry is optional (class / file stem is used).

## 🎨 Custom Themes

Themes apply to **library HTML docs** and the **dashboard** (same token set).

### How to set a theme

| Mode | Where to set |
|------|----------------|
| Single-library | Top-level `theme` and/or `theme_file` |
| Multi-library / dashboard | Prefer `site.theme` / `site.theme_file` (inherited by libraries; also styles the dashboard). Top-level `theme` / `theme_file` is a dashboard fallback. Per-library `theme` overrides site for that library’s docs. |

`theme` may be:
- Preset name: `"light"` or `"dark"`
- Path to a JSON/YAML theme file
- Inline token object

`theme_file` is always a path to a JSON/YAML theme file. If both are set, `theme_file` loads first, then `theme` overrides.

```json
{
  "theme": "light",
  "theme_file": "brand.json"
}
```

```json
{
  "theme": {
    "preset": "light",
    "accent": "#16a34a",
    "hero_badge_bg": "#e8fcef",
    "hero_badge_text": "#14532d",
    "btn_primary_bg": "#16a34a",
    "btn_primary_text": "#f8fafc",
    "rf_keyword": "#1d4ed8",
    "rf_section": "#6d28d9"
  }
}
```

### Token groups

| Group | Keys |
|-------|------|
| Surfaces | `bg`, `bg_alt`, `card`, `border`, `text`, `muted`, `accent`, `accent_soft` |
| Argument badges | `badge_required`, `badge_required_bg`, `badge_required_text`, `badge_default`, `badge_default_bg`, `badge_default_text`, `badge_tag_bg`, `badge_tag_text`, `badge_primary_bg`, `badge_primary_text` |
| Arg / return type text | `arg_type` |
| Hero badges | `hero_badge_bg`, `hero_badge_text`, `hero_badge_kind_bg`, `hero_badge_kind_text` |
| Buttons | `btn_primary_bg`, `btn_primary_text`, `btn_ghost_bg`, `btn_ghost_text` |
| Code surfaces | `code_bg`, `code_inline_bg` |
| RF syntax | `rf_keyword`, `rf_control`, `rf_setting`, `rf_variable`, `rf_comment`, `rf_section`, `rf_name`, `rf_arg`, `rf_string`, `rf_number` |

Omitted tokens keep built-in defaults (or the chosen preset). Colors may be hex (`#38bdf8`, `#fff`), `rgb`/`rgba`, `hsl`/`hsla`, or CSS named colors.

### Sample themes

Ready-made files live in [`sample_configs/theme/`](sample_configs/theme/) (e.g. `graphite.json`, `sage.yml`, `matcha.yml`, `accent-only.json`, `paper.json`, `ocean.yaml`, …). An example multi-lib + dashboard config is [`sample_configs/lib/timetravel_with_theme.json`](sample_configs/lib/timetravel_with_theme.json).

```bash
docgen -c sample_configs/lib/timetravel_with_theme.json --dashboard -d timetravel-docs
```

## 📖 Usage

### Keyword Decorator

Public Python methods need `@keyword` to appear in docs. Robot `.resource` / `.robot` keywords come from Libdoc (private / `robot:private` / underscore helpers are skipped).

```python
from enum import Enum
from robot.api.deco import keyword

class Color(Enum):
    RED = "red"
    BLUE = "blue"

class MyLibrary:
    def __init__(self, base_url: str = "https://example.com"):
        """Constructor docs appear in the Importing section."""
        self.base_url = base_url

    @keyword("Open Application")
    def open_app(self, path: str, color: Color = Color.RED) -> None:
        """
        Opens an application at the given path.

        Enum-typed args list allowed members. Cross-link with [Other Keyword].
        """
        pass

    @keyword
    def open_workbook(self, file: str) -> None:
        """Function name becomes title case: Open Workbook."""
        pass
```

**Important:** Undecorated Python methods do **not** appear in documentation.

### Examples from Tests

Suites that call your keywords can supply **Example** blocks (test `[Documentation]` + body snippet):

```bash
docgen sample_libs/http_helpers.resource \
  --examples-from sample_libs/tests/ \
  -o http_helpers.html
```

Or via config (`examples_from_tests` on the entry, `site`, or top-level — same as `--examples-from`):

```json
{
  "examples_from_tests": ["tests/", "acceptance.robot"]
}
```

Harvested suite examples win over an `Examples:` section inside the keyword docstring.

### Markdown in Docstrings

Docstrings are rendered as Markdown (Python-Markdown), aligned with Robot Framework Libdoc 7.5+ plus common extras:

- **Headers**: `#` … `######` (TOC via `%TOC%` marker)
- **Emphasis**: `**bold**`, `*italic*`, `` `code` ``
- **Links / images**: `[text](url)`, bare `https://…` autolinks, `![alt](url)`
- **Lists**: bulleted, numbered, nested (4-space indent)
- **Tables**: pipe tables
- **Quotes / rules**: `>` blockquotes, `---` horizontal rules
- **Fenced code**: ` ```robot ` / ` ```python ` (Robot highlighting is docgen-native)
- **Admonitions**: `!!! note` / `tip` / `warning` / `danger` / …
- **Definition lists**, **footnotes**, **abbreviations** (`*[HTML]: …`)
- **Attribute lists** / **Markdown inside HTML** (`md_in_html`)
- **Keyword refs**: `[Keyword Name]` → in-page links when resolvable

**Example:**
```python
@keyword
def process_data(self, data: dict) -> dict:
    """
    Process data with configuration.
    
    **Arguments:**
    - `data`: Dictionary containing data to process
    
    **Example:**
    ```robot
    *** Settings ***
    Library    MyLibrary
    
    *** Test Cases ***
    Example
        ${result}=    Process Data    ${data}
    ```
    
    **Options:**
    | Option | Description |
    |--------|-------------|
    | validate | Validate input data |
    | transform | Transform data structure |
    """
    pass
```

## 🎛️ Dashboard Features

The interactive dashboard lists every config entry (Python libraries and Robot resources) with search, filtering, and export.

### Library Search
- **Real-time filtering**: Type to filter library cards instantly
- **No dropdown results**: Matching libraries are shown directly as cards

### Keyword Search
- **Global search**: Search keywords across all libraries
- **Instant results**: See matching keywords with library names
- **Keyboard navigation**: Use arrow keys to navigate, Enter to open
- **Quick access**: Press `/` to focus the search bar

### Library Grouping
- **Normal View**: Default view showing all entries as cards (grouping ignored)
- **Group View**: Group cards summarizing entry count and total keywords per group
- **Group Libraries View**: Drill into a single group to see only its libraries/resources, with breadcrumb and "Back to Groups"
- **Ungrouped Handling**: Entries without a `group` value appear under **Ungrouped**

### Filtering
Filter libraries by:
- **Author**: Filter by library author
- **Maintainer**: Filter by maintainer
- **License**: Filter by license type
- **Robot Framework Version**: Filter by RF version requirements
- **Python Version**: Filter by Python version requirements

### Sorting
- **Name (A–Z)**: Alphabetical sorting
- **Keyword Count (desc)**: Sort by number of keywords

### Export
Export library metadata as:
- **CSV**: Comma-separated values
- **Excel**: Microsoft Excel format
- **PDF**: Portable Document Format

### Multi-Language Support
Dashboard is available in:
- English, Spanish, French, German, Chinese, Japanese, Portuguese, Russian, Italian, Korean
- Language preference is saved in browser localStorage
- Instant translation without page reload

### Keyboard Shortcuts
- `/` - Focus keyword search bar
- `↑/↓` - Navigate search results
- `Enter` - Open selected result
- `Esc` - Close dropdown / Remove focus

## 🎨 Syntax Highlighting

Robot Framework code blocks are highlighted with dedicated CSS classes. Default colors (VS Code Dark+ style):

| Element | Token | Default feel |
|---------|-------|----------------|
| Section headers (`*** Settings ***`) | `rf_section` | Blue |
| Keywords | `rf_keyword` | Teal (bold) |
| Variables (`${var}`, `@{list}`, `&{dict}`) | `rf_variable` | Light blue |
| Comments (`# …`) | `rf_comment` | Green (italic) |
| Named args (`arg=value`) | `rf_arg` | Yellow/beige |
| Control flow (`IF`, `FOR`, `TRY`) | `rf_control` | Orange |
| Settings (`[Setup]`, `Library`, …) | `rf_setting` | Purple |
| Test / keyword names | `rf_name` | Yellow |

Override any of these via theme tokens (see [Custom Themes](#-custom-themes)). The `light` preset ships readable light-background syntax colors.

Library and BuiltIn keywords are matched when known; other names in call position (including example/dummy keywords) are highlighted structurally.

## 📊 Catalog, Coverage & Diff

These utilities share the same catalog model (Python libraries + Robot resources). Inputs can be a source file, a directory, a multi-lib config, or an existing catalog JSON.

| Command | Purpose |
|---------|---------|
| `docgen catalog <source> -o catalog.json` | Export KeywordMetadata (names, params, types, docs) |
| `docgen coverage <source>` | Report undocumented keywords / untyped params; `--fail-under N` exits 1 below threshold |
| `docgen diff <old> <new>` | Changelog: added / removed / changed signatures |

Formats: `-f text|markdown|json` (coverage & diff). While generating docs, `--export-catalog path.json` writes the same catalog without a separate command.

```bash
docgen catalog sample_libs/ -o catalogs/sample.json
docgen coverage catalogs/sample.json --fail-under 90
docgen diff v1-catalog.json v2-catalog.json -f markdown -o CHANGELOG.md
```

## ❓ Troubleshooting

### "Successfully parsed 0 keywords"

For Python libraries, ensure public methods are decorated with `@keyword`:
```python
@keyword("My Keyword")  # ✅ Correct
def my_method(self):
    pass

def helper_method(self):  # ❌ Won't appear
    pass
```

For `.resource` / `.robot` files, confirm the path is correct and keywords are not private (`robot:private` or underscore-prefixed).

### Multi-library mode errors

- Ensure config contains a `site` object and a non-empty `libraries` and/or `resources` array
- Use `--multi-lib` flag: `docgen -c config.json --multi-lib`
- Don't use `--multi-lib` with single-library configs (no `site` / `libraries` / `resources`)
- `--dashboard` automatically enables multi-library mode (no need for `--multi-lib`)
- Validation errors (unknown keys, wrong source extension, missing files, bad theme colors) are printed before generation

### Dashboard and serve errors

- `--serve` requires `--dashboard` flag: `docgen -c config.json --dashboard --serve`
- Dashboard requires multi-library configuration with `site` and `libraries` and/or `resources`
- Port already in use: Use `--port` to specify a different port
- To serve on all network interfaces: Use `--host 0.0.0.0`

### Output file location

- **Single-library**: `-d/--dir` sets base directory, `-o/--output` can be relative (combined with `-d`) or absolute (ignores `-d`)
- **Multi-library**: `-d/--dir` sets base output directory (defaults to `output/`), `-o/--output` is ignored

### Config not being read

Ensure you're passing the `-c/--config` flag:
```bash
docgen your_library.py -c config.json  # ✅ Correct
docgen your_library.py                 # ❌ Config not loaded
```

### Type hints not showing

Add type hints to function signatures (Enum types also list members in the docs):
```python
@keyword
def my_keyword(self, arg1: str, arg2: int = 10) -> bool:
    """Keyword documentation."""
    pass
```

If type hints are not provided, arguments show as `Any` type.

## 📚 Examples

- **Sample libraries / resources**: `sample_libs/` (includes `http_helpers.resource`, `auth_suite.robot`, `tests/`)
- **Sample configs**: `sample_configs/lib/` (`multi_lib_config.json`, `single_lib_config.json`, `timetravel_with_theme.json`)
- **Themes**: `sample_configs/theme/`

**Single library / resource:**
```bash
docgen sample_libs/string_utils.py -f html -o sample_docs.html -c sample_configs/lib/single_lib_config.json

docgen sample_libs/http_helpers.resource \
  --examples-from sample_libs/tests/ \
  -o http_helpers.html
```

**Multi-library with dashboard:**
```bash
docgen -c sample_configs/lib/multi_lib_config.json --dashboard -d docs

# Themed TimeTravel sample (uses site.theme_file)
docgen -c sample_configs/lib/timetravel_with_theme.json --dashboard -d timetravel-docs
docgen -c sample_configs/lib/timetravel_with_theme.json --dashboard --serve -d timetravel-docs
docgen -c sample_configs/lib/timetravel_with_theme.json --dashboard --parallel --serve --port 8080
```

**Quality gates:**
```bash
docgen coverage sample_libs/ --fail-under 80 -f markdown -o coverage.md
docgen catalog sample_libs/ -o catalogs/sample.json
docgen diff catalogs/old.json catalogs/sample.json -f text
```

## 📄 License

Apache License 2.0 - See [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
