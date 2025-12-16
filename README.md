# robotframework-docgen

A powerful documentation generator for Robot Framework libraries that extracts keywords, arguments, and docstrings to create professional, well-formatted HTML documentation with advanced markdown support and syntax highlighting.

See the generated documentation in action: **[View Sample Documentation](https://deekshith-poojary98.github.io/robotframework-docgen/)**


## 🚀 Features

### Core Functionality
- **Keyword Extraction**: Automatically extracts keywords from methods decorated with `@keyword`
- **Type Hints Support**: Displays argument types from function signatures
- **Multiple Output Formats**: Generate documentation in HTML or Markdown
- **Markdown Integration**: Full markdown support for docstrings with tables, images, code blocks, and more
- **Syntax Highlighting**: Custom Robot Framework syntax highlighting with professional color schemes
- **Configuration System**: JSON-based configuration for customizing behavior and metadata

### Documentation Features
- **Rich Text Formatting**: Bold, italic, underlined, strikethrough text
- **Structured Content**: Headers, tables, code blocks, horizontal rules
- **Code Highlighting**: Syntax-highlighted code blocks for Robot Framework, Python, JavaScript, and 100+ languages via Pygments
- **Images**: Support for markdown image syntax `![alt](url)`
- **Tables**: Full markdown table support with professional styling
- **Professional Styling**: Theme-aware CSS with Robot Framework integration
- **Responsive Design**: Mobile and desktop friendly with hamburger menu for smaller screens

### Advanced Syntax Highlighting
- **Robot Framework Keywords**: Automatically extracted from your library and standard Robot Framework libraries
- **Variables**: `${variable}`, `@{list}`, `&{dict}` highlighting
- **Keyword Arguments**: `arg=value` highlighting in yellow/beige
- **Comments**: Green italic comments (both full-line and inline)
- **Reserved Control Keywords**: `IF`, `FOR`, `TRY`, `WHILE`, etc. in orange
- **Settings Keywords**: `Library`, `Resource`, `Documentation`, etc. in purple
- **Section Headers**: `*** Settings ***`, `*** Test Cases ***` in blue

## 📖 Documentation Syntax

### Supported Markdown Features

#### 1. Headers
Create hierarchical headers using `#` symbols:

```markdown
# Main Title
## Section Title
### Subsection Title
#### Sub-subsection Title
##### Level 5 Header
###### Level 6 Header
```

#### 2. Text Formatting

**Bold Text**
```markdown
**bold text** or __bold text__
```

*Italic Text*
```markdown
*italic text* or _italic text_
```

`Inline Code`
```markdown
`code snippet`
```

#### 3. Links
Create clickable links:

```markdown
[Link Text](https://example.com)
```

#### 4. Code Blocks
Create syntax-highlighted code blocks:

```robot
*** Settings ***
Library    MyLibrary

*** Test Cases ***
Example
    My Keyword    ${variable}    arg=value
    # This is a comment
```

Supported languages:
- `robot` - Robot Framework syntax (custom highlighter with full syntax support)
- All Pygments-supported languages including:
  - `python`, `javascript`, `java`, `c`, `cpp`, `html`, `css`, `sql`, `bash`, `yaml`, `json`, `xml`, `go`, `rust`, `php`, `ruby`, `swift`, `kotlin`, and many more...

#### 5. Tables
Create structured tables with full markdown support:

```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| **Bold** | *Italic* | `Code` |
| Data 1   | Data 2   | Data 3   |
```

#### 6. Images
Include images in your documentation:

```markdown
![Alt Text](https://example.com/image.png)
```

#### 7. Lists
Create bulleted and numbered lists:

```markdown
- Item 1
- Item 2
  - Nested item
- Item 3

1. First step
2. Second step
3. Third step
```

## 🎨 Robot Framework Syntax Highlighting

### Color Scheme

| Element | Color | Hex Code | Description |
|---------|-------|----------|-------------|
| **Section Headers** | Blue | `#569cd6` | `*** Settings ***`, `*** Test Cases ***` |
| **Keywords** | Teal | `#4ec9b0` | Robot Framework keywords (bold) |
| **Variables** | Light Blue | `#9cdcfe` | `${variable}`, `@{list}`, `&{dict}` |
| **Comments** | Green | `#6a9955` | `# comment` (italic) |
| **Keyword Arguments** | Yellow/Beige | `#dcdcaa` | `arg=value` |
| **Reserved Control** | Orange | `#ce9178` | `IF`, `FOR`, `TRY`, `WHILE`, etc. |
| **Settings Keywords** | Purple | `#c586c0` | `Library`, `Resource`, `Documentation` |
| **Test Cases** | Yellow | `#dcdcaa` | Test case names (bold) |

### Highlighting Features
- **Automatic Keyword Detection**: Keywords are automatically extracted from your library and standard Robot Framework libraries
- **Custom Keywords**: Add additional keywords via `config.json` for highlighting
- **Multi-word Keywords**: Properly highlights keywords like "Create Dictionary", "Should Be Equal"
- **Variable Highlighting**: All Robot Framework variable types are highlighted
- **Inline Comments**: Comments at the end of lines are highlighted in green

## ⚙️ Configuration System

### Usage

```bash
python src/docgen.py your_library.py -f html -o output.html -c config.json
```

### Configuration File (`config.json`)

All fields are optional. Only provide the fields you want to display:

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
  "custom_keywords": [
    "Custom Keyword 1",
    "Custom Keyword 2"
  ]
}
```

### Configuration Options

#### Library Metadata (Optional)
- `author`: Library author name
- `maintainer`: Library maintainer name
- `license`: License information
- `robot_framework`: Required Robot Framework version
- `python`: Required Python version

#### Links (Optional)
- `github_url`: GitHub repository URL (enables "View on GitHub" and "Open an Issue" buttons)
- `library_url`: Library website URL (enables "Library Website" button)
- `support_email`: Support email address (enables "Contact Support" button)

#### Highlighting (Optional)
- `custom_keywords`: Array of additional keywords to highlight in code blocks

### Dynamic Display
- Buttons and metadata are only displayed if the corresponding fields are provided in `config.json`
- If `github_url` is not provided, the "Open an Issue on GitHub" button won't appear
- If `support_email` is not provided, the "Contact Support" button won't appear
- Metadata fields are only shown if they have values

## 📝 Usage Examples

### Basic Usage

```bash
# Generate HTML documentation (default format)
docgen your_library.py -o docs.html -c config.json

# Generate Markdown documentation
docgen your_library.py -f markdown -o docs.md -c config.json

# Generate with default output filename (your_library.html)
docgen your_library.py -c config.json

# Generate without config file
docgen your_library.py
```

### Keyword Decorator Usage

#### ✅ Correct Usage

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

#### ❌ Incorrect Usage

```python
# This will NOT appear in documentation (no @keyword decorator)
def helper_method(self, data: str) -> str:
    """This method won't appear in documentation"""
    return data.upper()
```

### Complete Example

```python
from robot.api.deco import keyword
from typing import Dict, List

class DataProcessor:
    @keyword
    def process_data(self, data: Dict[str, any], options: List[str] = None) -> Dict[str, any]:
        """
        Process data with optional configuration.
        
        This keyword processes the provided data dictionary and returns
        a processed result based on the given options.
        
        **Arguments:**
        - `data`: Dictionary containing data to process
        - `options`: Optional list of processing options
        
        **Returns:** Processed dictionary with results.
        
        **Example:**
        ```robot
        *** Settings ***
        Library    DataProcessor
        
        *** Test Cases ***
        Process Example
            ${data}=    Create Dictionary    name=John    age=30
            ${result}=    Process Data    ${data}    options=['option1', 'option2']
        ```
        
        **Options:**
        | Option | Description |
        |--------|-------------|
        | `validate` | Validate input data |
        | `transform` | Transform data structure |
        | `filter` | Filter data entries |
        """
        # Implementation here
        return {}
```

## 🎯 Key Features

### For Developers
- **Rich documentation** with professional formatting
- **Easy to write** using standard markdown syntax
- **Type hints support** - automatically displays argument types
- **Automatic keyword extraction** - no need to manually list keywords
- **Function name conversion** - `my_keyword` becomes "My Keyword" automatically
- **Consistent styling** across all documentation
- **Better readability** with headers, tables, code blocks, and images

### For Users
- **Professional appearance** matching Robot Framework standards
- **Interactive features** like search and theme toggle
- **Mobile-friendly** responsive design with hamburger menu
- **Accessible** with proper HTML structure
- **Syntax highlighting** for better code readability
- **Dynamic metadata** display based on configuration

### For Teams
- **Standardized format** for all library documentation
- **Easy maintenance** with clear syntax rules
- **Version control friendly** with readable source format
- **Extensible** design for future enhancements
- **Configuration-driven** customization

## 🔧 Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Install from PyPI (Recommended)

The easiest way to install `robotframework-libdocgen` is using pip:

```bash
pip install robotframework-libdocgen
```

This will automatically install all required dependencies:
- Robot Framework >= 5.0.1
- Markdown >= 3.4.0
- Pygments >= 2.10.0
- Rich >= 13.0.0

### Verify Installation

After installation, verify that the CLI commands are available:

```bash
# Check if the command is available
docgen --help

# Or using the full command name
robotframework-libdocgen --help
```

You should see the help message with usage instructions.

### Install from Source

If you want to install from the source code or contribute to the project:

```bash
# Clone the repository
git clone https://github.com/deekshith-poojary98/robotframework-docgen.git
cd robotframework-docgen

# Install in development mode (recommended for development)
pip install -e .

# Or install directly
pip install .
```

**Development Mode (`-e` flag):**
- Installs the package in "editable" mode
- Changes to source code are immediately reflected
- Useful when developing or modifying the package

### Upgrade Installation

To upgrade to the latest version:

```bash
pip install --upgrade robotframework-libdocgen
```

### Uninstall

To uninstall the package:

```bash
pip uninstall robotframework-libdocgen
```

## 📁 Project Structure

```
robotframework-docgen/
├── robotframework_docgen/     # Main package
│   ├── __init__.py           # Package initialization
│   ├── parser.py              # Parser module (RobotFrameworkDocParser)
│   ├── generator.py           # Generator module (DocumentationGenerator)
│   ├── cli.py                 # CLI entry point
│   └── templates/
│       └── libdoc.html        # HTML template
├── config.json                # Configuration file (optional)
├── example_config.json        # Example configuration
├── pyproject.toml             # Package configuration
├── MANIFEST.in                # Package manifest
├── README.md                  # This file
└── LICENSE                    # License file
```

## 🚀 Getting Started

### Quick Start

1. **Install the package**:
   ```bash
   pip install robotframework-libdocgen
   ```

2. **Create a configuration file** (optional):
   Create a `config.json` file with your library metadata:
   ```json
   {
     "github_url": "https://github.com/username/repo",
     "library_url": "https://example.com/library",
     "support_email": "support@example.com",
     "author": "Your Name",
     "maintainer": "Maintainer Name",
     "license": "Apache-2.0",
     "robot_framework": ">=7.0",
     "python": ">=3.8",
     "custom_keywords": ["Custom Keyword 1", "Custom Keyword 2"]
   }
   ```

3. **Generate documentation**:
   ```bash
   # Generate HTML documentation (default)
   docgen your_library.py -o docs.html -c config.json

   # Generate Markdown documentation
   docgen your_library.py -f markdown -o README.md -c config.json

   # Generate with default settings (HTML format, no config)
   docgen your_library.py
   ```

4. **View the documentation**:
   - Open the generated HTML file in your browser
   - Or view the Markdown file in your editor/README viewer

### Example

```bash
# Install
pip install robotframework-libdocgen

# Generate docs for your library
docgen sample_library.py -o documentation.html -c config.json

# Open in browser (macOS)
open documentation.html

# Or on Linux
xdg-open documentation.html

# Or on Windows
start documentation.html
```

## 🎨 UI Features

### Responsive Design
- **Desktop**: Full sidebar navigation with keyword list
- **Tablet/Mobile**: Hamburger menu for sidebar access
- **Search**: Real-time keyword search functionality
- **Theme Toggle**: Switch between light and dark themes

### Dynamic Content
- **Metadata Display**: Author, maintainer, license, versions (only if provided)
- **Action Buttons**: GitHub, library website, contact support (only if URLs/email provided)
- **Last Updated**: Automatic timestamp in footer
- **Keyword Count**: Dynamic count of extracted keywords

## 📄 License

See [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📚 Examples

Check out the `sample_library.py` file for a comprehensive example demonstrating all features:
- Multiple keyword types
- Type hints
- Markdown tables
- Code blocks in multiple languages
- Images
- Lists and formatting
- Complex documentation structures

Generate documentation for it:
```bash
python src/docgen.py sample_library.py -f html -o sample_docs.html -c config.json
```
