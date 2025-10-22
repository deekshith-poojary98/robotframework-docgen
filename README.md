# robotframework-docgen

A powerful documentation generator for Robot Framework libraries that extracts keywords, arguments, and docstrings to create clean, well-formatted docs in HTML or Markdown with advanced custom syntax support.

## 🚀 Features

### Core Functionality
- **Keyword Extraction**: Automatically extracts keywords, arguments, and docstrings from Robot Framework libraries
- **Multiple Output Formats**: Generate documentation in HTML or Markdown
- **Custom Syntax Support**: Rich markdown-like syntax for professional documentation
- **Syntax Highlighting**: Custom Robot Framework syntax highlighting with professional color schemes
- **Configuration System**: JSON-based configuration for customizing behavior

### Important Notes
- **@keyword Decorator Required**: Only methods decorated with `@keyword("Keyword Name")` will be included in the documentation
- **Undecorated Methods Ignored**: Methods without the `@keyword` decorator are automatically excluded
- **Custom Keyword Names**: The decorator allows you to specify custom keyword names that differ from the method name

### Advanced Documentation Features
- **Rich Text Formatting**: Bold, italic, underlined, strikethrough text
- **Structured Content**: Headers, tables, code blocks, horizontal rules
- **Code Highlighting**: Syntax-highlighted code blocks with language support
- **Professional Styling**: Theme-aware CSS with Robot Framework integration
- **Responsive Design**: Mobile and desktop friendly output

## 📖 Custom Documentation Syntax

### Supported Features

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

++Underlined Text++
```markdown
++underlined text++
```

~~Strikethrough Text~~
```markdown
~~strikethrough text~~
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
***** Settings *****
Library         MyLibrary

***** Test Cases *****
Example
    My Keyword    ${variable}
```


Supported languages:
- `robot` - Robot Framework syntax (custom highlighter)
- All Pygments-supported languages including:
  - `python` - Python code
  - `javascript` - JavaScript code
  - `java` - Java code
  - `c` - C code
  - `cpp` - C++ code
  - `html` - HTML markup
  - `css` - CSS styles
  - `sql` - SQL queries
  - `bash` - Bash shell scripts
  - `yaml` - YAML configuration
  - `json` - JSON data
  - `xml` - XML markup
  - `go` - Go language
  - `rust` - Rust code
  - `php` - PHP code
  - `ruby` - Ruby code
  - `swift` - Swift code
  - `kotlin` - Kotlin code
  - `scala` - Scala code
  - `r` - R language
  - `matlab` - MATLAB code
  - `lua` - Lua code
  - `perl` - Perl code
  - `powershell` - PowerShell scripts
  - `dockerfile` - Docker files
  - `ini` - INI configuration
  - `toml` - TOML configuration
  - `text` - Plain text (default)
  - And many more...

#### 5. Tables
Create structured tables:

```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| **Bold** | *Italic* | `Code` |
| Data 1   | Data 2   | Data 3   |
```

#### 6. Horizontal Rules
Create visual separators:

```markdown
---
***
```

## 🎨 Custom Robot Framework Syntax Highlighting

### Color Scheme

| Element | Color | Hex Code | Description |
|---------|-------|----------|-------------|
| **Section Headers** | Blue | `#569cd6` | `*** Settings ***`, `*** Test Cases ***` |
| **Keywords** | Teal | `#4ec9b0` | Robot Framework keywords |
| **Variables** | Light Blue | `#9cdcfe` | `${variable}`, `@{list}`, `&{dict}` |
| **Comments** | Green | `#6a9955` | `# comment` with italic |
| **Strings** | Orange | `#ce9178` | `"quoted text"` |
| **Numbers** | Light Green | `#b5cea8` | `123`, `45.67` |
| **Settings** | Purple | `#c586c0` | `Library`, `Resource`, `Documentation` |
| **Test Cases** | Yellow | `#dcdcaa` | Test case names |

### Features
- **Section Headers**: `*** Settings ***`, `*** Test Cases ***`, `*** Keywords ***`, `*** Variables ***`
- **Keywords**: Robot Framework keywords with bold formatting
- **Variables**: `${variable}`, `@{list}`, `&{dict}` with light blue highlighting
- **Comments**: Green italic comments
- **Strings**: Orange quoted text
- **Settings**: Purple Library, Resource, Documentation keywords
- **Test Cases**: Yellow test case names

## ⚙️ Configuration System

### Usage

```bash
python src/docgen.py src/PywinautoLibrary.py -f html -o output.html -c config.json
```

### Basic Configuration

```json
{
  "custom_keywords": [
    "Open Application",
    "Close Application",
    "Kill Application",
    "Connect to Application",
    "Get Process ID",
    "Wait for Process Exit"
  ]
}
```

### Advanced Configuration

```json
{
  "custom_keywords": [
    "Open Application",
    "Close Application",
    "Kill Application",
    "Connect to Application",
    "Get Process ID",
    "Wait for Process Exit",
    "Custom Keyword 1",
    "Custom Keyword 2"
  ],
  "description": "Configuration file for Robot Framework documentation parser",
  "version": "1.0.0"
}
```

### Configuration Options

#### Required
- `custom_keywords`: Array of custom keywords to highlight (strings)

#### Optional
- `description`: Description of the configuration file
- `version`: Configuration file version

### Examples

#### Minimal Configuration
```json
{
  "custom_keywords": ["My Custom Keyword"]
}
```

#### Full Configuration
```json
{
  "custom_keywords": [
    "Open Application",
    "Close Application",
    "Custom Keyword"
  ],
  "description": "My custom configuration",
  "version": "1.0.0"
}
```


## 📝 Complete Example

### Before (Standard Robot Framework)
```python
@keyword("Open Application")
def open_application(self, app_path: str) -> None:
    """
    The ``Open Application`` keyword starts a new application instance.
    
    = Example =
    
    | ***** Settings *****
    | Library         PywinautoLibrary
    |
    | ***** Test Cases *****
    | Example
    |     Open Application    ${app_path}
    """
```

### Important: @keyword Decorator Required
```python
# ✅ This will be included in documentation
@keyword("Open Application")
def open_application(self, app_path: str) -> None:
    """Documentation here..."""
    pass

# ❌ This will be IGNORED (no @keyword decorator)
def helper_method(self, data: str) -> str:
    """This method won't appear in documentation"""
    return data.upper()

# ❌ This will be IGNORED (no keyword name specified)
@keyword
def my_method(self, param: str) -> str:
    """This method won't appear in documentation"""
    return param

# ✅ This will be included with custom name
@keyword("Close Application")
def close_app(self, pid: str) -> bool:
    """Documentation here..."""
    pass
```

### After (Our Custom Syntax)
```python
@keyword("Open Application")
def open_application(self, app_path: str) -> None:
    """
    The **Open Application** keyword starts a new application instance.
    
    ## Example
    
    ```robot
    *** Settings ***
    Library         PywinautoLibrary
    
    *** Test Cases ***
    Example
        Open Application    ${app_path}
        ${process_id}       Get Process ID
        Close Application
    ```
    """
```

## 🎯 Benefits

### For Developers
- **Rich documentation** with professional formatting
- **Easy to write** using familiar markdown-like syntax
- **Consistent styling** across all documentation
- **Better readability** with headers, tables, and code blocks

### For Users
- **Professional appearance** matching Robot Framework standards
- **Interactive features** like search and theme toggle
- **Mobile-friendly** responsive design
- **Accessible** with proper HTML structure

### For Teams
- **Standardized format** for all library documentation
- **Easy maintenance** with clear syntax rules
- **Version control friendly** with readable source format
- **Extensible** design for future enhancements

## 🔮 Future Enhancements

### Potential Additions
- **Image support** with `![alt](url)` syntax
- **Collapsible sections** for large documentation
- **Interactive examples** with runnable code
- **Cross-references** between keywords
- **Export options** for PDF, Word, etc.

### Advanced Features
- **Mathematical expressions** with LaTeX support
- **Diagram generation** from text descriptions
- **API documentation** auto-generation
- **Multi-language support** for international teams

## 🎊 Conclusion

We've successfully created a **next-generation documentation system** for Robot Framework libraries that:

- ✅ **Maintains compatibility** with existing Robot Framework standards
- ✅ **Adds powerful formatting** capabilities
- ✅ **Provides professional output** with modern styling
- ✅ **Supports all requested features** (tables, headers, code blocks, formatting)
- ✅ **Is easy to use** with familiar markdown-like syntax
- ✅ **Is fully functional** and ready for production use

This custom syntax format transforms Robot Framework library documentation from basic text to **rich, professional documentation** that rivals the best API documentation systems available today! 🚀

## 📁 Project Structure

```
robotframework-docgen/
├── src/
│   └── docgen.py          # Enhanced parser with custom syntax support
├── config.json                # Configuration file
├── example_config.json        # Example configuration
├── README.md                  # This file
└── LICENSE                    # License file
```

## 🚀 Getting Started

1. **Install dependencies** (if any)
2. **Create a configuration file** (optional)
3. **Run the parser**:
   ```bash
   python src/docgen.py your_library.py -f html -o output.html -c config.json
   ```

## 📄 License

See [LICENSE](LICENSE) file for details.
