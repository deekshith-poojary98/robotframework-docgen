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
import textwrap
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass
from functools import lru_cache

try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, TextLexer
    from pygments.formatters import HtmlFormatter
    from pygments.util import ClassNotFound

    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

try:
    import markdown

    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


@dataclass
class KeywordInfo:
    """Information about a Robot Framework keyword."""

    name: str
    description: str
    example: str
    parameters: List[Tuple[str, str]]
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
    
    # Standard Robot Framework libraries to load keywords from
    ROBOT_FRAMEWORK_LIBRARIES = [
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
    
    # Reserved control keywords for Robot Framework
    RESERVED_CONTROL_KEYWORDS = [
        "IF",
        "ELSE IF",
        "ELSE",
        "END",
        "FOR",
        "IN",
        "IN RANGE",
        "IN ENUMERATE",
        "IN ZIP",
        "WHILE",
        "TRY",
        "EXCEPT",
        "FINALLY",
        "RETURN",
        "CONTINUE",
        "BREAK",
        "PASS",
        "FAIL",
        "VAR",
    ]
    
    # Robot Framework settings reserved keywords
    ROBOT_FRAMEWORK_SETTINGS_KEYWORDS = [
        "Library",
        "Resource",
        "Variables",
        "Suite Setup",
        "Suite Teardown",
        "Test Setup",
        "Test Teardown",
        "Test Template",
        "Test Timeout",
        "Task Setup",
        "Task Teardown",
        "Task Template",
        "Task Timeout",
        "Documentation",
        "Metadata",
        "Force Tags",
        "Default Tags",
        "Keyword Tags",
    ]

    def __init__(self, config: dict = None):
        self.library_info = None
        self._cached_keywords = None
        self.config = config
        self._identifier_pattern = re.compile(r"\b[A-Za-z0-9]*_[A-Za-z0-9_]*\b")

    def _function_name_to_keyword_name(self, function_name: str) -> str:
        """Convert function name to keyword name by removing underscores and title casing.

        Examples:
            my_keyword -> My Keyword
            open_workbook -> Open Workbook
            get_sheet_index -> Get Sheet Index
        """
        return function_name.replace("_", " ").title()

    def parse_file(self, file_path: str) -> LibraryInfo:
        """Parse a Python file and extract library information."""
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        tree = ast.parse(content)
        module_globals = self._execute_module_safely(file_path)

        library_info = self._extract_library_info(tree, file_path, module_globals)
        self.library_info = library_info
        self._cached_keywords = None
        return library_info

    def _execute_module_safely(self, file_path: str) -> dict:
        """Safely execute the module to get actual values."""
        try:
            import sys
            import importlib.util
            import os

            file_dir = os.path.dirname(os.path.abspath(file_path))
            if file_dir not in sys.path:
                sys.path.insert(0, file_dir)

            spec = importlib.util.spec_from_file_location("temp_module", file_path)
            if spec is None or spec.loader is None:
                return {}

            module = importlib.util.module_from_spec(spec)

            spec.loader.exec_module(module)

            result = {}
            for attr_name in dir(module):
                if not attr_name.startswith("_"):
                    try:
                        attr_value = getattr(module, attr_name)
                        if not callable(attr_value):
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

        module_vars = self._extract_module_variables(tree)

        module_vars.update(module_globals)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if self._is_robot_library_class(node):
                    return self._parse_library_class(node, module_vars)

        filename = Path(file_path).stem
        return LibraryInfo(
            name=filename,
            version=self._get_module_attribute(
                "ROBOT_LIBRARY_VERSION", module_vars, "Unknown"
            ),
            scope=self._get_module_attribute(
                "ROBOT_LIBRARY_SCOPE", module_vars, "TEST"
            ),
            description=self._get_module_docstring(tree),
            keywords=self._extract_module_keywords(tree),
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
                        elif hasattr(ast, "Str") and isinstance(node.value, ast.Str):
                            module_vars[target.id] = str(node.value.s)
        return module_vars

    def _is_robot_library_class(self, class_node: ast.ClassDef) -> bool:
        """Check if a class is a Robot Framework library."""
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == "keyword":
                        return True
                    elif isinstance(decorator, ast.Call) and isinstance(
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

        version = self._get_class_attribute(
            class_node, "ROBOT_LIBRARY_VERSION", "Unknown", module_vars
        )
        scope = self._get_class_attribute(
            class_node, "ROBOT_LIBRARY_SCOPE", "TEST", module_vars
        )

        if version in module_vars:
            version = module_vars[version]
        if scope in module_vars:
            scope = module_vars[scope]

        description = self._get_class_docstring(class_node)

        keyword_data = []
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                keyword_name = None
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == "keyword":
                        keyword_name = self._function_name_to_keyword_name(node.name)
                    elif isinstance(decorator, ast.Call) and isinstance(
                        decorator.func, ast.Name
                    ):
                        if decorator.func.id == "keyword":
                            if decorator.args and isinstance(
                                decorator.args[0], ast.Constant
                            ):
                                keyword_name = decorator.args[0].value
                            else:
                                keyword_name = self._function_name_to_keyword_name(
                                    node.name
                                )

                if keyword_name:
                    docstring = ast.get_docstring(node) or ""
                    parameters = []
                    for arg in node.args.args:
                        if arg.arg == "self":
                            continue
                        param_name = arg.arg
                        param_type = (
                            self._ast_type_to_string(arg.annotation)
                            if arg.annotation
                            else "Any"
                        )
                        parameters.append((param_name, param_type))

                    return_type = "None"
                    if node.returns:
                        return_type = self._ast_type_to_string(node.returns)

                    keyword_data.append(
                        {
                            "name": keyword_name,
                            "docstring": docstring,
                            "parameters": parameters,
                            "return_type": return_type,
                            "line_number": node.lineno,
                        }
                    )

        keywords = []
        for data in keyword_data:
            keywords.append(
                KeywordInfo(
                    name=data["name"],
                    description="",
                    example="",
                    parameters=data["parameters"],
                    return_type=data["return_type"],
                    line_number=data["line_number"],
                )
            )

        library_info = LibraryInfo(
            name=class_node.name,
            version=version,
            scope=scope,
            description=description,
            keywords=keywords,
        )
        self.library_info = library_info
        self._cached_keywords = None

        for i, data in enumerate(keyword_data):
            description, example = self._parse_docstring(data["docstring"], self.config)
            keywords[i].description = description
            keywords[i].example = example

        return library_info

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
                            if node.value.id in module_vars:
                                return module_vars[node.value.id]
                            return str(node.value.id)
                        elif isinstance(node.value, ast.Call):
                            return self._execute_function_call(node.value, module_vars)
                        elif hasattr(ast, "Str") and isinstance(node.value, ast.Str):
                            return str(node.value.s)
        return default

    def _execute_function_call(self, call_node: ast.Call, module_vars: dict) -> str:
        """Execute a function call safely to get the return value."""
        try:
            if isinstance(call_node.func, ast.Name):
                func_name = call_node.func.id

                if func_name in ["__version__", "version"]:
                    return module_vars.get(func_name, "Unknown")
                else:
                    return self._find_and_execute_function(func_name, module_vars)
            else:
                return "Unknown"
        except Exception as e:
            print(f"Warning: Could not execute function call: {e}")
            return "Unknown"

    def _find_and_execute_function(self, func_name: str, module_vars: dict) -> str:
        """Find and execute a function by name."""
        try:
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

    def _ast_type_to_string(self, node: ast.AST) -> str:
        """Convert an AST type annotation node to a string representation."""
        if node is None:
            return "Any"

        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Subscript):
            value = self._ast_type_to_string(node.value)
            if isinstance(node.slice, ast.Tuple):
                args = [self._ast_type_to_string(el) for el in node.slice.elts]
                return f"{value}[{', '.join(args)}]"
            else:
                arg = self._ast_type_to_string(node.slice)
                return f"{value}[{arg}]"
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            left = self._ast_type_to_string(node.left)
            right = self._ast_type_to_string(node.right)
            return f"{left} | {right}"
        else:
            try:
                return ast.unparse(node) if hasattr(ast, "unparse") else "Any"
            except Exception:
                return "Any"

    def _parse_keyword_function(
        self, func_node: ast.FunctionDef
    ) -> Optional[KeywordInfo]:
        """Parse a function to extract keyword information."""
        keyword_name = None
        for decorator in func_node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "keyword":
                keyword_name = self._function_name_to_keyword_name(func_node.name)
            elif isinstance(decorator, ast.Call) and isinstance(
                decorator.func, ast.Name
            ):
                if decorator.func.id == "keyword":
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        keyword_name = decorator.args[0].value
                    else:
                        keyword_name = self._function_name_to_keyword_name(
                            func_node.name
                        )

        if not keyword_name:
            return None

        docstring = ast.get_docstring(func_node) or ""
        description, example = self._parse_docstring(docstring, self.config)

        parameters = []
        for arg in func_node.args.args:
            if arg.arg == "self":
                continue
            param_name = arg.arg
            param_type = (
                self._ast_type_to_string(arg.annotation) if arg.annotation else "Any"
            )
            parameters.append((param_name, param_type))

        return_type = "None"
        if func_node.returns:
            return_type = self._ast_type_to_string(func_node.returns)

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

        if MARKDOWN_AVAILABLE:
            parsed_content = self._render_docstring_with_markdown(docstring, config)
        parsed_content = self._parse_custom_syntax(docstring, config)

        return parsed_content, ""

    def _render_docstring_with_markdown(
        self, docstring: str, config: dict = None
    ) -> str:
        """Convert a docstring to HTML using the markdown package with custom code highlighting."""
        if not MARKDOWN_AVAILABLE:
            return self._parse_custom_syntax(docstring, config)

        content = textwrap.dedent(docstring).strip("\n")
        if not content:
            return ""

        code_pattern = re.compile(r"```(?P<lang>[^\n`]*)\n(?P<code>.*?)```", re.DOTALL)
        segments: List[str] = []
        last_end = 0

        for match in code_pattern.finditer(content):
            text_chunk = content[last_end : match.start()]
            text_chunk = re.sub(r"``([^`\n*]+?)\*\*(?!\*)", r"``\1``", text_chunk)
            text_chunk = self._protect_identifier_tokens(text_chunk)
            text_html = self._markdown_to_html(text_chunk)
            if text_html:
                segments.append(text_html)

            lang = (match.group("lang") or "text").strip()
            code_block = textwrap.dedent(match.group("code") or "").rstrip("\n")
            if code_block:
                segments.append(self._render_code_block(code_block, lang, config))

            last_end = match.end()

        remainder = content[last_end:]
        remainder = re.sub(r"``([^`\n*]+?)\*\*(?!\*)", r"``\1``", remainder)
        remainder = self._protect_identifier_tokens(remainder)
        remainder_html = self._markdown_to_html(remainder)
        if remainder_html:
            segments.append(remainder_html)

        return "\n".join(segments)

    def _markdown_to_html(self, text: str) -> str:
        """Convert markdown text (without fenced code blocks) to HTML."""
        cleaned = textwrap.dedent(text).strip()
        if not cleaned:
            return ""

        cleaned = re.sub(r"``([^`\n]+?)\*\*(?!\*)", r"``\1``", cleaned)

        cleaned = re.sub(r"!\s+\[", "![", cleaned)

        def convert_image(match):
            alt_text = match.group(1)
            url = match.group(2)
            import html

            alt_text = html.escape(alt_text)
            return f'<img alt="{alt_text}" src="{url}" />'

        image_pattern = r"!\[([^\]]+)\]\(([^\)]+)\)"
        cleaned = re.sub(image_pattern, convert_image, cleaned)

        return markdown.markdown(
            cleaned,
            extensions=[
                "sane_lists",
                "tables",
                "toc",
            ],
        )

    def _render_code_block(self, code: str, language: str, config: dict = None) -> str:
        """Render a fenced code block with appropriate syntax highlighting."""
        language = (language or "text").strip() or "text"
        normalized = language.lower()

        code = code.rstrip()

        if normalized == "robot":
            highlighted = self._highlight_robot_framework(code, config)
        else:
            highlighted = self._highlight_with_pygments(code, normalized, config)

        highlighted = highlighted.rstrip()

        return (
            f'<div class="code-block"><pre class="language-{language}">'
            f"{highlighted}"
            "</pre></div>"
        )

    def _protect_identifier_tokens(self, text: str) -> str:
        """Wrap underscore-based identifier tokens in backticks to prevent accidental emphasis."""
        if not text:
            return ""

        segments = text.split("`")
        for idx in range(0, len(segments), 2):
            segments[idx] = self._identifier_pattern.sub(
                lambda m: f"`{m.group(0)}`",
                segments[idx],
            )

        reconstructed = []
        for idx, segment in enumerate(segments):
            reconstructed.append(segment)
            if idx < len(segments) - 1:
                reconstructed.append("`")

        return "".join(reconstructed)

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
        prev_content_type = None
        current_language = "text"

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            if line.startswith("```"):
                if in_code_block:
                    html_lines.append("</pre></div>")
                    in_code_block = False
                else:
                    current_language = line[3:].strip() or "text"
                    html_lines.append(
                        f'<div class="code-block"><pre class="language-{current_language}">'
                    )
                    in_code_block = True
                i += 1
                continue

            if in_code_block:
                code_lines = []
                j = i
                while j < len(lines) and not lines[j].startswith("```"):
                    code_lines.append(lines[j])
                    j += 1

                code_content = "\n".join(code_lines)

                if PYGMENTS_AVAILABLE and current_language != "robot":
                    highlighted_code = self._highlight_with_pygments(
                        code_content, current_language, config
                    )
                    html_lines.append(highlighted_code)
                elif current_language == "robot":
                    highlighted_code = self._highlight_robot_framework(
                        code_content, config
                    )
                    html_lines.append(highlighted_code)
                else:
                    highlighted_code = self._escape_html(code_content)
                    html_lines.append(highlighted_code)

                i = j
                continue

            if line.startswith("|") and "|" in line[1:]:
                if not in_table:
                    in_table = True
                    table_lines = []
                table_lines.append(line)
                i += 1
                continue
            elif in_table:
                html_lines.append(self._render_table(table_lines))
                in_table = False
                just_finished_table = True
                table_lines = []

            stripped_line = line.strip()
            if stripped_line.startswith("# "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(
                    f"<h1>{self._parse_inline_formatting(stripped_line[2:])}</h1>"
                )
                prev_line_was_content = True
                prev_content_type = "header"
                i += 1
                continue
            elif stripped_line.startswith("## "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(
                    f"<h2>{self._parse_inline_formatting(stripped_line[3:])}</h2>"
                )
                prev_line_was_content = True
                prev_content_type = "header"
                i += 1
                continue
            elif stripped_line.startswith("### "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(
                    f"<h3>{self._parse_inline_formatting(stripped_line[4:])}</h3>"
                )
                prev_line_was_content = True
                prev_content_type = "header"
                i += 1
                continue
            elif stripped_line.startswith("#### "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(
                    f"<h4>{self._parse_inline_formatting(stripped_line[5:])}</h4>"
                )
                prev_line_was_content = True
                prev_content_type = "header"
                i += 1
                continue
            elif stripped_line.startswith("##### "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(
                    f"<h5>{self._parse_inline_formatting(stripped_line[6:])}</h5>"
                )
                prev_line_was_content = True
                prev_content_type = "header"
                i += 1
                continue
            elif stripped_line.startswith("###### "):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(
                    f"<h6>{self._parse_inline_formatting(stripped_line[7:])}</h6>"
                )
                prev_line_was_content = True
                prev_content_type = "header"
                i += 1
                continue
            elif line.startswith("---") or line.startswith("***"):
                html_lines.append("<hr>")
                i += 1
                continue
            elif line.strip().startswith("- "):
                if not in_list:
                    in_list = True
                    html_lines.append("<ul>")
                html_lines.append(
                    f"<li>{self._parse_inline_formatting(line.strip()[2:])}</li>"
                )
                prev_line_was_content = True
                i += 1
                continue
            elif not line.strip():
                if (
                    not in_list
                    and not in_table
                    and not just_finished_table
                    and prev_content_type != "paragraph"
                ):
                    next_non_empty = None
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip():
                            next_non_empty = lines[j]
                            break

                    if prev_line_was_content and (
                        not next_non_empty or not next_non_empty.startswith("```")
                    ):
                        html_lines.append("<br>")
                prev_line_was_content = False
                prev_content_type = None
                just_finished_table = False
                i += 1
                continue
            else:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False

                if line.strip():
                    html_lines.append(f"<p>{self._parse_inline_formatting(line)}</p>")
                    prev_line_was_content = True
                    prev_content_type = "paragraph"
                    just_finished_table = False
                i += 1

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

        text = self._escape_html(text)

        text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"__(.*?)__", r"<strong>\1</strong>", text)

        text = re.sub(r"\*(.*?)\*", r"<em>\1</em>", text)
        text = re.sub(r"_(.*?)_", r"<em>\1</em>", text)

        text = re.sub(r"\+\+(.*?)\+\+", r"<u>\1</u>", text)

        text = re.sub(r"~~(.*?)~~", r"<del>\1</del>", text)

        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)

        return text

    def _render_table(self, table_lines: List[str]) -> str:
        """Render a table from markdown-style table lines."""
        if not table_lines:
            return ""

        html_lines = ['<table class="doc-table">']

        for i, line in enumerate(table_lines):
            if re.match(r"^\|[\s\-\|]+\|$", line):
                continue

            cells = [cell.strip() for cell in line.split("|")[1:-1]]

            if i == 0:
                html_lines.append("<thead><tr>")
                for cell in cells:
                    html_lines.append(f"<th>{self._parse_inline_formatting(cell)}</th>")
                html_lines.append("</tr></thead><tbody>")
            else:
                html_lines.append("<tr>")
                for cell in cells:
                    html_lines.append(f"<td>{self._parse_inline_formatting(cell)}</td>")
                html_lines.append("</tr>")

        html_lines.append("</tbody></table>")
        return "\n".join(html_lines)

    def _highlight_with_pygments(
        self, code: str, language: str, config: dict = None
    ) -> str:
        """Use Pygments to highlight code with proper syntax highlighting."""
        if not PYGMENTS_AVAILABLE:
            return self._escape_html(code)

        if language == "robot":
            return self._highlight_robot_framework(code, config)

        try:
            lexer = get_lexer_by_name(language, stripall=True)
        except ClassNotFound:
            lexer = TextLexer()

        formatter = HtmlFormatter(
            nowrap=True,
            noclasses=True,
            style="default",
        )

        code = code.rstrip()

        highlighted = highlight(code, lexer, formatter)

        highlighted = highlighted.replace('<div class="highlight"><pre>', "").replace(
            "</pre></div>", ""
        )

        highlighted = highlighted.replace("#00F", "#ffe400")
        highlighted = highlighted.replace("#00f", "#ffe400")

        highlighted = highlighted.rstrip()

        return highlighted

    def _highlight_robot_framework(self, code: str, config: dict = None) -> str:
        """Custom Robot Framework syntax highlighting."""
        if not code:
            return ""

        code = code.rstrip()

        lines = code.split("\n")
        highlighted_lines = []

        for line in lines:
            highlighted_line = self._highlight_robot_line(line, config)
            highlighted_lines.append(highlighted_line)

        result = "\n".join(highlighted_lines)
        return result.rstrip()

    def _get_robot_framework_keywords(self, config: dict = None) -> list:
        """Get all Robot Framework keywords from built-in libraries (cached)."""
        if self._cached_keywords is not None:
            if self.library_info and self.library_info.keywords:
                library_keyword_names = [kw.name for kw in self.library_info.keywords]
                if any(kw not in self._cached_keywords for kw in library_keyword_names):
                    self._cached_keywords = None
                else:
                    return self._cached_keywords
            else:
                return self._cached_keywords

        try:
            from robot.libdocpkg import LibraryDocumentation

            all_keywords = []
            optional_libs = {
                "robot.libraries.Dialogs": "requires tkinter (GUI library)",
                "robot.libraries.Telnet": "requires telnetlib (removed in Python 3.13+)",
            }

            for lib in self.ROBOT_FRAMEWORK_LIBRARIES:
                try:
                    lib_doc = LibraryDocumentation(lib)
                    all_keywords.extend([kw.name for kw in lib_doc.keywords])
                except Exception as e:
                    if lib not in optional_libs:
                        print(f"Warning: Could not load {lib}: {e}")
                    continue

            if self.library_info and self.library_info.keywords:
                library_keyword_names = [kw.name for kw in self.library_info.keywords]
                all_keywords.extend(library_keyword_names)

            if config and "custom_keywords" in config:
                custom_keywords = config["custom_keywords"]
                if isinstance(custom_keywords, list):
                    all_keywords.extend(custom_keywords)

            all_keywords = sorted(set(all_keywords))
            self._cached_keywords = all_keywords
            return all_keywords

        except ImportError:
            print(
                "Error: robot.libdocpkg not available. Robot Framework must be installed."
            )
            self._cached_keywords = []
            return []

    def _highlight_robot_line(self, line: str, config: dict = None) -> str:
        """Highlight a single Robot Framework line with clean, non-overlapping highlighting."""
        if not line:
            return ""

        line = self._escape_html(line)

        if line.strip().startswith("#"):
            return f'<span style="color: #6a9955; font-style: italic;">{line}</span>'

        if line.strip().startswith("***"):
            return f'<span style="color: #569cd6; font-weight: bold;">{line}</span>'

        settings = sorted(
            self.ROBOT_FRAMEWORK_SETTINGS_KEYWORDS, key=len, reverse=True
        )
        for setting in settings:
            stripped_line = line.strip()
            if stripped_line.startswith(setting):
                setting_end_pos = len(setting)
                if (
                    setting_end_pos < len(stripped_line)
                    and stripped_line[setting_end_pos] == " "
                ):
                    value_part = stripped_line[setting_end_pos:].strip()
                    indent = line[: len(line) - len(line.lstrip())]
                    return f'{indent}<span style="color: #c586c0; font-weight: bold;">{setting}</span> {value_part}'
                elif setting_end_pos == len(stripped_line):
                    indent = line[: len(line) - len(line.lstrip())]
                    return f'{indent}<span style="color: #c586c0; font-weight: bold;">{setting}</span>'
                continue

        if (
            not line.startswith("    ")
            and not line.startswith("\t")
            and not line.startswith("***")
            and line.strip()
            and not line.startswith("[")
        ):
            return f'<span style="color: #dcdcaa; font-weight: bold;">{line}</span>'

        if line.startswith("    ") or line.startswith("\t"):
            indent = ""
            for i, char in enumerate(line):
                if char in " \t":
                    indent += char
                else:
                    break

            content = line[len(indent) :]

            robot_keywords = self._get_robot_framework_keywords(config)
            robot_keywords.extend(self.RESERVED_CONTROL_KEYWORDS)

            if (
                content.startswith("${")
                or content.startswith("@{")
                or content.startswith("&{")
            ):
                highlighted_content = self._highlight_variables_only(content, config)
                return f"{indent}{highlighted_content}"

            keyword_found = None
            rest_content = content

            sorted_keywords = sorted(robot_keywords, key=len, reverse=True)

            for keyword in sorted_keywords:
                if content.startswith(keyword):
                    next_char_pos = len(keyword)
                    if next_char_pos >= len(content) or content[next_char_pos] == " ":
                        keyword_found = keyword
                        rest_content = content[next_char_pos:]
                        break

            if keyword_found:
                if keyword_found in self.RESERVED_CONTROL_KEYWORDS:
                    keyword_color = "#ce9178"
                else:
                    keyword_color = "#4ec9b0"

                if rest_content:
                    rest_content = self._highlight_variables_only(rest_content, config)
                    return f'{indent}<span style="color: {keyword_color}; font-weight: bold;">{keyword_found}</span> {rest_content}'
                else:
                    return f'{indent}<span style="color: {keyword_color}; font-weight: bold;">{keyword_found}</span>'
            else:
                highlighted_content = self._highlight_variables_only(content, config)
                return f"{indent}{highlighted_content}"

        line = self._highlight_variables_only(line, config)
        return line

    def _highlight_variables_only(self, text: str, config: dict = None) -> str:
        """Highlight Robot Framework variables, keywords, and keyword arguments."""
        import re

        var_markers = {}
        var_counter = 0

        def mark_variable(match):
            nonlocal var_counter
            var = match.group(0)
            marker = f"__VAR_MARKER_{var_counter}__"
            var_markers[marker] = f'<span style="color: #9cdcfe;">{var}</span>'
            var_counter += 1
            return marker

        text = re.sub(r"\$\{[^}]+\}", mark_variable, text)
        text = re.sub(r"@\{[^}]+\}", mark_variable, text)
        text = re.sub(r"&\{[^}]+\}", mark_variable, text)

        robot_keywords = self._get_robot_framework_keywords(config)
        sorted_keywords = sorted(robot_keywords, key=len, reverse=True)

        keyword_markers = {}
        keyword_counter = 0

        for keyword in sorted_keywords:
            if keyword in text:
                marker_pattern = "__KW_MARKER_\\d+__"
                if not re.search(marker_pattern.replace("\\d+", ".*"), text):
                    escaped_keyword = re.escape(keyword)
                    pattern = r"\b" + escaped_keyword + r"(?=\s|$|[^a-zA-Z0-9_])"

                    def mark_keyword(match):
                        nonlocal keyword_counter
                        kw = match.group(0)
                        marker = f"__KW_MARKER_{keyword_counter}__"
                        keyword_markers[marker] = (
                            f'<span style="color: #4ec9b0; font-weight: bold;">{kw}</span>'
                        )
                        keyword_counter += 1
                        return marker

                    text = re.sub(pattern, mark_keyword, text, count=1)

        arg_markers = {}
        arg_counter = 0

        def mark_keyword_arg(match):
            nonlocal arg_counter
            arg_name = match.group(1)
            arg_value = match.group(2)
            if arg_value in var_markers:
                arg_value = var_markers[arg_value]
            elif arg_value in keyword_markers:
                arg_value = keyword_markers[arg_value]

            marker = f"__ARG_MARKER_{arg_counter}__"
            arg_markers[marker] = (
                f'<span style="color: #dcdcaa;">{arg_name}</span>={arg_value}'
            )
            arg_counter += 1
            return marker

        arg_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(__VAR_MARKER_\d+__|__KW_MARKER_\d+__|"[^"]*"|\'[^\']*\'|[^\s<]+)'
        text = re.sub(arg_pattern, mark_keyword_arg, text)

        for marker, html in var_markers.items():
            text = text.replace(marker, html)
        for marker, html in keyword_markers.items():
            text = text.replace(marker, html)
        for marker, html in arg_markers.items():
            text = text.replace(marker, html)

        def highlight_comment(match):
            comment = match.group(0)
            return f'<span style="color: #6a9955; font-style: italic;">{comment}</span>'

        parts = re.split(r"(<[^>]+>)", text)
        result_parts = []
        for part in parts:
            if part.startswith("<") and part.endswith(">"):
                result_parts.append(part)
            else:
                part = re.sub(r"(#.*)$", highlight_comment, part)
                result_parts.append(part)

        text = "".join(result_parts)

        return text

    def _get_module_attribute(
        self, attr_name: str, module_vars: dict, default: str
    ) -> str:
        """Get a module-level attribute value."""
        return module_vars.get(attr_name, default)

    def _get_module_docstring(self, tree: ast.AST) -> str:
        """Extract module-level docstring."""
        if (
            tree.body
            and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)
        ):
            return tree.body[0].value.value
        return ""

    def _extract_module_keywords(self, tree: ast.AST) -> List[KeywordInfo]:
        """Extract keywords from module-level functions."""
        keywords = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                keyword_name = None
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == "keyword":
                        keyword_name = self._function_name_to_keyword_name(node.name)
                        break
                    elif (
                        isinstance(decorator, ast.Call)
                        and isinstance(decorator.func, ast.Name)
                        and decorator.func.id == "keyword"
                    ):
                        if decorator.args and isinstance(
                            decorator.args[0], ast.Constant
                        ):
                            keyword_name = decorator.args[0].value
                        else:
                            keyword_name = self._function_name_to_keyword_name(
                                node.name
                            )
                        break

                if keyword_name:
                    docstring = ""
                    if (
                        node.body
                        and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)
                    ):
                        docstring = node.body[0].value.value

                    parameters = []
                    args_with_defaults = node.args.args[
                        len(node.args.args) - len(node.args.defaults) :
                    ]
                    defaults = node.args.defaults

                    for i, arg in enumerate(node.args.args):
                        if arg.arg != "self":
                            param_name = arg.arg
                            if arg.annotation:
                                param_type = self._extract_type_annotation(
                                    arg.annotation
                                )
                            else:
                                param_type = "Any"

                            param_str = f"{param_name}: {param_type}"
                            if arg in args_with_defaults:
                                default_idx = args_with_defaults.index(arg)
                                if default_idx < len(defaults):
                                    default_value = self._extract_default_value(
                                        defaults[default_idx]
                                    )
                                    param_str += f" = {default_value}"

                            parameters.append(param_str)

                    return_type = ""
                    if node.returns:
                        return_type = self._extract_type_annotation(node.returns)

                    keywords.append(
                        KeywordInfo(
                            name=keyword_name,
                            description=docstring,
                            example="",
                            parameters=parameters,
                            return_type=return_type,
                            line_number=node.lineno,
                        )
                    )
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
            if isinstance(annotation.value, ast.Name):
                return f"{annotation.value.id}.{annotation.attr}"
            return "Any"
        elif isinstance(annotation, ast.BinOp):
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
            if isinstance(subscript.value.value, ast.Name):
                base_type = f"{subscript.value.value.id}.{subscript.value.attr}"
                slice_content = self._extract_slice_content(subscript.slice)
                return f"{base_type}[{slice_content}]"
        return "Any"

    def _extract_slice_content(self, slice_node: ast.AST) -> str:
        """Extract content from slice node."""
        if isinstance(slice_node, ast.Index):
            return self._extract_type_annotation(slice_node.value)
        elif isinstance(slice_node, ast.Tuple):
            elts = []
            for elt in slice_node.elts:
                elts.append(self._extract_type_annotation(elt))
            return ", ".join(elts)
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
        return " | ".join(types)

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
            if isinstance(default_node.func, ast.Name):
                return f"{default_node.func.id}()"
            elif isinstance(default_node.func, ast.Attribute):
                if isinstance(default_node.func.value, ast.Name):
                    return f"{default_node.func.value.id}.{default_node.func.attr}()"
        elif isinstance(default_node, ast.Attribute):
            if isinstance(default_node.value, ast.Name):
                return f"{default_node.value.id}.{default_node.attr}"
        else:
            return "..."

    def _highlight_robot_syntax(self, line: str) -> str:
        """Apply syntax highlighting to Robot Framework code."""
        if not line:
            return ""

        line = self._escape_html(line)

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

        line = re.sub(
            r"^(\s{4,})([A-Za-z][A-Za-z0-9\s]*?)(\s+.*)?$",
            lambda m: f'{m.group(1)}<span class="robot-keywords">{m.group(2)}</span>{m.group(3) or ""}',
            line,
        )

        line = re.sub(
            r"(\$\{[^}]+\})", r'<span class="robot-variables">\1</span>', line
        )
        line = re.sub(r"(@\{[^}]+\})", r'<span class="robot-variables">\1</span>', line)
        line = re.sub(r"(&\{[^}]+\})", r'<span class="robot-variables">\1</span>', line)

        line = re.sub(r"(#.*)$", r'<span class="robot-comments">\1</span>', line)

        line = re.sub(
            r'(["\'])([^"\']*)\1', r'\1<span class="robot-strings">\2</span>\1', line
        )

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

    TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "libdoc.html"

    def __init__(self, library_info: LibraryInfo, parser=None, config: dict = None):
        self.library_info = library_info
        self.parser = parser
        self.config = config or {}

    @classmethod
    @lru_cache(maxsize=1)
    def _load_html_template(cls) -> str:
        try:
            return cls.TEMPLATE_PATH.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"HTML template not found at {cls.TEMPLATE_PATH}"
            ) from exc

    def _html_to_markdown(self, html_content: str) -> str:
        """Convert basic HTML tags to markdown format."""
        if not html_content:
            return ""
        
        # Convert code blocks with syntax highlighting
        html_content = re.sub(
            r'<div class="code-block"><pre class="language-([^"]+)">(.*?)</pre></div>',
            lambda m: f"```{m.group(1)}\n{self._strip_html_tags(m.group(2)).strip()}\n```",
            html_content,
            flags=re.DOTALL
        )
        
        # Convert inline code
        html_content = re.sub(r'<code>(.*?)</code>', r'`\1`', html_content)
        
        # Convert bold
        html_content = re.sub(r'<strong>(.*?)</strong>', r'**\1**', html_content)
        
        # Convert italic
        html_content = re.sub(r'<em>(.*?)</em>', r'*\1*', html_content)
        html_content = re.sub(r'<i>(.*?)</i>', r'*\1*', html_content)
        
        # Convert paragraphs
        html_content = re.sub(r'<p>(.*?)</p>', r'\1\n\n', html_content, flags=re.DOTALL)
        
        # Convert lists
        html_content = re.sub(r'<ul>(.*?)</ul>', r'\1', html_content, flags=re.DOTALL)
        html_content = re.sub(r'<ol>(.*?)</ol>', r'\1', html_content, flags=re.DOTALL)
        html_content = re.sub(r'<li>(.*?)</li>', r'- \1\n', html_content, flags=re.DOTALL)
        
        # Convert tables - basic conversion
        html_content = re.sub(r'<table[^>]*>(.*?)</table>', self._convert_table_to_markdown, html_content, flags=re.DOTALL)
        
        # Convert links
        html_content = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', html_content)
        
        # Convert headers
        html_content = re.sub(r'<h([1-6])>(.*?)</h[1-6]>', lambda m: '#' * int(m.group(1)) + ' ' + m.group(2) + '\n', html_content)
        
        # Strip remaining HTML tags
        html_content = self._strip_html_tags(html_content)
        
        # Clean up extra whitespace
        html_content = re.sub(r'\n{3,}', '\n\n', html_content)
        html_content = html_content.strip()
        
        return html_content
    
    def _strip_html_tags(self, text: str) -> str:
        """Remove HTML tags and decode entities."""
        # Decode HTML entities
        text = text.replace('&quot;', '"')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&nbsp;', ' ')
        
        # Remove HTML tags (including style attributes in spans)
        text = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '', text)
        
        return text
    
    def _convert_table_to_markdown(self, match) -> str:
        """Convert HTML table to markdown table."""
        table_html = match.group(1)
        
        # Extract rows
        rows = []
        for row_match in re.finditer(r'<tr>(.*?)</tr>', table_html, re.DOTALL):
            row_html = row_match.group(1)
            cells = []
            for cell_match in re.finditer(r'<t[dh][^>]*>(.*?)</t[dh]>', row_html, re.DOTALL):
                cell_content = self._strip_html_tags(cell_match.group(1)).strip()
                cells.append(cell_content)
            if cells:
                rows.append(cells)
        
        if not rows:
            return ""
        
        # Generate markdown table
        md_rows = []
        for i, row in enumerate(rows):
            md_row = '| ' + ' | '.join(row) + ' |'
            md_rows.append(md_row)
            if i == 0:  # Add separator after header
                separator = '| ' + ' | '.join(['---'] * len(row)) + ' |'
                md_rows.append(separator)
        
        return '\n'.join(md_rows) + '\n\n'

    def generate_markdown(self) -> str:
        """Generate markdown documentation."""
        md_content = []

        md_content.append(f"# {self.library_info.name}")
        md_content.append("")
        md_content.append(f"**Version:** {self.library_info.version}")
        md_content.append(f"**Scope:** {self.library_info.scope}")
        md_content.append("")

        if self.library_info.description:
            md_content.append("## Description")
            md_content.append("")
            md_content.append(self._html_to_markdown(self.library_info.description))
            md_content.append("")

        md_content.append("## Keywords")
        md_content.append("")

        for keyword in self.library_info.keywords:
            md_content.append(f"### {keyword.name}")
            md_content.append("")

            if keyword.description:
                md_content.append(self._html_to_markdown(keyword.description))
                md_content.append("")

            if keyword.parameters:
                md_content.append("**Parameters:**")
                md_content.append("")
                for param_name, param_type in keyword.parameters:
                    md_content.append(f"- `{param_name}` : `{param_type}`")
                md_content.append("")

            if keyword.return_type and keyword.return_type != "None":
                md_content.append(f"**Returns:** `{keyword.return_type}`")
                md_content.append("")

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
        template = self._load_html_template()

        keyword_list_items = []
        keyword_sections = []

        for keyword in self.library_info.keywords:
            keyword_id = keyword.name.lower().replace(" ", "-")
            keyword_list_items.append(
                f'<li><a href="#{keyword_id}">{keyword.name}</a></li>'
            )

            section_lines = [
                f'<div class="keyword-container" id="{keyword_id}">',
                '  <div class="keyword-name">',
                f'    <h2><a class="kw-name" href="#{keyword_id}">{keyword.name}</a></h2>',
                "  </div>",
                '  <div class="keyword-content">',
            ]

            has_overview = bool(
                keyword.parameters
                or (keyword.return_type and keyword.return_type != "None")
            )

            if has_overview:
                section_lines.append('    <div class="kw-overview">')

            if keyword.parameters:
                section_lines.extend(
                    [
                        '      <div class="args">',
                        "        <h4>Arguments</h4>",
                        '        <div class="arguments-list-container">',
                        '          <div class="arguments-list">',
                    ]
                )
                for param_name, param_type in keyword.parameters:
                    section_lines.append(
                        f'            <li><span class="arg-name">{param_name}</span> : <span class="arg-type">{param_type}</span></li>'
                    )
                section_lines.extend(
                    [
                        "          </div>",
                        "        </div>",
                        "      </div>",
                    ]
                )

            if keyword.return_type and keyword.return_type != "None":
                section_lines.extend(
                    [
                        '      <div class="return-type">',
                        "        <h4>Return Type</h4>",
                        f'        <span class="arg-type">{keyword.return_type}</span>',
                        "      </div>",
                    ]
                )

            if has_overview:
                section_lines.append("    </div>")
            else:
                section_lines.append('    <div style="margin-bottom: 1rem;"></div>')

            if keyword.description:
                description = keyword.description
                broken_image_pattern = r'!<a href="([^"]+)">([^<]+)</a>'

                def fix_broken_image(match):
                    url = match.group(1)
                    alt_text = match.group(2)
                    import html

                    alt_text = html.escape(alt_text)
                    return f'<img alt="{alt_text}" src="{url}" />'

                description = re.sub(
                    broken_image_pattern, fix_broken_image, description
                )

                section_lines.extend(
                    [
                        '    <div class="kw-docs">',
                        "      <h4>Documentation</h4>",
                        '      <div class="kwdoc doc">',
                        f"        {description}",
                        "      </div>",
                        "    </div>",
                    ]
                )

            section_lines.extend(
                [
                    "  </div>",
                    "</div>",
                ]
            )

            keyword_sections.append("\n".join(section_lines))

        intro_section = ""
        if self.library_info.description:
            if self.parser:
                processed_description = self.parser._parse_custom_syntax(
                    self.library_info.description
                )
            else:
                processed_description = self.library_info.description
            intro_section = (
                '<section class="keyword-container intro-section">'
                '<div class="keyword-name"><h2>Introduction</h2></div>'
                f'<div class="kw-overview"><div class="kw-docs"><div class="intro-content">{processed_description}</div></div></div>'
                "</section>"
            )

        metadata_pairs = []
        metadata_fields = [
            ("author", "Author"),
            ("maintainer", "Maintainer"),
            ("license", "License"),
            ("robot_framework", "Robot Framework"),
            ("python", "Python"),
        ]
        for key, label in metadata_fields:
            value = self.config.get(key)
            if not value:
                continue
            metadata_pairs.append(f"<span><strong>{label}:</strong> {value}</span>")

        library_meta = ""
        if metadata_pairs:
            library_meta = (
                '<div class="hero-meta meta-grid">' + "".join(metadata_pairs) + "</div>"
            )

        hero_buttons = []
        library_url = self.config.get("library_url", "")
        if library_url:
            hero_buttons.append(
                f'<a class="btn btn-primary" href="{library_url}" target="_blank" rel="noopener noreferrer">'
                '<svg height="18" aria-hidden="true" viewBox="0 0 24 24" width="18" fill="currentColor">'
                '<path d="M12 2a10 10 0 1 0 10 10A10.011 10.011 0 0 0 12 2Zm6.93 9H16.2a17.459 17.459 0 0 0-1.18-4.495A7.953 7.953 0 0 1 18.93 11Zm-7.93 8a15.417 15.417 0 0 1-1.458-4h2.916A15.417 15.417 0 0 1 11 19Zm-1.458-6a13.7 13.7 0 0 1 0-2h2.916a13.7 13.7 0 0 1 0 2Zm-3.25-2a13.116 13.116 0 0 1 .4-2h2.365a13.472 13.472 0 0 0 0 4H6.692a13.116 13.116 0 0 1-.4-2Zm4.708-6a15.417 15.417 0 0 1 1.458 4h-2.916A15.417 15.417 0 0 1 11 5Zm-2.02.505A17.459 17.459 0 0 0 7.8 11H5.07A7.953 7.953 0 0 1 8.98 5.505ZM5.07 13H7.8a17.459 17.459 0 0 0 1.18 4.495A7.953 7.953 0 0 1 5.07 13Zm9.95 4.495c.42-1.282.728-2.64.892-3.995h2.188a7.953 7.953 0 0 1-3.08 3.995Z"></path>'
                "</svg>"
                "<span>Library Website</span>"
                "</a>"
            )

        github_url = self.config.get("github_url", "")
        if github_url:
            hero_buttons.append(
                f'<a class="btn btn-ghost" href="{github_url}" target="_blank" rel="noopener noreferrer">'
                '<svg height="18" aria-hidden="true" viewBox="0 0 24 24" width="18" '
                'data-view-component="true" class="octicon octicon-mark-github v-align-middle">'
                '<path fill="currentColor" d="M12 1C5.923 1 1 5.923 1 12c0 4.867 3.149 8.979 7.521 '
                "10.436.55.096.756-.233.756-.522 0-.262-.013-1.128-.013-2.049-2.764.509-3.479-.674-3.699-1.292-.124-.317-.66-1.293-1.127-1.554-.385-.207-.936-.715-.014-.729.866-.014 "
                "1.485.797 1.691 1.128.99 1.663 2.571 1.196 3.204.907.096-.715.385-1.196.701-1.471-2.448-.275-5.005-1.224-5.005-5.432 "
                "0-1.196.426-2.186 1.128-2.956-.111-.275-.496-1.402.11-2.915 0 0 .921-.288 3.024 1.128a10.193 10.193 0 0 1 "
                "2.75-.371c.936 0 1.871.123 2.75.371 2.104-1.43 3.025-1.128 3.025-1.128.605 1.513.221 2.64.111 "
                "2.915.701.77 1.127 1.747 1.127 2.956 0 4.222-2.571 5.157-5.019 5.432.399.344.743 1.004.743 2.035 "
                '0 1.471-.014 2.654-.014 3.025 0 .289.206.632.756.522C19.851 20.979 23 16.854 23 12c0-6.077-4.922-11-11-11Z"></path>'
                "</svg>"
                "<span>View on GitHub</span>"
                "</a>"
            )

        support_email = self.config.get("support_email")
        if support_email:
            hero_buttons.append(
                f'<a class="btn btn-ghost" href="mailto:{support_email}">'
                '<svg height="18" aria-hidden="true" viewBox="0 0 24 24" width="18" fill="currentColor">'
                '<path d="M19.25 4H4.75A2.75 2.75 0 0 0 2 6.75v10.5A2.75 2.75 0 0 0 4.75 20h14.5A2.75 2.75 0 0 0 '
                "22 17.25V6.75A2.75 2.75 0 0 0 19.25 4Zm0 1.5c.129 0 .252.027.363.076L12 11.14 4.387 5.076A1.25 1.25 0 "
                "0 1 4.75 5.5Zm0 13H4.75A1.25 1.25 0 0 1 3.5 17.25V7.46l7.87 6.04a.75.75 0 0 0 .88 "
                '0l7.87-6.04v9.79A1.25 1.25 0 0 1 19.25 18.5Z"></path>'
                "</svg>"
                "<span>Contact Support</span>"
                "</a>"
            )

        hero_actions = ""
        if hero_buttons:
            hero_actions = (
                '<div class="hero-actions">' + "".join(hero_buttons) + "</div>"
            )

        github_issue_button = ""
        github_url = self.config.get("github_url", "")
        if github_url:
            issues_url = f"{github_url.rstrip('/')}/issues/new"
            github_issue_button = (
                '<p style="margin-top: 1rem;">'
                f'<a class="btn btn-primary" href="{issues_url}" target="_blank" rel="noopener noreferrer">'
                "Open an Issue on GitHub"
                "</a>"
                "</p>"
            )

        sample_usage_code = f"""*** Settings ***
Library    {self.library_info.name}

*** Test Cases ***
Example
    [Documentation]    Demonstrates using {self.library_info.name}
    # add your keyword calls here"""

        if self.parser:
            sample_usage_highlighted = self.parser._highlight_robot_framework(
                sample_usage_code, self.config
            )
        else:
            sample_usage_highlighted = sample_usage_code

        replacements = {
            "{{LIBRARY_NAME}}": self.library_info.name,
            "{{VERSION}}": self.library_info.version,
            "{{SCOPE}}": self.library_info.scope,
            "{{KEYWORD_COUNT}}": str(len(self.library_info.keywords)),
            "{{KEYWORD_LIST}}": "\n        ".join(keyword_list_items),
            "{{INTRO_SECTION}}": intro_section,
            "{{KEYWORDS_SECTION}}": "\n        ".join(keyword_sections),
            "{{LAST_UPDATE}}": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "{{LIBRARY_META}}": library_meta,
            "{{HERO_ACTIONS}}": hero_actions,
            "{{SAMPLE_USAGE}}": sample_usage_highlighted,
            "{{GITHUB_ISSUE_BUTTON}}": github_issue_button,
        }

        html_output = template
        for placeholder, value in replacements.items():
            html_output = html_output.replace(placeholder, value or "")

        return html_output


def load_config(config_file: str) -> dict:
    """Load configuration from JSON file."""
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        if RICH_AVAILABLE:
            console.print(
                f"[yellow]Warning:[/yellow] Invalid JSON in config file {config_file}: {e}"
            )
        else:
            print(f"Warning: Invalid JSON in config file {config_file}: {e}")
        return {}
    except Exception as e:
        if RICH_AVAILABLE:
            console.print(
                f"[red]Error:[/red] Could not load config file {config_file}: {e}"
            )
        else:
            print(f"Error: Could not load config file {config_file}: {e}")
        return {}


def main():
    """Main function to run the documentation parser."""
    parser = argparse.ArgumentParser(
        description="Generate professional documentation from Robot Framework library files",
        epilog="""
Examples:
  # Generate HTML documentation (default)
  python src/docgen.py my_library.py -o docs.html -c config.json
  
  # Generate Markdown documentation
  python src/docgen.py my_library.py -f markdown -o README.md
  
  # Generate with default settings (HTML format)
  python src/docgen.py my_library.py

For more information, visit: https://github.com/deekshith-poojary98/robotframework-docgen
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input_file",
        help="Path to the Python library file containing Robot Framework keywords"
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Output file path. If not specified, defaults to input_file.html (for HTML) or input_file.md (for markdown)"
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["markdown", "html"],
        default="html",
        help="Output format: 'markdown' for Markdown files, 'html' for HTML documentation (default: html)"
    )
    parser.add_argument(
        "-c",
        "--config",
        metavar="FILE",
        help="Path to JSON configuration file. Optional fields include: github_url, library_url, support_email, author, maintainer, license, robot_framework, python, custom_keywords"
    )

    args = parser.parse_args()

    config = {}
    if args.config:
        config = load_config(args.config)

    doc_parser = RobotFrameworkDocParser(config)
    try:
        library_info = doc_parser.parse_file(args.input_file)
    except Exception as e:
        if RICH_AVAILABLE:
            console.print(f"[red]Error:[/red] Failed to parse file: {e}")
        else:
            print(f"Error parsing file: {e}")
        return 1

    if len(library_info.keywords) == 0:
        if RICH_AVAILABLE:
            error_text = Text()
            error_text.append("No keywords found in the library file.\n\n", style="red")
            error_text.append("Make sure to use the ", style="")
            error_text.append("@keyword", style="bold yellow")
            error_text.append(" decorator from ", style="")
            error_text.append("robot.api.deco", style="bold cyan")
            error_text.append(
                " to mark your functions as Robot Framework keywords.\n\n", style=""
            )
            error_text.append("Example:\n", style="bold")
            error_text.append("    from robot.api.deco import keyword\n\n", style="dim")
            error_text.append(
                "    # Option 1: Use function name as keyword name\n", style="dim"
            )
            error_text.append("    @keyword\n", style="cyan")
            error_text.append("    def my_keyword(self, arg1):\n", style="")
            error_text.append('        """Documentation here."""\n', style="dim")
            error_text.append("        pass\n\n", style="")
            error_text.append(
                "    # Option 2: Specify custom keyword name\n", style="dim"
            )
            error_text.append('    @keyword("Custom Keyword Name")\n', style="cyan")
            error_text.append("    def my_function(self, arg1):\n", style="")
            error_text.append('        """Documentation here."""\n', style="dim")
            error_text.append("        pass\n", style="")

            console.print(
                Panel(
                    error_text,
                    title="[bold red]No Keywords Found[/bold red]",
                    border_style="red",
                )
            )
        else:
            print("Error: No keywords found in the library file.")
            print(
                "Make sure to use the @keyword decorator from robot.api.deco to mark your functions as Robot Framework keywords."
            )
            print("\nExample:")
            print("    from robot.api.deco import keyword")
            print("    # Option 1: Use function name as keyword name")
            print("    @keyword")
            print("    def my_keyword(self, arg1):")
            print('        """Documentation here."""')
            print("        pass")
            print("    # Option 2: Specify custom keyword name")
            print('    @keyword("Custom Keyword Name")')
            print("    def my_function(self, arg1):")
            print('        """Documentation here."""')
            print("        pass")
        return 1

    doc_generator = DocumentationGenerator(library_info, doc_parser, config)

    if args.format == "markdown":
        content = doc_generator.generate_markdown()
        output_file = args.output or f"{Path(args.input_file).stem}.md"
    else:
        content = doc_generator.generate_html()
        output_file = args.output or f"{Path(args.input_file).stem}.html"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    if RICH_AVAILABLE:
        total_keywords = len(library_info.keywords)
        custom_keywords_count = len(config.get("custom_keywords", [])) if config else 0

        summary_text = Text()
        summary_text.append("✓ ", style="green")
        summary_text.append(f"Parsed {total_keywords} keywords from ", style="")
        summary_text.append(library_info.name, style="bold cyan")

        if custom_keywords_count > 0:
            summary_text.append(
                f"\n✓ Added {custom_keywords_count} custom keywords", style="green"
            )

        summary_text.append(
            f"\n✓ Generated {args.format.upper()} documentation", style="green"
        )
        summary_text.append(f"\n  → {output_file}", style="dim")

        console.print(
            Panel(
                summary_text,
                title="[bold green]Documentation Generated[/bold green]",
                border_style="green",
            )
        )
    else:
        print(
            f"✓ Parsed {len(library_info.keywords)} keywords from {library_info.name}"
        )
        print(f"✓ Documentation generated: {output_file}")

    return 0


if __name__ == "__main__":
    exit(main())
