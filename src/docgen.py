#!/usr/bin/env python3
"""
Documentation Parser for Robot Framework Libraries

This parser reads Python files containing Robot Framework library classes
and generates comprehensive documentation from their docstrings.
"""

import ast
import re
import argparse
import json
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, TextLexer
    from pygments.formatters import HtmlFormatter
    from pygments.util import ClassNotFound

    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False


@dataclass
class KeywordInfo:
    """Information about a Robot Framework keyword."""

    name: str
    description: str
    example: str
    parameters: List[str]
    return_type: str
    line_number: int


@dataclass
class LibraryInfo:
    """Information about a Robot Framework library."""

    name: str
    version: str
    scope: str
    description: str
    keywords: List[KeywordInfo]


class RobotFrameworkDocParser:
    """Parser for Robot Framework library documentation."""

    def __init__(self, config: dict = None):
        self.library_info = None
        self._cached_keywords = None
        self.config = config

    def parse_file(self, file_path: str) -> LibraryInfo:
        """Parse a Python file and extract library information."""
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        tree = ast.parse(content)

        # Try to execute the module to get actual values
        module_globals = self._execute_module_safely(file_path)

        return self._extract_library_info(tree, file_path, module_globals)

    def _execute_module_safely(self, file_path: str) -> dict:
        """Safely execute the module to get actual values."""
        try:
            import sys
            import importlib.util
            import os

            # Add the directory containing the file to the path
            file_dir = os.path.dirname(os.path.abspath(file_path))
            if file_dir not in sys.path:
                sys.path.insert(0, file_dir)

            # Create a new module
            spec = importlib.util.spec_from_file_location("temp_module", file_path)
            if spec is None or spec.loader is None:
                return {}

            module = importlib.util.module_from_spec(spec)

            # Execute the module in a controlled environment
            spec.loader.exec_module(module)

            # Extract all module-level variables that might be referenced
            result = {}
            for attr_name in dir(module):
                if not attr_name.startswith('_'):  # Skip private attributes
                    try:
                        attr_value = getattr(module, attr_name)
                        if not callable(attr_value):  # Only get non-callable attributes
                            result[attr_name] = str(attr_value)
                    except Exception:
                        continue

            return result

        except Exception as e:
            print(f"Warning: Could not execute module {file_path}: {e}")
            return {}

    def _extract_library_info(
        self, tree: ast.AST, file_path: str, module_globals: dict = None
    ) -> LibraryInfo:
        """Extract library information from AST."""
        if module_globals is None:
            module_globals = {}

        # First, extract module-level variables
        module_vars = self._extract_module_variables(tree)

        # Merge with executed module globals
        module_vars.update(module_globals)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if this class has Robot Framework decorators
                if self._is_robot_library_class(node):
                    return self._parse_library_class(node, module_vars)

        # If no Robot Framework library class found, create a library info from filename
        filename = Path(file_path).stem
        return LibraryInfo(
            name=filename,
            version=self._get_module_attribute("ROBOT_LIBRARY_VERSION", module_vars, "Unknown"),
            scope=self._get_module_attribute("ROBOT_LIBRARY_SCOPE", module_vars, "TEST"),
            description=self._get_module_docstring(tree),
            keywords=self._extract_module_keywords(tree)
        )

    def _extract_module_variables(self, tree: ast.AST) -> dict:
        """Extract module-level variable assignments."""
        module_vars = {}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if isinstance(node.value, ast.Constant):
                            module_vars[target.id] = str(node.value.value)
                        elif hasattr(ast, "Str") and isinstance(
                            node.value, ast.Str
                        ):  # For Python < 3.8 compatibility
                            module_vars[target.id] = str(node.value.s)
        return module_vars

    def _is_robot_library_class(self, class_node: ast.ClassDef) -> bool:
        """Check if a class is a Robot Framework library."""
        # Look for @keyword decorators in methods
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and isinstance(
                        decorator.func, ast.Name
                    ):
                        if decorator.func.id == "keyword":
                            return True
        return False

    def _parse_library_class(
        self, class_node: ast.ClassDef, module_vars: dict = None
    ) -> LibraryInfo:
        """Parse a Robot Framework library class."""
        if module_vars is None:
            module_vars = {}

        # Extract class attributes
        version = self._get_class_attribute(
            class_node, "ROBOT_LIBRARY_VERSION", "Unknown", module_vars
        )
        scope = self._get_class_attribute(
            class_node, "ROBOT_LIBRARY_SCOPE", "TEST", module_vars
        )

        # If the attribute references a module variable, resolve it
        if version in module_vars:
            version = module_vars[version]
        if scope in module_vars:
            scope = module_vars[scope]

        description = self._get_class_docstring(class_node)

        # Extract keywords
        keywords = []
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                keyword_info = self._parse_keyword_function(node)
                if keyword_info:
                    keywords.append(keyword_info)

        return LibraryInfo(
            name=class_node.name,
            version=version,
            scope=scope,
            description=description,
            keywords=keywords,
        )

    def _get_class_attribute(
        self,
        class_node: ast.ClassDef,
        attr_name: str,
        default: str,
        module_vars: dict = None,
    ) -> str:
        """Get a class attribute value."""
        if module_vars is None:
            module_vars = {}

        for node in class_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == attr_name:
                        if isinstance(node.value, ast.Constant):
                            return str(node.value.value)
                        elif isinstance(node.value, ast.Name):
                            # Handle variable references like __version__
                            if node.value.id in module_vars:
                                return module_vars[node.value.id]
                            return str(node.value.id)
                        elif isinstance(node.value, ast.Call):
                            # Handle function calls like get_version()
                            return self._execute_function_call(node.value, module_vars)
                        elif hasattr(ast, "Str") and isinstance(
                            node.value, ast.Str
                        ):  # For Python < 3.8 compatibility
                            return str(node.value.s)
        return default

    def _execute_function_call(self, call_node: ast.Call, module_vars: dict) -> str:
        """Execute a function call safely to get the return value."""
        try:
            # Get the function name
            if isinstance(call_node.func, ast.Name):
                func_name = call_node.func.id

                # Handle version variable references
                if func_name in ["__version__", "version"]:
                    return module_vars.get(func_name, "Unknown")
                else:
                    # Try to execute any function
                    return self._find_and_execute_function(func_name, module_vars)
            else:
                return "Unknown"
        except Exception as e:
            print(f"Warning: Could not execute function call: {e}")
            return "Unknown"

    def _find_and_execute_function(self, func_name: str, module_vars: dict) -> str:
        """Find and execute a function by name."""
        try:
            # Check if we have the function result from module execution
            if func_name in module_vars:
                return str(module_vars[func_name])

            return "Unknown"
        except Exception as e:
            print(f"Warning: Could not execute function {func_name}: {e}")
            return "Unknown"

    def _get_class_docstring(self, class_node: ast.ClassDef) -> str:
        """Get the class docstring."""
        if (
            class_node.body
            and isinstance(class_node.body[0], ast.Expr)
            and isinstance(class_node.body[0].value, ast.Constant)
        ):
            return class_node.body[0].value.value
        return ""

    def _parse_keyword_function(
        self, func_node: ast.FunctionDef
    ) -> Optional[KeywordInfo]:
        """Parse a function to extract keyword information."""
        # Check if function has @keyword decorator
        keyword_name = None
        for decorator in func_node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                if decorator.func.id == "keyword":
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        keyword_name = decorator.args[0].value
                    else:
                        keyword_name = func_node.name

        if not keyword_name:
            return None

        # Parse docstring
        docstring = ast.get_docstring(func_node) or ""
        description, example = self._parse_docstring(docstring, self.config)

        # Extract parameters
        parameters = [arg.arg for arg in func_node.args.args if arg.arg != "self"]

        # Extract return type
        return_type = "None"
        if func_node.returns:
            if isinstance(func_node.returns, ast.Name):
                return_type = func_node.returns.id
            elif isinstance(func_node.returns, ast.Constant):
                return_type = func_node.returns.value

        return KeywordInfo(
            name=keyword_name,
            description=description,
            example=example,
            parameters=parameters,
            return_type=return_type,
            line_number=func_node.lineno,
        )

    def _parse_docstring(self, docstring: str, config: dict = None) -> Tuple[str, str]:
        """Parse docstring using our custom syntax format."""
        if not docstring:
            return "", ""

        # Parse the custom syntax and convert to HTML
        parsed_content = self._parse_custom_syntax(docstring, config)

        # For now, return the parsed content as description
        # In the future, we could separate examples from descriptions
        return parsed_content, ""

    def _parse_custom_syntax(self, content: str, config: dict = None) -> str:
        """Parse our custom documentation syntax and convert to HTML."""
        if not content:
            return ""

        lines = content.strip().split("\n")
        html_lines = []
        in_code_block = False
        in_table = False
        in_list = False
        just_finished_table = False
        table_lines = []
        prev_line_was_content = False
        prev_content_type = None  # Track type of previous content
        current_language = "text"

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            # Code blocks
            if line.startswith("```"):
                if in_code_block:
                    # End code block
                    html_lines.append("</pre></div>")
                    in_code_block = False
                else:
                    # Start code block
                    current_language = line[3:].strip() or "text"
                    html_lines.append(
                        f'<div class="code-block"><pre class="language-{current_language}">'
                    )
                    in_code_block = True
                i += 1
                continue

            if in_code_block:
                # Use Pygments for syntax highlighting if available
                if PYGMENTS_AVAILABLE:
                    # Collect all code lines in this block
                    code_lines = []
                    j = i
                    while j < len(lines) and not lines[j].startswith("```"):
                        code_lines.append(lines[j])
                        j += 1

                    # Highlight the entire code block
                    code_content = "\n".join(code_lines)
                    highlighted_code = self._highlight_with_pygments(
                        code_content, current_language, config
                    )
                    html_lines.append(highlighted_code)

                    # Skip to the end of the code block
                    i = j
                    continue
                else:
                    # Fallback to custom highlighting
                    if current_language == "robot":
                        highlighted_line = self._highlight_robot_syntax(line)
                        html_lines.append(highlighted_line)
                    else:
                        html_lines.append(self._escape_html(line))
                i += 1
                continue

            # Tables
            if line.startswith("|") and "|" in line[1:]:
                if not in_table:
                    in_table = True
                    table_lines = []
                table_lines.append(line)
                i += 1
                continue
            elif in_table:
                # End table
                html_lines.append(self._render_table(table_lines))
                in_table = False
                just_finished_table = True
                table_lines = []
                # Continue processing this line (don't skip it)

            # Headers (handle with leading whitespace)
            stripped_line = line.strip()
            if stripped_line.startswith("# "):
                # Close list if we were in one
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<h1>{self._parse_inline_formatting(stripped_line[2:])}</h1>")
                prev_line_was_content = True
                prev_content_type = "header"
                i += 1
                continue
            elif stripped_line.startswith("## "):
                # Close list if we were in one
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<h2>{self._parse_inline_formatting(stripped_line[3:])}</h2>")
                prev_line_was_content = True
                prev_content_type = "header"
                i += 1
                continue
            elif stripped_line.startswith("### "):
                # Close list if we were in one
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<h3>{self._parse_inline_formatting(stripped_line[4:])}</h3>")
                prev_line_was_content = True
                prev_content_type = "header"
                i += 1
                continue
            elif stripped_line.startswith("#### "):
                # Close list if we were in one
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<h4>{self._parse_inline_formatting(stripped_line[5:])}</h4>")
                prev_line_was_content = True
                prev_content_type = "header"
                i += 1
                continue
            elif stripped_line.startswith("##### "):
                # Close list if we were in one
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<h5>{self._parse_inline_formatting(stripped_line[6:])}</h5>")
                prev_line_was_content = True
                prev_content_type = "header"
                i += 1
                continue
            elif stripped_line.startswith("###### "):
                # Close list if we were in one
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<h6>{self._parse_inline_formatting(stripped_line[7:])}</h6>")
                prev_line_was_content = True
                prev_content_type = "header"
                i += 1
                continue
            # Horizontal rule
            elif line.startswith("---") or line.startswith("***"):
                html_lines.append("<hr>")
                i += 1
                continue
            # Bullet lists
            elif line.strip().startswith("- "):
                # Start or continue a list
                if not in_list:
                    in_list = True
                    html_lines.append("<ul>")
                html_lines.append(f"<li>{self._parse_inline_formatting(line.strip()[2:])}</li>")
                prev_line_was_content = True
                i += 1
                continue
            # Empty line - only add br if previous line was content and next line is not a code block
            elif not line.strip():
                # Don't add <br> if we're inside a list, table, just finished a table, or if previous content was a paragraph
                if not in_list and not in_table and not just_finished_table and prev_content_type != "paragraph":
                    # Check if next non-empty line is a code block
                    next_non_empty = None
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip():
                            next_non_empty = lines[j]
                            break

                    # Only add <br> if previous line was content and next line is not a code block
                    if prev_line_was_content and (
                        not next_non_empty or not next_non_empty.startswith("```")
                    ):
                        html_lines.append("<br>")
                prev_line_was_content = False
                prev_content_type = None
                just_finished_table = False
                i += 1
                continue
            # Regular paragraph
            else:
                # Close list if we were in one
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                
                if line.strip():
                    html_lines.append(f"<p>{self._parse_inline_formatting(line)}</p>")
                    prev_line_was_content = True
                    prev_content_type = "paragraph"
                    just_finished_table = False
                i += 1

        # Close any open blocks
        if in_code_block:
            html_lines.append("</pre></div>")
        if in_table:
            html_lines.append(self._render_table(table_lines))
        if in_list:
            html_lines.append("</ul>")

        return "\n".join(html_lines)

    def _parse_inline_formatting(self, text: str) -> str:
        """Parse inline formatting like bold, italic, links, etc."""
        if not text:
            return ""

        # Escape HTML first
        text = self._escape_html(text)

        # Bold: **text** or __text__
        text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"__(.*?)__", r"<strong>\1</strong>", text)

        # Italic: *text* or _text_
        text = re.sub(r"\*(.*?)\*", r"<em>\1</em>", text)
        text = re.sub(r"_(.*?)_", r"<em>\1</em>", text)

        # Underline: ++text++
        text = re.sub(r"\+\+(.*?)\+\+", r"<u>\1</u>", text)

        # Strikethrough: ~~text~~
        text = re.sub(r"~~(.*?)~~", r"<del>\1</del>", text)

        # Inline code: `text`
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

        # Links: [text](url)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)

        return text

    def _render_table(self, table_lines: List[str]) -> str:
        """Render a table from markdown-style table lines."""
        if not table_lines:
            return ""

        html_lines = ['<table class="doc-table">']

        for i, line in enumerate(table_lines):
            # Skip separator lines (like |---|---|)
            if re.match(r"^\|[\s\-\|]+\|$", line):
                continue

            # Parse table row
            cells = [
                cell.strip() for cell in line.split("|")[1:-1]
            ]  # Remove empty first/last

            if i == 0:
                # Header row
                html_lines.append("<thead><tr>")
                for cell in cells:
                    html_lines.append(f"<th>{self._parse_inline_formatting(cell)}</th>")
                html_lines.append("</tr></thead><tbody>")
            else:
                # Data row
                html_lines.append("<tr>")
                for cell in cells:
                    html_lines.append(f"<td>{self._parse_inline_formatting(cell)}</td>")
                html_lines.append("</tr>")

        html_lines.append("</tbody></table>")
        return "\n".join(html_lines)

    def _highlight_with_pygments(self, code: str, language: str, config: dict = None) -> str:
        """Use Pygments to highlight code with proper syntax highlighting."""
        if not PYGMENTS_AVAILABLE:
            return self._escape_html(code)

        # Use custom Robot Framework highlighting
        if language == "robot":
            return self._highlight_robot_framework(code, config)

        try:
            # Try to get the appropriate lexer for other languages
            lexer = get_lexer_by_name(language, stripall=True)
        except ClassNotFound:
            # Fallback to text lexer if language not supported
            lexer = TextLexer()

        # Create HTML formatter with inline styles
        formatter = HtmlFormatter(
            nowrap=True,  # Don't wrap in <div>
            noclasses=True,  # Use inline styles instead of CSS classes
            style="default",  # Use default color scheme
        )

        # Highlight the code
        highlighted = highlight(code, lexer, formatter)

        # Remove the <div> wrapper that Pygments adds
        highlighted = highlighted.replace('<div class="highlight"><pre>', "").replace(
            "</pre></div>", ""
        )

        # Replace Pygments color #00F with #ffe400
        highlighted = highlighted.replace("#00F", "#ffe400")
        highlighted = highlighted.replace("#00f", "#ffe400")

        return highlighted

    def _highlight_robot_framework(self, code: str, config: dict = None) -> str:
        """Custom Robot Framework syntax highlighting."""
        if not code:
            return ""

        lines = code.split("\n")
        highlighted_lines = []

        for line in lines:
            highlighted_line = self._highlight_robot_line(line, config)
            highlighted_lines.append(highlighted_line)

        return "\n".join(highlighted_lines)

    def _get_robot_framework_keywords(self, config: dict = None) -> list:
        """Get all Robot Framework keywords from built-in libraries (cached)."""
        if self._cached_keywords is not None:
            return self._cached_keywords

        try:
            from robot.libdocpkg import LibraryDocumentation

            libs = [
                "robot.libraries.BuiltIn",
                "robot.libraries.Collections",
                "robot.libraries.DateTime",
                "robot.libraries.Dialogs",
                "robot.libraries.OperatingSystem",
                "robot.libraries.Process",
                "robot.libraries.Screenshot",
                "robot.libraries.String",
                "robot.libraries.Telnet",
                "robot.libraries.XML",
            ]

            all_keywords = []
            for lib in libs:
                try:
                    lib_doc = LibraryDocumentation(lib)
                    all_keywords.extend([kw.name for kw in lib_doc.keywords])
                except Exception:
                    print(f"Warning: Could not load {lib}")
                    continue

            # Add custom keywords from config file
            if config and 'custom_keywords' in config:
                custom_keywords = config['custom_keywords']
                if isinstance(custom_keywords, list):
                    all_keywords.extend(custom_keywords)
                    print(f"Added {len(custom_keywords)} custom keywords from config")
            else:
                # Default custom keywords if no config provided
                default_custom_keywords = [
                    "Open Application",
                    "Close Application", 
                    "Kill Application",
                    "Connect to Application",
                    "Get Process ID",
                    "Wait for Process Exit"
                ]
                all_keywords.extend(default_custom_keywords)
            
            # Remove duplicates and sort
            all_keywords = sorted(set(all_keywords))
            print(f"Loaded {len(all_keywords)} Robot Framework keywords")
            self._cached_keywords = all_keywords
            return all_keywords

        except ImportError:
            print(
                "Error: robot.libdocpkg not available. Robot Framework must be installed."
            )
            # Return empty list if Robot Framework is not available
            self._cached_keywords = []
            return []

    def _highlight_robot_line(self, line: str, config: dict = None) -> str:
        """Highlight a single Robot Framework line with clean, non-overlapping highlighting."""
        if not line:
            return ""

        # Escape HTML first
        line = self._escape_html(line)

        # 1. Comments (highest priority - entire line)
        if line.strip().startswith("#"):
            return f'<span style="color: #6a9955; font-style: italic;">{line}</span>'

        # 2. Section headers (entire line) - keep as is
        if line.strip().startswith("***"):
            return f'<span style="color: #569cd6; font-weight: bold;">{line}</span>'

        # 3. Settings lines (Library, Resource, etc.) - keep as is
        settings = [
            "Library",
            "Resource",
            "Documentation",
            "Suite Setup",
            "Suite Teardown",
            "Test Setup",
            "Test Teardown",
            "Default Tags",
            "Force Tags",
            "Tags",
        ]
        for setting in settings:
            if line.strip().startswith(setting):
                # Split into setting name and value
                parts = line.split(None, 1)
                if len(parts) == 2:
                    return f'<span style="color: #c586c0; font-weight: bold;">{parts[0]}</span> {parts[1]}'
                else:
                    return f'<span style="color: #c586c0; font-weight: bold;">{line}</span>'

        # 4. Test case names (lines that don't start with spaces and aren't section headers)
        if (
            not line.startswith("    ")
            and not line.startswith("\t")
            and not line.startswith("***")
            and line.strip()
            and not line.startswith("[")
        ):
            return f'<span style="color: #dcdcaa; font-weight: bold;">{line}</span>'

        # 5. Keyword lines (indented lines) - use dynamic keyword list
        if line.startswith("    ") or line.startswith("\t"):
            # Find the indentation (spaces/tabs at the beginning)
            indent = ""
            for i, char in enumerate(line):
                if char in " \t":
                    indent += char
                else:
                    break

            # Get the content after indentation
            content = line[len(indent) :]

            # Get Robot Framework keywords dynamically
            robot_keywords = self._get_robot_framework_keywords(config)
            robot_keywords.extend(
                [
                    "IF",
                    "ELSE",
                    "ELSE IF",
                    "END",
                    "FOR",
                    "WHILE",
                    "Continue For Loop",
                    "Break",
                    "Continue",
                    "VAR",
                ]
            )

            # Check if the line starts with a variable (${var}, @{list}, &{dict})
            # If so, treat the entire line as a variable assignment, not a keyword
            if (
                content.startswith("${")
                or content.startswith("@{")
                or content.startswith("&{")
            ):
                # This is a variable assignment line, highlight the entire line as content
                highlighted_content = self._highlight_variables_only(content, config)
                return f"{indent}{highlighted_content}"

            # Try to match keywords (sorted by length, longest first for better matching)
            keyword_found = None
            rest_content = content

            # Sort keywords by length (longest first) to match multi-word keywords first
            sorted_keywords = sorted(robot_keywords, key=len, reverse=True)

            for keyword in sorted_keywords:
                if content.startswith(keyword):
                    # Check if the next character is a space or end of line
                    next_char_pos = len(keyword)
                    if next_char_pos >= len(content) or content[next_char_pos] == " ":
                        keyword_found = keyword
                        # Don't strip the rest content to preserve spacing
                        rest_content = content[next_char_pos:]
                        break

            if keyword_found:
                # Found a keyword
                if rest_content:
                    rest_content = self._highlight_variables_only(rest_content, config)
                    return f'{indent}<span style="color: #4ec9b0; font-weight: bold;">{keyword_found}</span> {rest_content}'
                else:
                    return f'{indent}<span style="color: #4ec9b0; font-weight: bold;">{keyword_found}</span>'
            else:
                # No keyword found - just highlight variables
                highlighted_content = self._highlight_variables_only(content, config)
                return f"{indent}{highlighted_content}"

        # 6. Default processing for other lines - only highlight variables
        line = self._highlight_variables_only(line, config)
        return line


    def _highlight_variables_only(self, text: str, config: dict = None) -> str:
        """Highlight Robot Framework variables, keywords, and keyword arguments."""
        import re
        
        # Variables (${variable}, @{list}, &{dict})
        text = re.sub(
            r"(\$\{[^}]+\})", r'<span style="color: #9cdcfe;">\1</span>', text
        )
        text = re.sub(r"(@\{[^}]+\})", r'<span style="color: #9cdcfe;">\1</span>', text)
        text = re.sub(r"(&\{[^}]+\})", r'<span style="color: #9cdcfe;">\1</span>', text)
        
        # Also highlight keywords in variable assignment lines FIRST
        # Get the keywords list
        robot_keywords = self._get_robot_framework_keywords(config)
        
        # Sort keywords by length (longest first) to match multi-word keywords first
        sorted_keywords = sorted(robot_keywords, key=len, reverse=True)
        
        for keyword in sorted_keywords:
            if keyword in text:
                # Simple replacement that preserves existing HTML by checking if already highlighted
                if f'<span style="color: #4ec9b0; font-weight: bold;">{keyword}</span>' not in text:
                    text = text.replace(keyword, f'<span style="color: #4ec9b0; font-weight: bold;">{keyword}</span>')
        
        # Keyword arguments (name=value) - but avoid HTML attributes
        # Only highlight if it's clearly a Robot Framework keyword argument
        # Use a more sophisticated approach that doesn't break existing HTML
        # Split by existing spans and process each part
        parts = re.split(r'(<span[^>]*>.*?</span>)', text)
        result_parts = []
        for part in parts:
            if part.startswith('<span') and part.endswith('</span>'):
                # Already highlighted, keep as is
                result_parts.append(part)
            else:
                # Process this part for keyword arguments
                part = re.sub(
                    r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=', 
                    r'<span style="color: #dcdcaa;">\1</span>=', 
                    part
                )
                result_parts.append(part)
        
        text = ''.join(result_parts)
        
        return text

    def _get_module_attribute(self, attr_name: str, module_vars: dict, default: str) -> str:
        """Get a module-level attribute value."""
        return module_vars.get(attr_name, default)

    def _get_module_docstring(self, tree: ast.AST) -> str:
        """Extract module-level docstring."""
        if (tree.body and isinstance(tree.body[0], ast.Expr) 
            and isinstance(tree.body[0].value, ast.Constant) 
            and isinstance(tree.body[0].value.value, str)):
            return tree.body[0].value.value
        return ""

    def _extract_module_keywords(self, tree: ast.AST) -> List[KeywordInfo]:
        """Extract keywords from module-level functions."""
        keywords = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                # Check if function has @keyword decorator
                for decorator in node.decorator_list:
                    if (isinstance(decorator, ast.Call) and 
                        isinstance(decorator.func, ast.Name) and 
                        decorator.func.id == "keyword"):
                        # Extract keyword name from decorator
                        keyword_name = node.name
                        if decorator.args and isinstance(decorator.args[0], ast.Constant):
                            keyword_name = decorator.args[0].value
                        
                        # Extract docstring
                        docstring = ""
                        if (node.body and isinstance(node.body[0], ast.Expr) and
                            isinstance(node.body[0].value, ast.Constant) and
                            isinstance(node.body[0].value.value, str)):
                            docstring = node.body[0].value.value
                        
                        # Extract function arguments
                        parameters = []
                        args_with_defaults = node.args.args[len(node.args.args) - len(node.args.defaults):]
                        defaults = node.args.defaults
                        
                        for i, arg in enumerate(node.args.args):
                            if arg.arg != 'self':  # Skip 'self' parameter
                                param_name = arg.arg
                                # Check for type annotation
                                if arg.annotation:
                                    param_type = self._extract_type_annotation(arg.annotation)
                                else:
                                    param_type = "Any"
                                
                                # Check for default value
                                param_str = f"{param_name}: {param_type}"
                                if arg in args_with_defaults:
                                    default_idx = args_with_defaults.index(arg)
                                    if default_idx < len(defaults):
                                        default_value = self._extract_default_value(defaults[default_idx])
                                        param_str += f" = {default_value}"
                                
                                parameters.append(param_str)
                        
                        # Extract return type
                        return_type = ""
                        if node.returns:
                            return_type = self._extract_type_annotation(node.returns)
                        
                        keywords.append(KeywordInfo(
                            name=keyword_name,
                            description=docstring,
                            example="",
                            parameters=parameters,
                            return_type=return_type,
                            line_number=node.lineno
                        ))
        return keywords

    def _extract_type_annotation(self, annotation: ast.AST) -> str:
        """Extract type annotation from AST node."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        elif isinstance(annotation, ast.Subscript):
            return self._extract_subscript_type(annotation)
        elif isinstance(annotation, ast.Attribute):
            # Handle qualified names like typing.List, typing.Union
            if isinstance(annotation.value, ast.Name):
                return f"{annotation.value.id}.{annotation.attr}"
            return "Any"
        elif isinstance(annotation, ast.BinOp):
            # Handle modern union syntax: str | int | None
            return self._extract_union_type(annotation)
        else:
            return "Any"

    def _extract_subscript_type(self, subscript: ast.Subscript) -> str:
        """Extract type from subscript annotation."""
        if isinstance(subscript.value, ast.Name):
            base_type = subscript.value.id
            slice_content = self._extract_slice_content(subscript.slice)
            return f"{base_type}[{slice_content}]"
        elif isinstance(subscript.value, ast.Attribute):
            # Handle typing.Union[str, int], typing.Optional[str]
            if isinstance(subscript.value.value, ast.Name):
                base_type = f"{subscript.value.value.id}.{subscript.value.attr}"
                slice_content = self._extract_slice_content(subscript.slice)
                return f"{base_type}[{slice_content}]"
        return "Any"

    def _extract_slice_content(self, slice_node: ast.AST) -> str:
        """Extract content from slice node."""
        if isinstance(slice_node, ast.Index):
            # Handle single parameter generics like List[str]
            return self._extract_type_annotation(slice_node.value)
        elif isinstance(slice_node, ast.Tuple):
            # Handle multiple parameter generics like Dict[str, int]
            elts = []
            for elt in slice_node.elts:
                elts.append(self._extract_type_annotation(elt))
            return ', '.join(elts)
        else:
            return self._extract_type_annotation(slice_node)

    def _extract_union_type(self, binop: ast.BinOp) -> str:
        """Extract union type from binary operation (str | int | None)."""
        def collect_union_types(node):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
                left_types = collect_union_types(node.left)
                right_types = collect_union_types(node.right)
                return left_types + right_types
            else:
                return [self._extract_type_annotation(node)]
        
        types = collect_union_types(binop)
        return ' | '.join(types)

    def _extract_default_value(self, default_node: ast.AST) -> str:
        """Extract default value from AST node."""
        if isinstance(default_node, ast.Constant):
            if isinstance(default_node.value, str):
                return f'"{default_node.value}"'
            elif isinstance(default_node.value, (int, float)):
                return str(default_node.value)
            elif isinstance(default_node.value, bool):
                return str(default_node.value)
            elif default_node.value is None:
                return "None"
            else:
                return repr(default_node.value)
        elif isinstance(default_node, ast.Name):
            return default_node.id
        elif isinstance(default_node, ast.List):
            return "[]"
        elif isinstance(default_node, ast.Dict):
            return "{}"
        elif isinstance(default_node, ast.Tuple):
            return "()"
        elif isinstance(default_node, ast.Call):
            # Handle function calls like datetime.now()
            if isinstance(default_node.func, ast.Name):
                return f"{default_node.func.id}()"
            elif isinstance(default_node.func, ast.Attribute):
                if isinstance(default_node.func.value, ast.Name):
                    return f"{default_node.func.value.id}.{default_node.func.attr}()"
        elif isinstance(default_node, ast.Attribute):
            # Handle qualified names like datetime.UTC
            if isinstance(default_node.value, ast.Name):
                return f"{default_node.value.id}.{default_node.attr}"
        else:
            return "..."

    def _highlight_robot_syntax(self, line: str) -> str:
        """Apply syntax highlighting to Robot Framework code."""
        if not line:
            return ""

        # Escape HTML first
        line = self._escape_html(line)

        # Robot Framework syntax highlighting
        # Settings and Test Cases sections
        line = re.sub(
            r"(\*\*\*\s+Settings\s+\*\*\*)",
            r'<span class="robot-settings">\1</span>',
            line,
        )
        line = re.sub(
            r"(\*\*\*\s+Test Cases\s+\*\*\*)",
            r'<span class="robot-test-cases">\1</span>',
            line,
        )
        line = re.sub(
            r"(\*\*\*\s+Keywords\s+\*\*\*)",
            r'<span class="robot-test-cases">\1</span>',
            line,
        )
        line = re.sub(
            r"(\*\*\*\s+Variables\s+\*\*\*)",
            r'<span class="robot-test-cases">\1</span>',
            line,
        )

        # Keywords (lines that start with 4+ spaces and contain a keyword)
        line = re.sub(
            r"^(\s{4,})([A-Za-z][A-Za-z0-9\s]*?)(\s+.*)?$",
            lambda m: f'{m.group(1)}<span class="robot-keywords">{m.group(2)}</span>{m.group(3) or ""}',
            line,
        )

        # Variables (${variable} and @{list} and &{dict})
        line = re.sub(
            r"(\$\{[^}]+\})", r'<span class="robot-variables">\1</span>', line
        )
        line = re.sub(r"(@\{[^}]+\})", r'<span class="robot-variables">\1</span>', line)
        line = re.sub(r"(&\{[^}]+\})", r'<span class="robot-variables">\1</span>', line)

        # Comments (# comment)
        line = re.sub(r"(#.*)$", r'<span class="robot-comments">\1</span>', line)

        # Strings (quoted text)
        line = re.sub(
            r'(["\'])([^"\']*)\1', r'\1<span class="robot-strings">\2</span>\1', line
        )

        # Numbers
        line = re.sub(r"\b(\d+)\b", r'<span class="robot-numbers">\1</span>', line)

        return line

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ""

        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&#x27;")
        return text


class DocumentationGenerator:
    """Generate documentation from parsed library information."""

    def __init__(self, library_info: LibraryInfo, parser=None):
        self.library_info = library_info
        self.parser = parser

    def generate_markdown(self) -> str:
        """Generate markdown documentation."""
        md_content = []

        # Header
        md_content.append(f"# {self.library_info.name}")
        md_content.append("")
        md_content.append(f"**Version:** {self.library_info.version}")
        md_content.append(f"**Scope:** {self.library_info.scope}")
        md_content.append("")

        if self.library_info.description:
            md_content.append("## Description")
            md_content.append("")
            md_content.append(self.library_info.description)
            md_content.append("")

        # Keywords section
        md_content.append("## Keywords")
        md_content.append("")

        for keyword in self.library_info.keywords:
            md_content.append(f"### {keyword.name}")
            md_content.append("")

            if keyword.description:
                md_content.append(keyword.description)
                md_content.append("")

            # Parameters
            if keyword.parameters:
                md_content.append("**Parameters:**")
                md_content.append("")
                for param in keyword.parameters:
                    md_content.append(f"- `{param}`")
                md_content.append("")

            # Return type
            if keyword.return_type and keyword.return_type != "None":
                md_content.append(f"**Returns:** `{keyword.return_type}`")
                md_content.append("")

            # Example
            if keyword.example:
                md_content.append("**Example:**")
                md_content.append("")
                md_content.append("```robot")
                md_content.append(keyword.example)
                md_content.append("```")
                md_content.append("")

        return "\n".join(md_content)

    def generate_html(self) -> str:
        """Generate HTML documentation following Robot Framework libdoc format."""
        html_content = []

        # HTML header following Robot Framework libdoc format
        html_content.append(
            """<!doctype html>
<html id="library-documentation-top" lang="en">

<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1, user-scalable=0">
  <meta http-equiv="Pragma" content="no-cache">
  <meta http-equiv="Expires" content="-1">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="Generator" content="Robot Framework Documentation Parser">
  <link rel="icon" type="image/x-icon" href="data:image/x-icon;base64,AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAKcAAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAAqAAAAAAAAAAAAAAAAAAAALIAAAD/AAAA4AAAANwAAADcAAAA3AAAANwAAADcAAAA3AAAANwAAADcAAAA4AAAAP8AAACxAAAAAAAAAKYAAAD/AAAAuwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAC/AAAA/wAAAKkAAAD6AAAAzAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAN8AAAD/AAAA+gAAAMMAAAAAAAAAAgAAAGsAAABrAAAAawAAAGsAAABrAAAAawAAAGsAAABrAAAADAAAAAAAAADaAAAA/wAAAPoAAADDAAAAAAAAAIsAAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAANEAAAAAAAAA2gAAAP8AAAD6AAAAwwAAAAAAAAAAAAAAMgAAADIAAAAyAAAAMgAAADIAAAAyAAAAMgAAADIAAAAFAAAAAAAAANoAAAD/AAAA+gAAAMMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADaAAAA/wAAAPoAAADDAAAAAAAAADwAAAB8AAAAAAAAAGAAAABcAAAAAAAAAH8AAABKAAAAAAAAAAAAAAAAAAAA2gAAAP8AAAD6AAAAwwAAAAAAAADCAAAA/wAAACkAAADqAAAA4QAAAAAAAAD7AAAA/wAAALAAAAAGAAAAAAAAANoAAAD/AAAA+gAAAMMAAAAAAAAAIwAAAP4AAAD/AAAA/wAAAGAAAAAAAAAAAAAAAMkAAAD/AAAAigAAAAAAAADaAAAA/wAAAPoAAADDAAAAAAAAAAAAAAAIAAAAcAAAABkAAAAAAAAAAAAAAAAAAAAAAAAAEgAAAAAAAAAAAAAA2gAAAP8AAAD7AAAAywAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAN4AAAD/AAAAqwAAAP8AAACvAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAALIAAAD/AAAAsgAAAAAAAAC5AAAA/wAAAMoAAADAAAAAwAAAAMAAAADAAAAAwAAAAMAAAADAAAAAwAAAAMkAAAD/AAAAvAAAAAAAAAAAAAAAAAAAAKwAAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAArQAAAAAAAAAAwAMAAIABAAAf+AAAP/wAAD/8AAAgBAAAP/wAAD/8AAA//AAAJIwAADHEAAA//AAAP/wAAB/4AACAAQAAwAMAAA==">
  <title>"""
            + self.library_info.name
            + """ Documentation</title>
  <style>
    :root {
      --background-color: #0d1117;
      --text-color: #f0f6fc;
      --border-color: #30363d;
      --light-background-color: #161b22;
      --robot-highlight: #00d4aa;
      --highlighted-color: var(--background-color);
      --highlighted-background-color: #ffd700;
      --less-important-text-color: #8b949e;
      --link-color: #58a6ff;
      color-scheme: dark
    }

    [data-theme=light] {
      --background-color: white;
      --text-color: black;
      --border-color: #e0e0e2;
      --light-background-color: #f3f3f3;
      --robot-highlight: #00c0b5;
      --highlighted-color: var(--text-color);
      --highlighted-background-color: yellow;
      --less-important-text-color: gray;
      --link-color: #00e
    }

    body {
      background: var(--background-color);
      color: var(--text-color);
      margin: 0;
      font-family: system-ui, -apple-system, sans-serif;
      line-height: 1.6;
    }

    .container {
      display: flex;
      min-height: 100vh;
    }

    .sidebar {
      width: 300px;
      background: var(--light-background-color);
      border-right: 1px solid var(--border-color);
      padding: 20px;
      position: fixed;
      height: 100vh;
      overflow-y: auto;
    }

    .theme-toggle {
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 1000;
      background: var(--light-background-color);
      color: var(--text-color);
      border: 1px solid var(--border-color);
      padding: 8px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      transition: all 0.3s ease;
    }

    .theme-toggle:hover {
      background: var(--robot-highlight);
      color: var(--background-color);
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }

    .sidebar h1 {
      color: var(--robot-highlight);
      margin-bottom: 10px;
      font-size: 1.5em;
      border-bottom: 2px solid var(--robot-highlight);
      padding-bottom: 10px;
    }

    .sidebar .version {
      color: var(--less-important-text-color);
      font-size: 0.9em;
      margin-bottom: 10px;
    }

    .sidebar .scope {
      color: var(--less-important-text-color);
      font-size: 0.9em;
    }

    .sidebar h3 {
      color: var(--text-color);
      margin: 20px 0 10px 0;
      font-size: 1.1em;
    }

    .keyword-list {
      list-style: none;
      padding: 0;
    }

    .keyword-list li {
      margin: 5px 0;
    }

    .keyword-list a {
      color: var(--link-color);
      text-decoration: none;
      padding: 8px 12px;
      display: block;
      border-radius: 4px;
      transition: background-color 0.3s;
      font-size: 0.9em;
    }

    .keyword-list a:hover {
      background-color: var(--border-color);
    }

    .search-container {
      margin: 20px 0;
    }

    .search-input {
      width: 100%;
      padding: 10px 12px;
      border: 1px solid var(--border-color);
      border-radius: 6px;
      background: var(--background-color);
      color: var(--text-color);
      font-size: 14px;
      transition: border-color 0.3s ease;
      box-sizing: border-box;
    }

    .search-input:focus {
      outline: none;
      border-color: var(--robot-highlight);
      box-shadow: 0 0 0 2px rgba(0, 212, 170, 0.2);
    }

    .search-input::placeholder {
      color: var(--less-important-text-color);
    }

    .keyword-list li.hidden {
      display: none;
    }

    .no-results {
      color: var(--less-important-text-color);
      font-style: italic;
      text-align: center;
      padding: 20px;
    }

    .main-content {
      margin-left: 320px;
      padding: 40px 60px;
      max-width: 800px;
      background: var(--background-color);
      min-height: 100vh;
      font-size: 16px;
    }

    .main-content h1 {
      color: var(--text-color);
      border-bottom: 3px solid var(--robot-highlight);
      padding-bottom: 10px;
      margin-bottom: 20px;
    }

    .main-content h2 {
      color: var(--text-color);
      margin: 0px 0 0px 0;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 5px;
    }

    .main-content h3 {
      color: var(--text-color);
      margin: 0px 0 0px 0;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 5px;
    }

    .main-content h4 {
      color: var(--text-color);
      margin: 0px 0 0px 0;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 5px;
    }

    .main-content h5 {
      color: var(--text-color);
      margin: 0px 0 0px 0;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 5px;
    }

    .main-content h6 {
      color: var(--text-color);
      margin: 0px 0 0px 0;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 5px;
    }

    .keyword-container {
      background: var(--background-color);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 20px;
      margin: 20px 0;
    }

    .keyword-name h2 {
      color: var(--robot-highlight);
      margin: 0 0 15px 0;
      border-bottom: 2px solid var(--robot-highlight);
      padding-bottom: 10px;
    }

    .keyword-name a {
      color: var(--robot-highlight);
      text-decoration: none;
    }

    .keyword-name a:hover {
      text-decoration: underline;
    }

    .args {
      background: #1c2128;
      border: 1px solid var(--border-color);
      padding: 15px;
      border-radius: 5px;
      margin: 10px 0;
    }

     .args h4 {
       color: var(--text-color);
       margin: 2px 0 4px 0;
       border-bottom: none;
     }

    .arguments-list {
      margin-left: 20px;
    }

    .arguments-list li {
      margin: 5px 0;
    }

    .arg-name {
      font-family: monospace;
      background: #6666664d;
      padding: 2px 6px;
      border-radius: 3px;
      font-weight: bold;
    }

    .return-type {
      background: #0d2818;
      border: 1px solid #238636;
      padding: 10px;
      border-radius: 5px;
      margin: 10px 0;
      border-left: 4px solid #238636;
    }

     .return-type h4 {
       color: var(--text-color);
       margin: 2px 0 4px 0;
       border-bottom: none;
     }

    .arg-type {
      font-family: monospace;
      background: #3d5230a8;
      padding: 2px 6px;
      border-radius: 3px;
    }

    .kw-docs {
      background: #1c1c16;
      border: 1px solid #d29922;
      padding: 15px;
      border-radius: 5px;
      margin: 15px 0;
      border-left: 4px solid #d29922;
    }

     .kw-docs h4 {
       color: var(--text-color);
       margin: 2px 0 4px 0;
       border-bottom: 0px;
     }

     .kwdoc {
       font-family: monospace;
       background: var(--light-background-color);
       padding: 10px;
       border-radius: 5px;
       overflow-x: auto;
       white-space: pre-wrap;
       font-size: 0.9em;
       line-height: 1.3;
     }

     /* Custom syntax styles */
     .kwdoc h1, .kwdoc h2, .kwdoc h3, .kwdoc h4, .kwdoc h5, .kwdoc h6 {
       color: var(--text-color);
       margin: 4px 0 0px 0;
       font-weight: bold;
     }

     .kwdoc h1 { font-size: 1.4em; }
     .kwdoc h2 { font-size: 1.3em; }
     .kwdoc h3 { font-size: 1.2em; }
     .kwdoc h4 { font-size: 1.1em; }
     .kwdoc h5 { font-size: 1.05em; }
     .kwdoc h6 { font-size: 1em; }

     .kwdoc p {
       margin: 0px;
       line-height: 1.5;
       font-size: 1.1em;
     }

     .kwdoc strong {
       font-weight: bold;
       color: var(--robot-highlight);
     }

     .kwdoc em {
       font-style: italic;
     }

     .kwdoc u {
       text-decoration: underline;
     }

     .kwdoc del {
       text-decoration: line-through;
       opacity: 0.7;
     }

     .kwdoc code {
       background: var(--light-background-color);
       padding: 2px 6px;
       border-radius: 3px;
       font-family: 'JetBrains Mono', 'Fira Code', monospace;
       font-size: 0.9em;
     }

     .kwdoc a {
       color: var(--link-color);
       text-decoration: none;
     }

     .kwdoc a:hover {
       text-decoration: underline;
     }

     .kwdoc hr {
       border: none;
       border-top: 1px solid var(--border-color);
       margin: 10px 0;
     }

     .kwdoc .code-block {
       background: var(--background-color);
       border: 1px solid var(--border-color);
       border-radius: 5px;
       margin: 0px;
       overflow-x: auto;
     }

     .kwdoc .code-block pre {
       margin: 0;
       padding: 10px;
       font-family: 'JetBrains Mono', 'Fira Code', monospace;
       font-size: 1em;
       line-height: 1.5;
       white-space: pre;
       overflow-x: auto;
     }

     /* Robot Framework syntax highlighting */
     .kwdoc .code-block pre.language-robot {
       color: #d4d4d4;
     }

     .kwdoc .code-block pre.language-robot .robot-settings {
       color: #569cd6 !important;
       font-weight: bold;
     }

     .kwdoc .code-block pre.language-robot .robot-test-cases {
       color: #569cd6 !important;
       font-weight: bold;
     }

     .kwdoc .code-block pre.language-robot .robot-keywords {
       color: #4ec9b0 !important;
       font-weight: bold;
     }

     .kwdoc .code-block pre.language-robot .robot-variables {
       color: #9cdcfe !important;
     }

     .kwdoc .code-block pre.language-robot .robot-comments {
       color: #6a9955 !important;
       font-style: italic;
     }

     .kwdoc .code-block pre.language-robot .robot-strings {
       color: #ce9178 !important;
     }

     .kwdoc .code-block pre.language-robot .robot-numbers {
       color: #b5cea8 !important;
     }

     .kwdoc .doc-table {
       width: 100%;
       border-collapse: collapse;
       margin: 0px;
       background: var(--light-background-color);
       border: 1px solid var(--border-color);
       border-radius: 5px;
       overflow: hidden;
     }

     .kwdoc .doc-table th,
     .kwdoc .doc-table td {
       padding: 6px 10px;
       text-align: left;
       border-bottom: 1px solid var(--border-color);
     }

     .kwdoc .doc-table th {
       background: var(--border-color);
       font-weight: bold;
       color: var(--text-color);
     }

     .kwdoc .doc-table tr:last-child td {
       border-bottom: none;
     }

     .kwdoc .doc-table tr:hover {
       background: var(--border-color);
     }

     .kwdoc ul {
       margin: 0px;
     }

     .kwdoc li {
       margin: 1px 0;
       line-height: 1.5;
       font-size: 1.1em;
     }

     /* Introduction content styles */
     .intro-content {
       font-family: monospace;
       font-size: inherit;
       background: transparent;
       padding: 0;
       margin-bottom: 20px;
     }

     .intro-content h1, .intro-content h2, .intro-content h3, .intro-content h4, .intro-content h5, .intro-content h6 {
       color: var(--text-color);
       margin: 4px 0 0px 0;
       font-weight: bold;
     }

     .intro-content h1 { font-size: 1.4em; }
     .intro-content h2 { font-size: 1.3em; }
     .intro-content h3 { font-size: 1.2em; }
     .intro-content h4 { font-size: 1.1em; }
     .intro-content h5 { font-size: 1.05em; }
     .intro-content h6 { font-size: 1em; }

     .intro-content p {
       margin: 0px;
       line-height: 1.9;
       font-size: inherit;
     }

     .intro-content strong {
       font-weight: bold;
       color: var(--robot-highlight);
     }

     .intro-content em {
       font-style: italic;
     }

     .intro-content u {
       text-decoration: underline;
     }

     .intro-content del {
       text-decoration: line-through;
       opacity: 0.7;
     }

     .intro-content code {
       background: var(--light-background-color);
       padding: 2px 6px;
       border-radius: 3px;
       font-family: 'JetBrains Mono', 'Fira Code', monospace;
       font-size: 0.9em;
     }

     .intro-content a {
       color: var(--link-color);
       text-decoration: none;
     }

     .intro-content a:hover {
       text-decoration: underline;
     }

     .intro-content hr {
       border: none;
       border-top: 1px solid var(--border-color);
       margin: 10px 0;
     }

     .intro-content .code-block {
       background: var(--background-color);
       border: 1px solid var(--border-color);
       border-radius: 5px;
       margin: 0px;
       overflow-x: auto;
     }

     .intro-content .code-block pre {
       margin: 0;
       padding: 10px;
       font-family: 'JetBrains Mono', 'Fira Code', monospace;
       font-size: 0.9em;
       line-height: 1.3;
       white-space: pre;
       overflow-x: auto;
     }

     .intro-content .doc-table {
       width: 100%;
       border-collapse: collapse;
       margin: 0px;
       background: var(--light-background-color);
       border: 1px solid var(--border-color);
       border-radius: 5px;
       overflow: hidden;
     }

     .intro-content .doc-table th,
     .intro-content .doc-table td {
       padding: 6px 10px;
       text-align: left;
       border-bottom: 1px solid var(--border-color);
     }

     .intro-content .doc-table th {
       background: var(--border-color);
       font-weight: bold;
       color: var(--text-color);
     }

     .intro-content .doc-table tr:last-child td {
       border-bottom: none;
     }

     .intro-content .doc-table tr:hover {
       background: var(--border-color);
     }

     .intro-content ul {
       margin: 0px;
     }

     .intro-content li {
       margin: 1px 0;
       line-height: 1.5;
       font-size: inherit;
     }

    @media (max-width: 768px) {
      .sidebar {
        width: 100%;
        position: relative;
        height: auto;
      }
      .main-content {
        margin-left: 0;
        padding: 20px 30px;
      }
      .theme-toggle {
        top: 10px;
        right: 10px;
      }
    }
  </style>
</head>
<body>"""
        )

        # Theme toggle button (top right corner)
        html_content.append(
            '<button id="theme-toggle" class="theme-toggle" onclick="toggleTheme()">🌙 Light Mode</button>'
        )

        # Sidebar
        html_content.append('<div class="container">')
        html_content.append('<div class="sidebar">')
        html_content.append(f"<h1>{self.library_info.name}</h1>")
        html_content.append(
            f'<div class="version">Version: {self.library_info.version}</div>'
        )
        html_content.append(
            f'<div class="scope">Scope: {self.library_info.scope}</div>'
        )

        html_content.append('<div class="search-container">')
        html_content.append(
            '<input type="text" id="keyword-search" class="search-input" placeholder="Search keywords...">'
        )
        html_content.append("</div>")

        html_content.append("<h3>Keywords</h3>")
        html_content.append('<ul class="keyword-list" id="keyword-list">')
        for keyword in self.library_info.keywords:
            keyword_id = keyword.name.lower().replace(" ", "-")
            html_content.append(f'<li><a href="#{keyword_id}">{keyword.name}</a></li>')
        html_content.append("</ul>")
        html_content.append("</div>")

        # Main content
        html_content.append('<div class="main-content">')

        if self.library_info.description:
            html_content.append("<h2>Introduction</h2>")
            # Process the class docstring through custom syntax parser
            if self.parser:
                processed_description = self.parser._parse_custom_syntax(self.library_info.description)
            else:
                processed_description = self.library_info.description
            html_content.append(f'<div class="intro-content">{processed_description}</div>')

        # Keywords
        html_content.append('<h2 id="Keywords">Keywords</h2>')
        html_content.append('<div class="keywords">')

        for keyword in self.library_info.keywords:
            keyword_id = keyword.name.lower().replace(" ", "-")
            html_content.append(f'<div class="keyword-container" id="{keyword_id}">')
            html_content.append('<div class="keyword-name">')
            html_content.append(
                f'<h2><a class="kw-name" href="#{keyword_id}">{keyword.name}</a></h2>'
            )
            html_content.append("</div>")

            html_content.append('<div class="keyword-content">')
            html_content.append('<div class="kw-overview">')

            # Parameters
            if keyword.parameters:
                html_content.append('<div class="args">')
                html_content.append("<h4>Arguments</h4>")
                html_content.append('<div class="arguments-list-container">')
                html_content.append('<div class="arguments-list">')
                for param in keyword.parameters:
                    html_content.append(
                        f'<li><span class="arg-name">{param}</span></li>'
                    )
                html_content.append("</div>")
                html_content.append("</div>")
                html_content.append("</div>")

            # Return type
            if keyword.return_type and keyword.return_type != "None":
                html_content.append('<div class="return-type">')
                html_content.append("<h4>Return Type</h4>")
                html_content.append(
                    f'<span class="arg-type">{keyword.return_type}</span>'
                )
                html_content.append("</div>")

            html_content.append("</div>")

            # Documentation
            if keyword.description:
                html_content.append('<div class="kw-docs">')
                html_content.append("<h4>Documentation</h4>")
                html_content.append('<div class="kwdoc doc">')
                # Don't escape HTML for syntax highlighted content
                html_content.append(keyword.description)
                html_content.append("</div>")
                html_content.append("</div>")

            html_content.append("</div>")
            html_content.append("</div>")

        html_content.append("</div>")
        html_content.append("</div>")
        html_content.append("</div>")

        # JavaScript for theme toggle and search functionality
        html_content.append("""
<script>
function toggleTheme() {
  const body = document.body;
  const button = document.getElementById('theme-toggle');
  
  if (body.getAttribute('data-theme') === 'light') {
    body.setAttribute('data-theme', 'dark');
    button.textContent = '🌙 Light Mode';
  } else {
    body.setAttribute('data-theme', 'light');
    button.textContent = '☀️ Dark Mode';
  }
  
  // Save preference
  localStorage.setItem('theme', body.getAttribute('data-theme'));
}

function searchKeywords() {
  const searchInput = document.getElementById('keyword-search');
  const keywordList = document.getElementById('keyword-list');
  const searchTerm = searchInput.value.toLowerCase().trim();
  
  const keywords = keywordList.querySelectorAll('li');
  let visibleCount = 0;
  
  keywords.forEach(keyword => {
    const keywordText = keyword.textContent.toLowerCase();
    if (keywordText.includes(searchTerm)) {
      keyword.classList.remove('hidden');
      visibleCount++;
    } else {
      keyword.classList.add('hidden');
    }
  });
  
  // Show no results message if no keywords match
  let noResultsMsg = keywordList.querySelector('.no-results');
  if (visibleCount === 0 && searchTerm !== '') {
    if (!noResultsMsg) {
      noResultsMsg = document.createElement('li');
      noResultsMsg.className = 'no-results';
      noResultsMsg.textContent = 'No keywords found';
      keywordList.appendChild(noResultsMsg);
    }
  } else if (noResultsMsg) {
    noResultsMsg.remove();
  }
}

// Load saved theme on page load
document.addEventListener('DOMContentLoaded', function() {
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme) {
    document.body.setAttribute('data-theme', savedTheme);
    const button = document.getElementById('theme-toggle');
    if (savedTheme === 'light') {
      button.textContent = '☀️ Dark Mode';
    } else {
      button.textContent = '🌙 Light Mode';
    }
  }
  
  // Add search functionality
  const searchInput = document.getElementById('keyword-search');
  if (searchInput) {
    searchInput.addEventListener('input', searchKeywords);
    searchInput.addEventListener('keyup', function(e) {
      if (e.key === 'Escape') {
        searchInput.value = '';
        searchKeywords();
        searchInput.blur();
      }
    });
  }
});
</script>""")

        html_content.append("</body></html>")

        return "\n".join(html_content)


def load_config(config_file: str) -> dict:
    """Load configuration from JSON file."""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"Loaded configuration from {config_file}")
        return config
    except FileNotFoundError:
        print(f"Warning: Config file {config_file} not found, using defaults")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file {config_file}: {e}")
        return {}
    except Exception as e:
        print(f"Error loading config file {config_file}: {e}")
        return {}


def main():
    """Main function to run the documentation parser."""
    parser = argparse.ArgumentParser(
        description="Generate documentation from Robot Framework library files"
    )
    parser.add_argument("input_file", help="Path to the Python library file")
    parser.add_argument(
        "-o", "--output", help="Output file path (default: input_file.md)"
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["markdown", "html"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "-c", "--config", 
        help="Path to JSON configuration file for custom keywords and settings"
    )

    args = parser.parse_args()

    # Load configuration
    config = {}
    if args.config:
        config = load_config(args.config)

    # Parse the library file
    doc_parser = RobotFrameworkDocParser(config)
    try:
        library_info = doc_parser.parse_file(args.input_file)
        print(
            f"Successfully parsed {len(library_info.keywords)} keywords from {library_info.name}"
        )
    except Exception as e:
        print(f"Error parsing file: {e}")
        return 1

    # Generate documentation
    doc_generator = DocumentationGenerator(library_info, doc_parser)

    if args.format == "markdown":
        content = doc_generator.generate_markdown()
        output_file = args.output or f"{Path(args.input_file).stem}.md"
    else:
        content = doc_generator.generate_html()
        output_file = args.output or f"{Path(args.input_file).stem}.html"

    # Write output file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Documentation generated: {output_file}")
    return 0


if __name__ == "__main__":
    exit(main())
