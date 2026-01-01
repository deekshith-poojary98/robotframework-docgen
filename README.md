# Robotframework Docgen

[![PyPI version](https://badge.fury.io/py/robotframework-libdocgen.svg)](https://badge.fury.io/py/robotframework-libdocgen)
[![Python](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/downloads/)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/robotframework-libdocgen?period=total&units=international_system&left_color=gray&right_color=orange&left_text=downloads)](https://pepy.tech/project/robotframework-libdocgen)

A powerful documentation generator for Robot Framework libraries that extracts keywords, arguments, and docstrings to create professional, well-formatted HTML documentation with advanced markdown support and syntax highlighting.

**View Sample Documentation:** 
- [Generated Documentation](https://deekshith-poojary98.github.io/robotframework-docgen/SingleLibrary/)
- [Dashboard](https://deekshith-poojary98.github.io/robotframework-docgen/)

## 🚀 Features

- **Keyword Extraction**: Automatically extracts keywords from methods decorated with `@keyword`
- **Type Hints Support**: Displays argument types from function signatures
- **Multiple Output Formats**: Generate documentation in HTML or Markdown
- **Multi-Library Support**: Generate documentation for multiple libraries from a single configuration
- **Interactive Dashboard**: Beautiful dashboard UI with library listing, global keyword search, filtering, sorting, and export
- **Live Server**: Built-in web server to serve and preview your dashboard locally
- **Parallel Processing**: Process multiple libraries concurrently for faster generation
- **Markdown Integration**: Full markdown support for docstrings (tables, images, code blocks, lists)
- **Syntax Highlighting**: Custom Robot Framework syntax highlighting with professional color schemes
- **Configuration System**: JSON-based configuration for customizing behavior and metadata
- **Responsive Design**: Mobile-friendly with hamburger menu and theme toggle
- **Multi-Language Support**: Dashboard available in 10 languages with instant translation

## 📦 Installation

```bash
pip install robotframework-libdocgen
```

**Dependencies:** Robot Framework >= 5.0.1, Markdown >= 3.4.0, Pygments >= 2.10.0, Rich >= 13.0.0

## 🔧 CLI Arguments

| Flag | Short | Description | Mode |
|------|-------|-------------|------|
| `--output` | `-o` | Output file path | Single-library only |
| `--format` | `-f` | Output format: `html` (default) or `markdown` | Both |
| `--config` | `-c` | Path to JSON configuration file | Both |
| `--multi-lib` | - | Enable multi-library mode | Multi-library only |
| `--dashboard` | - | Generate interactive dashboard UI | Multi-library only |
| `--serve` | - | Start web server to serve dashboard | Requires `--dashboard` |
| `--host` | - | Server host IP (default: `localhost`) | With `--serve` |
| `--port` | - | Server port number (default: `8000`) | With `--serve` |
| `--parallel` | - | Enable parallel processing | Multi-library only |
| `--workers` | - | Number of parallel workers | With `--parallel` |
| `--dir` | `-d` | Output directory | Both |

## 📝 Quick Start

### Single-Library Mode

```bash
# Generate HTML documentation (default)
docgen your_library.py -o docs.html -c config.json

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
docgen -c multi_lib_config.json --multi-lib

# With custom output directory
docgen -c multi_lib_config.json --multi-lib -d docs

# With parallel processing (faster for many libraries)
docgen -c multi_lib_config.json --multi-lib --parallel

# With custom number of workers
docgen -c multi_lib_config.json --multi-lib --parallel --workers 4
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
docgen -c multi_lib_config.json --dashboard

# Generate and serve dashboard locally
docgen -c multi_lib_config.json --dashboard --serve

# Serve on custom host and port
docgen -c multi_lib_config.json --dashboard --serve --host 0.0.0.0 --port 8080

# Combine with parallel processing
docgen -c multi_lib_config.json --dashboard --parallel --serve
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
  "custom_keywords": ["Custom Keyword 1", "Custom Keyword 2"]
}
```

**Note:** Single-library configs should NOT contain `site` or `libraries` keys.

### Multi-Library Configuration

Requires `site` object (mandatory) and `libraries` array (mandatory):

```json
{
  "site": {
    "github_url": "https://github.com/username/repo",
    "support_email": "support@example.com",
    "author": "Org / Team Name",
    "license": "MIT",
    "robot_framework": ">=7.0",
    "python": ">=3.11"
  },
  "libraries": [
    {
      "name": "Library1",
      "source": "library1.py",
      "output_file": "index.html",
      "output_format": "html",
      "library_url": "https://example.com/library1",
      "custom_keywords": ["Custom Keyword 1"]
    },
    {
      "name": "Library2",
      "source": "library2.py",
      "output_format": "markdown"
    }
  ]
}
```

**Configuration Priority (Multi-Library):**
1. Output filename: `library.output_file` > default (`index.html` or `index.md`)
2. Output format: `library.output_format` > CLI `-f/--format` > default (`html`)
3. Metadata: Library-specific config overrides `site` config

### Configuration Options

- **Metadata**: `author`, `maintainer`, `license`, `robot_framework`, `python`
- **Links**: `github_url` (enables "View on GitHub" and "Open an Issue" buttons), `library_url` (enables "Library Website" button), `support_email` (enables "Contact Support" button)
- **Highlighting**: `custom_keywords` (array of additional keywords to highlight)
- **Dashboard**: `site.name` and `site.description` for dashboard branding

**Note:** In multi-library mode, the `name` field in library entries is optional. If not provided, the class name will be used.

## 📖 Usage

### Keyword Decorator

```python
from robot.api.deco import keyword

class MyLibrary:
    # Custom keyword name
@keyword("Open Application")
    def open_app(self, path: str) -> None:
        """Opens an application at the given path."""
    pass

    # Function name converted to title case (Open Workbook)
@keyword
    def open_workbook(self, file: str) -> None:
        """Opens a workbook file."""
    pass
```

**Important:** Methods without `@keyword` decorator will NOT appear in documentation.

### Markdown in Docstrings

Full markdown support including:
- **Headers**: `# H1`, `## H2`, etc.
- **Text Formatting**: `**bold**`, `*italic*`, `` `code` ``
- **Code Blocks**: Use ` ```robot ` for Robot Framework syntax highlighting
- **Tables**: Standard markdown table syntax
- **Images**: `![alt](url)`
- **Lists**: Bulleted and numbered lists

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

The interactive dashboard provides a comprehensive view of all your libraries with powerful search and filtering capabilities.

### Library Search
- **Real-time filtering**: Type to filter library cards instantly
- **No dropdown results**: Matching libraries are shown directly as cards

### Keyword Search
- **Global search**: Search keywords across all libraries
- **Instant results**: See matching keywords with library names
- **Keyboard navigation**: Use arrow keys to navigate, Enter to open
- **Quick access**: Press `/` to focus the search bar

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

Robot Framework code blocks are automatically highlighted with:
- **Section Headers** (`*** Settings ***`): Blue
- **Keywords**: Teal (bold)
- **Variables** (`${var}`, `@{list}`, `&{dict}`): Light Blue
- **Comments** (`# comment`): Green (italic)
- **Keyword Arguments** (`arg=value`): Yellow/Beige
- **Reserved Control** (`IF`, `FOR`, `TRY`): Orange
- **Settings Keywords** (`Library`, `Resource`): Purple

Keywords are automatically extracted from your library and standard Robot Framework libraries. Add custom keywords via `config.json`.

## ❓ Troubleshooting

### "Successfully parsed 0 keywords"

Ensure all public methods are decorated with `@keyword`:
```python
@keyword("My Keyword")  # ✅ Correct
def my_method(self):
    pass

def helper_method(self):  # ❌ Won't appear
    pass
```

### Multi-library mode errors

- Ensure config contains `libraries` array
- Ensure config contains `site` object (mandatory)
- Use `--multi-lib` flag: `docgen -c config.json --multi-lib`
- Don't use `--multi-lib` with single-library configs
- `--dashboard` automatically enables multi-library mode (no need for `--multi-lib`)

### Dashboard and serve errors

- `--serve` requires `--dashboard` flag: `docgen -c config.json --dashboard --serve`
- Dashboard requires multi-library configuration with `site` and `libraries` keys
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

Add type hints to function signatures:
```python
@keyword
def my_keyword(self, arg1: str, arg2: int = 10) -> bool:
    """Keyword documentation."""
    pass
```

If type hints are not provided, arguments show as `Any` type.

## 📚 Examples

- **Sample Library**: See `sample_libs/` directory for comprehensive examples
- **Multi-Library Config**: See `multi_lib_config.json` for configuration structure

**Single Library:**
```bash
docgen sample_libs/string_utils.py -f html -o sample_docs.html -c config.json
```

**Multi-Library with Dashboard:**
```bash
# Generate dashboard
docgen -c multi_lib_config.json --dashboard

# Generate and serve dashboard
docgen -c multi_lib_config.json --dashboard --serve

# With parallel processing
docgen -c multi_lib_config.json --dashboard --parallel --serve --port 8080
```

## 📄 License

Apache License 2.0 - See [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 🔗 Links

- **Repository**: [GitHub](https://github.com/deekshith-poojary98/robotframework-docgen)
- **Live Demo**: [Sample Documentation](https://deekshith-poojary98.github.io/robotframework-docgen/)
