#!/usr/bin/env python3
"""
Documentation Parser for Robot Framework Libraries

This parser reads Python files containing Robot Framework library classes
and generates comprehensive documentation from their docstrings.
"""

import ast
import re
import textwrap
import enum
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field

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
    parameter_enums: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    """Dictionary mapping parameter names to Enum information.
    
    Structure: {
        'param_name': {
            'type_name': 'MyEnum',
            'members': [
                {'name': 'ValueA', 'value': 123},
                {'name': 'ValueB', 'value': 456}
            ],
            'default': 'ValueA'  # Optional, if parameter has default
        }
    }
    """
    parameter_defaults: Dict[str, str] = field(default_factory=dict)
    """Dictionary mapping parameter names to their default value representations.
    
    Structure: {
        'param_name': 'default_value_string'
    }
    """
    parameter_docs: Dict[str, str] = field(default_factory=dict)
    """HTML documentation snippets keyed by parameter name (Libdoc Argument.doc)."""
    return_doc: str = ""
    """HTML documentation for the keyword return value when available."""
    tags: List[str] = field(default_factory=list)
    """Robot Framework keyword tags from Libdoc when available."""
    source: str = ""
    """Filesystem path where this keyword is defined (Libdoc per-keyword source)."""


@dataclass
class InitInfo:
    """Library constructor / import argument documentation."""

    description: str = ""
    parameters: List[Tuple[str, str]] = field(default_factory=list)
    parameter_defaults: Dict[str, str] = field(default_factory=dict)
    parameter_docs: Dict[str, str] = field(default_factory=dict)
    parameter_enums: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class LibraryInfo:
    """Information about a Robot Framework library or resource file."""

    name: str
    version: str
    scope: str
    description: str
    keywords: List[KeywordInfo]
    source_type: str = "LIBRARY"
    """Origin of the documented source: LIBRARY, RESOURCE, or SUITE."""
    inits: List[InitInfo] = field(default_factory=list)
    """Library import/constructor signatures derived from Libdoc inits when available."""
    source: str = ""
    """Filesystem path of the parsed library/resource file when known."""


class RobotFrameworkDocParser:
    """Parser for Robot Framework library documentation."""

    # Robot Framework resource / suite file extensions supported by Libdoc.
    ROBOT_SOURCE_EXTENSIONS = {
        ".resource",
        ".robot",
        ".txt",
        ".tsv",
        ".rst",
        ".rest",
    }
    
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
        "SKIP",
        "GROUP",
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
        "Name",
        "Test Tags",
    ]

    def __init__(self, config: dict = None):
        self.library_info = None
        self._cached_keywords = None
        # Keyword names known while docs are still being parsed (before
        # library_info is assigned). Lets the highlighter match this library's
        # keywords in intro/docstring ```robotframework``` fences.
        self._pending_library_keywords: Optional[List[str]] = None
        self._last_libdoc_error: Optional[str] = None
        self.config = config
        self._identifier_pattern = re.compile(r"\b[A-Za-z0-9]*_[A-Za-z0-9_]*\b")

    def _set_pending_library_keywords(self, names: List[str]) -> None:
        self._pending_library_keywords = list(names)
        self._cached_keywords = None

    def _clear_pending_library_keywords(self) -> None:
        self._pending_library_keywords = None
        self._cached_keywords = None

    def _function_name_to_keyword_name(self, function_name: str) -> str:
        """Convert function name to keyword name by removing underscores and title casing.

        Examples:
            my_keyword -> My Keyword
            open_workbook -> Open Workbook
            get_sheet_index -> Get Sheet Index
        """
        return function_name.replace("_", " ").title()

    @classmethod
    def _is_robot_source_file(cls, file_path: str) -> bool:
        """Return True when the path looks like a Robot Framework resource or suite file."""
        return Path(file_path).suffix.lower() in cls.ROBOT_SOURCE_EXTENSIONS

    def parse_file(self, file_path: str) -> LibraryInfo:
        """
        Parse a Python library or Robot Framework resource/suite file.

        Uses Robot Framework's LibraryDocumentation API where possible,
        falling back to AST parsing for Python libraries when the API cannot
        be used (e.g., type hints, custom docstring processing).
        """
        if self._is_robot_source_file(file_path):
            library_info = self._parse_robot_source_with_libdoc(file_path)
        else:
            # Try to use Robot Framework's LibraryDocumentation API first
            library_info = self._parse_with_libdoc_api(file_path)

            if library_info is None:
                # Fallback to AST parsing if LibraryDocumentation API doesn't work
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()

                tree = ast.parse(content)
                module_globals = self._execute_module_safely(file_path)
                library_info = self._extract_library_info(tree, file_path, module_globals)

        if library_info is not None and not getattr(library_info, "source", None):
            library_info.source = file_path
        self.library_info = library_info
        self._cached_keywords = None
        return library_info

    @staticmethod
    def _tags_from_libdoc_keyword(kw_doc) -> List[str]:
        """Normalize Libdoc keyword tags to a list of strings."""
        raw = getattr(kw_doc, "tags", None)
        if not raw:
            return []
        try:
            return [str(tag).strip() for tag in raw if str(tag).strip()]
        except TypeError:
            return []

    @staticmethod
    def _source_from_libdoc_keyword(kw_doc) -> str:
        """Per-keyword source path from Libdoc (falls back to empty)."""
        raw = getattr(kw_doc, "source", None)
        if raw:
            return str(raw)
        try:
            data = kw_doc.to_dictionary()
        except Exception:
            return ""
        return str(data.get("source") or "") if isinstance(data, dict) else ""

    def _parse_robot_source_with_libdoc(self, file_path: str) -> LibraryInfo:
        """
        Parse a .resource / .robot (or other Libdoc-supported) Robot source file.

        These files must not fall through to Python AST parsing.
        """
        from robot.libdocpkg import LibraryDocumentation

        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Robot source file not found: {file_path}")

        try:
            lib_doc = LibraryDocumentation(str(path.resolve()))
        except Exception as exc:
            raise ValueError(
                f"Failed to parse Robot Framework source '{file_path}': {exc}"
            ) from exc

        source_type = (getattr(lib_doc, "type", None) or "RESOURCE").upper()
        if source_type not in {"LIBRARY", "RESOURCE", "SUITE"}:
            source_type = "RESOURCE"

        public_keyword_names = [
            (kw_doc.name or "")
            for kw_doc in lib_doc.keywords
            if not getattr(kw_doc, "private", False)
            and not (kw_doc.name or "").startswith("_")
        ]
        self._set_pending_library_keywords(public_keyword_names)
        try:
            keywords = []
            for kw_doc in lib_doc.keywords:
                # Skip private keywords (robot:private / Libdoc private flag) and
                # underscore-prefixed helpers, which are conventionally private.
                keyword_name = kw_doc.name or ""
                if getattr(kw_doc, "private", False) or keyword_name.startswith("_"):
                    continue

                parameters, parameter_defaults, libdoc_return = self._parameters_from_libdoc_args(
                    getattr(kw_doc, "args", None)
                )
                parameter_docs = self._parameter_docs_from_libdoc_object(kw_doc)
                libdoc_return_type, return_doc = self._return_meta_from_libdoc_keyword(kw_doc)
                description, example = self._parse_docstring(kw_doc.doc or "", self.config)
                keywords.append(
                    KeywordInfo(
                        name=keyword_name,
                        description=description,
                        example=example,
                        parameters=parameters,
                        return_type=libdoc_return or libdoc_return_type or "None",
                        line_number=getattr(kw_doc, "lineno", 0) or 0,
                        parameter_defaults=parameter_defaults,
                        parameter_docs=parameter_docs,
                        return_doc=return_doc,
                        tags=self._tags_from_libdoc_keyword(kw_doc),
                        source=self._source_from_libdoc_keyword(kw_doc),
                    )
                )

            description = self._normalize_library_description(lib_doc.doc or "")
        finally:
            self._clear_pending_library_keywords()

        return LibraryInfo(
            name=lib_doc.name or path.stem,
            version=lib_doc.version or "",
            scope=lib_doc.scope or "GLOBAL",
            description=description,
            keywords=keywords,
            source_type=source_type,
            inits=self._inits_from_libdoc(lib_doc),
            source=str(path.resolve()),
        )
    
    @staticmethod
    def _is_dynamic_library_class(cls: type) -> bool:
        """Return True for DynamicCore / get_keyword_names-style library classes."""
        for base in getattr(cls, "__mro__", ()):
            if getattr(base, "__name__", "") in {
                "DynamicCore",
                "HybridCore",
                "StaticCore",
            }:
                return True
        get_names = getattr(cls, "get_keyword_names", None)
        return callable(get_names)

    @staticmethod
    def _ast_base_name(base: ast.AST) -> str:
        if isinstance(base, ast.Name):
            return base.id
        if isinstance(base, ast.Attribute):
            return base.attr
        return ""

    def _runtime_library_class_score(self, cls: type) -> int:
        """Prefer DynamicCore aggregators over leaf ``@keyword`` component classes."""
        score = 0
        if self._is_dynamic_library_class(cls):
            score += 100
        if not cls.__name__.startswith("_"):
            score += 5
        if hasattr(cls, "ROBOT_LIBRARY_SCOPE") or hasattr(cls, "ROBOT_LIBRARY_VERSION"):
            score += 10
        for name, member in vars(cls).items():
            if name.startswith("_"):
                continue
            if callable(member) and hasattr(member, "robot_name"):
                score += 1
        return score

    def _ast_library_class_score(self, class_node: ast.ClassDef) -> int:
        """AST counterpart of :meth:`_runtime_library_class_score`."""
        score = 0
        if not class_node.name.startswith("_"):
            score += 5
        for base in class_node.bases:
            if self._ast_base_name(base) in {"DynamicCore", "HybridCore", "StaticCore"}:
                score += 100
                break
        for node in class_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.startswith(
                        "ROBOT_LIBRARY_"
                    ):
                        score += 10
            if isinstance(node, ast.FunctionDef):
                if node.name == "get_keyword_names":
                    score += 50
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == "keyword":
                        score += 1
                    elif (
                        isinstance(decorator, ast.Call)
                        and isinstance(decorator.func, ast.Name)
                        and decorator.func.id == "keyword"
                    ):
                        score += 1
        return score

    _NON_PACKAGE_DIR_NAMES = frozenset(
        {
            "",
            "/",
            "Users",
            "home",
            "tmp",
            "var",
            "private",
            "Desktop",
            "Documents",
            "Downloads",
            "Library",
            "Applications",
        }
    )

    def _ensure_library_import_paths(self, file_path: str) -> None:
        """Put the library directory and package parents on ``sys.path``."""
        import sys
        import os

        abs_path = Path(file_path).resolve()
        candidates = [str(abs_path.parent), os.getcwd()]
        current = abs_path.parent
        seen_non_package = False
        for _ in range(6):
            if current.name in self._NON_PACKAGE_DIR_NAMES:
                break
            parent = current.parent
            candidates.append(str(parent))
            if parent == current:
                break
            has_init = (current / "__init__.py").exists()
            if not has_init:
                if seen_non_package:
                    break
                seen_non_package = True
            current = parent

        for directory in candidates:
            if directory and directory not in sys.path:
                sys.path.insert(0, directory)

    def _module_name_candidates(self, file_path: str) -> List[str]:
        """Build dotted import names from a file path (deepest package first)."""
        abs_path = Path(file_path).resolve()
        parts = [abs_path.stem]
        names = [abs_path.stem]
        current = abs_path.parent
        seen_non_package = False
        for _ in range(6):
            if current.name in self._NON_PACKAGE_DIR_NAMES:
                break
            if current.parent == current:
                break
            parts.insert(0, current.name)
            names.append(".".join(parts))
            has_init = (current / "__init__.py").exists()
            if not has_init:
                # Allow one namespace-package level (e.g. ``sample_libs``).
                if seen_non_package:
                    break
                seen_non_package = True
            current = current.parent
        # Prefer longer (more specific) package paths first.
        return list(dict.fromkeys(reversed(names)))

    def _import_library_module(
        self, file_path: str
    ) -> Tuple[Optional[Any], Optional[str]]:
        """Import a library module, preferring package imports over file loads."""
        import sys
        import importlib
        import importlib.util

        self._ensure_library_import_paths(file_path)
        abs_path = Path(file_path).resolve()

        for module_name in self._module_name_candidates(file_path):
            try:
                if module_name in sys.modules:
                    module = sys.modules[module_name]
                else:
                    module = importlib.import_module(module_name)
                module_file = getattr(module, "__file__", None)
                if module_file and Path(module_file).resolve() == abs_path:
                    return module, module_name
            except Exception:
                continue

        # Flat-file fallback when package imports are unavailable.
        file_name = abs_path.stem
        try:
            spec = importlib.util.spec_from_file_location(file_name, str(abs_path))
            if spec is None or spec.loader is None:
                return None, None
            module = importlib.util.module_from_spec(spec)
            sys.modules[file_name] = module
            spec.loader.exec_module(module)
            return module, file_name
        except Exception as exc:
            self._last_libdoc_error = str(exc)
            return None, None

    def _candidate_library_classes(
        self, module: Any, module_name: str
    ) -> List[type]:
        """Return library classes defined in ``module``, highest score first."""
        classes: List[type] = []
        for attr_name in dir(module):
            if attr_name.startswith("_"):
                continue
            try:
                attr = getattr(module, attr_name)
            except Exception:
                continue
            if not isinstance(attr, type):
                continue
            if getattr(attr, "__module__", None) not in {module_name, module.__name__}:
                continue
            if self._runtime_library_class_score(attr) <= 0 and not self._is_dynamic_library_class(
                attr
            ):
                # Skip unrelated imported types with no RF signals.
                has_robot_keyword = any(
                    callable(getattr(attr, name, None))
                    and hasattr(getattr(attr, name, None), "robot_name")
                    for name in dir(attr)
                )
                if not has_robot_keyword:
                    continue
            classes.append(attr)
        classes.sort(key=self._runtime_library_class_score, reverse=True)
        return classes

    def _init_arg_placeholders(self, cls: type) -> List[str]:
        """Build Libdoc ``::`` placeholders for required ``__init__`` arguments."""
        import inspect

        try:
            signature = inspect.signature(cls.__init__)
        except (TypeError, ValueError):
            return []

        placeholders: List[str] = []
        for name, param in signature.parameters.items():
            if name == "self":
                continue
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue
            if param.default is not inspect.Parameter.empty:
                continue

            annotation = param.annotation
            ann_name = ""
            if annotation is not inspect.Parameter.empty:
                ann_name = getattr(annotation, "__name__", str(annotation)).lower()

            lowered = name.lower()
            if "url" in lowered or "uri" in lowered:
                placeholders.append("http://example.invalid")
            elif ann_name in {"int", "float"}:
                placeholders.append("0")
            elif ann_name == "bool":
                placeholders.append("False")
            else:
                placeholders.append("placeholder")
        return placeholders

    def _libdoc_targets_for_class(self, module_name: str, cls: type) -> List[str]:
        """Libdoc import targets for a class, with init-arg placeholders when needed."""
        base = f"{module_name}.{cls.__name__}"
        placeholders = self._init_arg_placeholders(cls)
        targets = []
        if placeholders:
            targets.append(f"{base}::{'::'.join(placeholders)}")
        targets.append(base)
        return targets

    def _library_documentation_from_path(self, file_path: str):
        """
        Resolve LibraryDocumentation for a Python library file.

        File-path Libdoc often returns zero keywords for DynamicCore aggregators
        (especially package modules). Prefer class-qualified targets and supply
        ``::`` init placeholders when the constructor requires arguments.
        """
        from robot.libdocpkg import LibraryDocumentation

        self._ensure_library_import_paths(file_path)
        errors: List[str] = []
        best = None
        best_score = -1

        def consider(target: str) -> None:
            nonlocal best, best_score
            try:
                doc = LibraryDocumentation(target)
            except Exception as exc:
                errors.append(f"{target}: {exc}")
                return
            score = len(getattr(doc, "keywords", []) or [])
            # Prefer a target that actually exposes keywords.
            if score > best_score:
                best = doc
                best_score = score

        consider(str(Path(file_path).resolve()))
        consider(file_path)

        # Always attempt class-qualified resolution when file-path Libdoc is empty
        # or failed — this is the DynamicCore / required-init fix for issue #7.
        if best is None or best_score == 0:
            module, module_name = self._import_library_module(file_path)
            if module is not None and module_name:
                classes = self._candidate_library_classes(module, module_name)
                # Prefer DynamicCore / get_keyword_names aggregators. Trying leaf
                # ``@keyword`` component classes first produces the wrong library
                # when the aggregator fails to initialize (GitHub issue #7).
                dynamic_classes = [
                    cls for cls in classes if self._is_dynamic_library_class(cls)
                ]
                to_try = dynamic_classes if dynamic_classes else classes
                for cls in to_try:
                    for target in self._libdoc_targets_for_class(module_name, cls):
                        consider(target)
                    if best_score > 0:
                        break

        if errors and (best is None or best_score == 0):
            self._last_libdoc_error = errors[-1]
        elif best is not None and best_score > 0:
            self._last_libdoc_error = None

        if best is None or best_score == 0:
            return None
        return best

    def _parse_with_libdoc_api(self, file_path: str) -> Optional[LibraryInfo]:
        """
        Parse library using Robot Framework's LibraryDocumentation API.
        
        Returns LibraryInfo if successful, None if API cannot be used.
        This method uses the same public API that Libdoc uses internally.
        
        NOTE: LibraryDocumentation requires the library to be importable.
        If the library cannot be imported or LibraryDocumentation fails,
        this returns None and the code falls back to AST parsing.
        """
        self._last_libdoc_error = None
        try:
            import sys
            import importlib.util

            file_name = Path(file_path).stem
            lib_doc = self._library_documentation_from_path(file_path)
            if lib_doc is None:
                return None

            # Extract library metadata from LibraryDocumentation (using public API)
            library_name = lib_doc.name
            library_version = lib_doc.version or ""
            library_scope = lib_doc.scope or "TEST"

            # If no keywords found via API, fall back to AST parsing
            # This can happen if the library structure doesn't match what LibraryDocumentation expects
            if len(lib_doc.keywords) == 0:
                return None

            # Make this library's keyword names available to the highlighter while
            # rendering the intro and keyword docstrings (library_info is set later).
            self._set_pending_library_keywords(
                [kw.name for kw in lib_doc.keywords if kw.name]
            )
            try:
                library_description = self._normalize_library_description(
                    lib_doc.doc or ""
                )

                # Extract keywords from LibraryDocumentation
                keywords = []
                # We still need AST for type hints (not available in LibraryDocumentation API)
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()
                tree = ast.parse(content)

                # Get module globals for type resolution
                # Try to get the module that was already loaded for LibraryDocumentation
                module_globals = {}
                try:
                    module, module_name = self._import_library_module(file_path)
                    if module is not None:
                        module_globals = {
                            name: getattr(module, name)
                            for name in dir(module)
                            if not name.startswith("_")
                        }
                    elif file_name in sys.modules:
                        loaded_module = sys.modules[file_name]
                        module_globals = {
                            name: getattr(loaded_module, name)
                            for name in dir(loaded_module)
                            if not name.startswith("_")
                        }
                    else:
                        spec = importlib.util.spec_from_file_location(file_name, file_path)
                        if spec and spec.loader:
                            temp_module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(temp_module)
                            module_globals = {
                                name: getattr(temp_module, name)
                                for name in dir(temp_module)
                                if not name.startswith("_")
                            }
                except Exception:
                    pass

                # Map keyword names from LibraryDocumentation to AST nodes for type hints
                keyword_ast_map = self._build_keyword_ast_map(tree)

                for kw_doc in lib_doc.keywords:
                    keyword_name = kw_doc.name
                    keyword_docstring = kw_doc.doc or ""
                
                    # Get type hints from AST (not available in LibraryDocumentation API)
                    # NOTE: LibraryDocumentation provides kw_doc.args but not type annotations
                    parameters = []
                    parameter_enums = {}
                    parameter_defaults = {}
                    return_type = "None"
                    line_number = kw_doc.lineno if hasattr(kw_doc, 'lineno') else 0
                
                    if keyword_name in keyword_ast_map:
                        func_node = keyword_ast_map[keyword_name]
                        for param_name, annotation, default_value in self._iter_function_parameters(
                            func_node
                        ):
                            self._append_signature_parameter(
                                parameters,
                                parameter_defaults,
                                parameter_enums,
                                param_name,
                                annotation,
                                default_value,
                                module_globals,
                            )

                        if func_node.returns:
                            return_type = self._ast_type_to_string(func_node.returns)
                    else:
                        # Keyword is not in the AST map (auto keywords, camelCase names,
                        # or module-level keywords). Read arguments from Libdoc instead of
                        # aborting the whole library parse.
                        parameters, parameter_defaults, libdoc_return = (
                            self._parameters_from_libdoc_args(getattr(kw_doc, "args", None))
                        )
                        if libdoc_return:
                            return_type = libdoc_return

                    parameter_docs = self._parameter_docs_from_libdoc_object(kw_doc)
                    libdoc_return_type, return_doc = self._return_meta_from_libdoc_keyword(
                        kw_doc
                    )
                    if (not return_type or return_type == "None") and libdoc_return_type:
                        return_type = libdoc_return_type
                
                    # Parse docstring with our custom markdown processing
                    # NOTE: We preserve our custom docstring parsing for markdown support
                    description, example = self._parse_docstring(keyword_docstring, self.config)
                
                    keywords.append(
                        KeywordInfo(
                            name=keyword_name,
                            description=description,
                            example=example,
                            parameters=parameters,
                            return_type=return_type,
                            line_number=line_number,
                            parameter_enums=parameter_enums,
                            parameter_defaults=parameter_defaults,
                            parameter_docs=parameter_docs,
                            return_doc=return_doc,
                            tags=self._tags_from_libdoc_keyword(kw_doc),
                            source=self._source_from_libdoc_keyword(kw_doc),
                        )
                    )
            
                # Prefer a clean class name over dotted Libdoc import paths.
                display_name = library_name
                if "." in (library_name or ""):
                    display_name = library_name.rsplit(".", 1)[-1]

                return LibraryInfo(
                    name=display_name,
                    version=library_version,
                    scope=library_scope,
                    description=library_description,
                    keywords=keywords,
                    source_type="LIBRARY",
                    inits=self._inits_from_libdoc(
                        lib_doc, tree=tree, module_globals=module_globals
                    ),
                    source=file_path,
                )
            finally:
                self._clear_pending_library_keywords()

            
        except Exception as exc:
            # LibraryDocumentation API failed, will fall back to AST parsing
            # This is expected for some edge cases (e.g., non-importable modules, 
            # libraries that don't follow standard RF patterns)
            self._last_libdoc_error = str(exc)
            return None
    
    def _build_keyword_ast_map(self, tree: ast.AST) -> dict:
        """
        Build a map of keyword names to their AST function nodes.
        This is needed to extract type hints which are not available in LibraryDocumentation.
        """
        keyword_map = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for class_node in node.body:
                    if isinstance(class_node, ast.FunctionDef):
                        keyword_name = None
                        for decorator in class_node.decorator_list:
                            if isinstance(decorator, ast.Name) and decorator.id == "keyword":
                                keyword_name = self._robot_keyword_name(class_node.name)
                            elif isinstance(decorator, ast.Call) and isinstance(
                                decorator.func, ast.Name
                            ):
                                if decorator.func.id == "keyword":
                                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                                        keyword_name = decorator.args[0].value
                                    else:
                                        keyword_name = self._robot_keyword_name(
                                            class_node.name
                                        )
                        
                        if keyword_name:
                            keyword_map[keyword_name] = class_node
        
        return keyword_map

    def _robot_keyword_name(self, function_name: str) -> str:
        """Return the keyword name Robot Framework derives from a function name."""
        try:
            from robot.utils import printable_name

            return printable_name(function_name, code_style=True)
        except Exception:
            return self._function_name_to_keyword_name(function_name)

    def _parameters_from_libdoc_args(self, args) -> Tuple[List[Tuple[str, str]], Dict[str, str], str]:
        """Convert a Libdoc ArgumentSpec (or legacy argument list) into parameter metadata.

        Returns (parameters, defaults, return_type). return_type is empty when Libdoc
        does not report one.
        """
        parameters: List[Tuple[str, str]] = []
        defaults: Dict[str, str] = {}
        if args is None:
            return parameters, defaults, ""

        # An ArgumentSpec with no parameters is falsy, but it can still carry
        # a return type. Read that before treating an empty spec as "no args".
        return_type = ""
        return_info = getattr(args, "return_type", None)
        if return_info:
            return_type = str(return_info)

        if not args:
            return parameters, defaults, return_type

        for arg in args:
            if isinstance(arg, str):
                parameters.append((arg, ""))
                continue
            if getattr(arg, "is_marker", False):
                continue

            name = getattr(arg, "name", "") or ""
            if not name:
                continue

            kind = getattr(arg, "kind", "")
            if kind == "VAR_POSITIONAL":
                name = f"*{name}"
            elif kind == "VAR_NAMED":
                name = f"**{name}"

            type_info = getattr(arg, "type", None)
            param_type = str(type_info) if type_info else ""
            parameters.append((name, param_type))

            default_repr = getattr(arg, "default_repr", None)
            if default_repr:
                defaults[name] = default_repr

        return parameters, defaults, return_type

    def _normalize_short_doc(self, text: str) -> str:
        """Render short Arg/Returns/Import docs to HTML without double-processing."""
        if not text:
            return ""
        if self._looks_like_html_fragment(text):
            return text
        rendered, _ = self._parse_docstring(text, self.config)
        return rendered

    def _parameter_docs_from_libdoc_args(self, args) -> Dict[str, str]:
        """Extract per-argument documentation from a Libdoc ArgumentSpec."""
        docs: Dict[str, str] = {}
        if not args:
            return docs
        for arg in args:
            if isinstance(arg, str) or getattr(arg, "is_marker", False):
                continue
            name = getattr(arg, "name", "") or ""
            if not name:
                continue
            kind = getattr(arg, "kind", "")
            if kind == "VAR_POSITIONAL":
                name = f"*{name}"
            elif kind == "VAR_NAMED":
                name = f"**{name}"
            doc = getattr(arg, "doc", None) or ""
            if doc:
                docs[name] = self._normalize_short_doc(str(doc))
        return docs

    def _parameter_docs_from_libdoc_object(self, libdoc_obj) -> Dict[str, str]:
        """Extract argument docs from a KeywordDoc/InitDoc (RF 7.5+ includes ``doc``)."""
        docs: Dict[str, str] = {}
        try:
            data = libdoc_obj.to_dictionary()
        except Exception:
            data = {}
        for arg in data.get("args") or []:
            if not isinstance(arg, dict):
                continue
            name = (arg.get("name") or "").strip()
            if not name:
                continue
            kind = arg.get("kind") or ""
            if kind == "VAR_POSITIONAL":
                name = f"*{name}"
            elif kind == "VAR_NAMED":
                name = f"**{name}"
            doc = (arg.get("doc") or "").strip()
            if doc:
                docs[name] = self._normalize_short_doc(doc)
        if docs:
            return docs
        return self._parameter_docs_from_libdoc_args(getattr(libdoc_obj, "args", None))

    def _return_meta_from_libdoc_keyword(self, kw_doc) -> Tuple[str, str]:
        """Return ``(return_type, return_doc_html)`` from a Libdoc KeywordDoc."""
        return_type = ""
        return_doc = ""
        try:
            data = kw_doc.to_dictionary()
        except Exception:
            data = {}

        if data:
            rt = data.get("returnType")
            if isinstance(rt, dict):
                return_type = (rt.get("name") or "").strip()
            elif rt:
                return_type = str(rt).strip()
            return_doc = (data.get("returnDoc") or "").strip()
        else:
            args = getattr(kw_doc, "args", None)
            return_info = getattr(args, "return_type", None) if args is not None else None
            if return_info:
                return_type = str(return_info).strip()

        if return_doc:
            return_doc = self._normalize_short_doc(return_doc)
        return return_type, return_doc

    def _inits_from_libdoc(
        self,
        lib_doc,
        tree: Optional[ast.AST] = None,
        module_globals: Optional[dict] = None,
    ) -> List[InitInfo]:
        """Build InitInfo entries from Libdoc library ``inits``."""
        init_enums: Dict[str, Dict[str, Any]] = {}
        init_params_from_ast: List[Tuple[str, str]] = []
        init_defaults_from_ast: Dict[str, str] = {}
        if tree is not None:
            init_params_from_ast, init_defaults_from_ast, init_enums = (
                self._extract_init_signature_from_ast(
                    tree,
                    module_globals or {},
                    class_name=getattr(lib_doc, "name", None),
                )
            )

        inits: List[InitInfo] = []
        for init in getattr(lib_doc, "inits", None) or []:
            parameters, parameter_defaults, _ = self._parameters_from_libdoc_args(
                getattr(init, "args", None)
            )
            # Prefer AST types/defaults when Libdoc omits annotations.
            if init_params_from_ast:
                parameters = init_params_from_ast
            if init_defaults_from_ast:
                parameter_defaults = {**parameter_defaults, **init_defaults_from_ast}
            parameter_docs = self._parameter_docs_from_libdoc_object(init)
            description = self._normalize_short_doc(getattr(init, "doc", None) or "")
            inits.append(
                InitInfo(
                    description=description,
                    parameters=parameters,
                    parameter_defaults=parameter_defaults,
                    parameter_docs=parameter_docs,
                    parameter_enums=dict(init_enums),
                )
            )
        return inits

    def _select_init_class(
        self, tree: ast.AST, class_name: Optional[str] = None
    ) -> Optional[ast.ClassDef]:
        """Pick the class whose ``__init__`` documents library import arguments.

        A module often defines ``@keyword`` component classes before the public
        library. Those components are themselves library-like, so the first
        ``__init__`` in source order is frequently the wrong constructor.
        """
        if isinstance(tree, ast.ClassDef):
            return tree

        classes = [
            node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        ]
        if class_name:
            # Match every class, not only ones decorated with @keyword.
            # Plain Robot Framework libraries expose public methods without
            # that decorator, and a helper class earlier in the file must not
            # supply the import signature.
            short = str(class_name).rsplit(".", 1)[-1]
            named = [node for node in classes if node.name == short]
            if named:
                named.sort(key=self._ast_library_class_score, reverse=True)
                return named[0]
        library_classes = [
            node for node in classes if self._is_robot_library_class(node)
        ]
        pool = library_classes or classes
        if not pool:
            return None
        pool.sort(key=self._ast_library_class_score, reverse=True)
        return pool[0]

    def _extract_init_signature_from_ast(
        self,
        tree: ast.AST,
        module_globals: dict,
        class_name: Optional[str] = None,
    ) -> Tuple[List[Tuple[str, str]], Dict[str, str], Dict[str, Dict[str, Any]]]:
        """Return ``(parameters, defaults, enums)`` for the library ``__init__``."""
        parameters: List[Tuple[str, str]] = []
        parameter_defaults: Dict[str, str] = {}
        parameter_enums: Dict[str, Dict[str, Any]] = {}

        class_node = self._select_init_class(tree, class_name)
        if class_node is None:
            return parameters, parameter_defaults, parameter_enums

        init_node: Optional[ast.FunctionDef] = None
        for child in class_node.body:
            if isinstance(child, ast.FunctionDef) and child.name == "__init__":
                init_node = child
                break

        if init_node is None:
            return parameters, parameter_defaults, parameter_enums

        for param_name, annotation, default_value in self._iter_function_parameters(
            init_node
        ):
            self._append_signature_parameter(
                parameters,
                parameter_defaults,
                parameter_enums,
                param_name,
                annotation,
                default_value,
                module_globals,
            )

        return parameters, parameter_defaults, parameter_enums

    def _execute_module_safely(self, file_path: str) -> dict:
        """Safely execute the module to get actual values."""
        result = {}
        
        try:
            import sys
            import importlib.util
            import os

            file_dir = os.path.dirname(os.path.abspath(file_path))
            if file_dir not in sys.path:
                sys.path.insert(0, file_dir)

            spec = importlib.util.spec_from_file_location("temp_module", file_path)
            if spec is None or spec.loader is None:
                # Fallback: try to extract Enum classes from AST
                return self._extract_enums_from_ast(file_path)

            module = importlib.util.module_from_spec(spec)
            
            # Try to execute the module
            try:
                spec.loader.exec_module(module)
            except (ImportError, ModuleNotFoundError):
                # If import fails, try to extract Enum classes from AST
                return self._extract_enums_from_ast(file_path)

            # Extract type objects from successfully loaded module
            for attr_name in dir(module):
                if not attr_name.startswith("_"):
                    try:
                        attr_value = getattr(module, attr_name)
                        # Store actual type objects for Enum detection
                        if isinstance(attr_value, type):
                            result[attr_name] = attr_value
                        elif not callable(attr_value):
                            result[attr_name] = str(attr_value)
                    except Exception:
                        continue

            return result

        except Exception:
            # Fallback: try to extract Enum classes from AST
            return self._extract_enums_from_ast(file_path)
    
    def _extract_enums_from_ast(self, file_path: str) -> dict:
        """
        Extract Enum classes from AST when module can't be fully loaded.
        This allows us to get Enum information even when dependencies are missing.
        """
        result = {}
        try:
            import enum
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            # Create a namespace with enum module
            namespace = {
                '__name__': '__main__',
                'enum': enum,
                'Enum': enum.Enum,
            }
            
            # Execute only class definitions (skip imports and other statements)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    # Check if it's an Enum subclass
                    is_enum = False
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id in ('Enum', 'enum.Enum'):
                            is_enum = True
                            break
                        elif isinstance(base, ast.Attribute):
                            if isinstance(base.value, ast.Name) and base.value.id == 'enum' and base.attr == 'Enum':
                                is_enum = True
                                break
                    
                    if is_enum:
                        # Compile and execute just this class
                        try:
                            class_code = compile(ast.Module(body=[node], type_ignores=[]), file_path, 'exec')
                            exec(class_code, namespace)
                            if node.name in namespace:
                                result[node.name] = namespace[node.name]
                        except Exception:
                            continue
            
            return result
        except Exception:
            return {}
    
    def _resolve_ast_type_to_class(self, annotation_node: ast.AST, module_globals: dict = None) -> Optional[type]:
        """
        Resolve an AST type annotation node to an actual Python class.
        
        Returns the class object if it can be resolved, None otherwise.
        """
        if annotation_node is None or module_globals is None:
            return None
        
        try:
            if isinstance(annotation_node, ast.Name):
                type_name = annotation_node.id
                # Check if it's a type object in module_globals
                if type_name in module_globals:
                    type_obj = module_globals.get(type_name)
                    # Check if it's actually a type (class), not a string
                    if isinstance(type_obj, type):
                        return type_obj
            elif isinstance(annotation_node, ast.Attribute):
                # Handle cases like enum.Enum, typing.Optional, etc.
                if isinstance(annotation_node.value, ast.Name):
                    module_name = annotation_node.value.id
                    attr_name = annotation_node.attr
                    if module_name in module_globals:
                        module_obj = module_globals.get(module_name)
                        # module_obj could be a module or a type
                        if isinstance(module_obj, type):
                            # It's a class, check for nested attributes
                            if hasattr(module_obj, attr_name):
                                type_obj = getattr(module_obj, attr_name)
                                if isinstance(type_obj, type):
                                    return type_obj
                        elif hasattr(module_obj, attr_name):
                            # It's a module, get the attribute
                            type_obj = getattr(module_obj, attr_name)
                            if isinstance(type_obj, type):
                                return type_obj
        except Exception:
            # Silently fail - this is expected for many cases
            pass
        
        return None
    
    def _extract_enum_info(self, enum_class: type, default_value: Any = None) -> Dict[str, Any]:
        """
        Extract Enum information from an Enum class.
        
        Returns a dictionary with:
        - type_name: Name of the Enum class
        - members: List of dicts with 'name' and 'value' for each member
        - default: Default value name if provided
        """
        if not issubclass(enum_class, enum.Enum):
            return {}
        
        members = []
        for member in enum_class:
            members.append({
                'name': member.name,
                'value': member.value
            })
        
        result = {
            'type_name': enum_class.__name__,
            'members': members
        }
        
        # Try to determine default value name
        if default_value is not None:
            if isinstance(default_value, enum_class):
                result['default'] = default_value.name
            elif isinstance(default_value, ast.Attribute):
                # AST node like MyEnum.ValueA
                if hasattr(default_value, 'attr'):
                    result['default'] = default_value.attr
            elif isinstance(default_value, ast.Name):
                # AST Name node (shouldn't happen for Enum defaults, but handle it)
                if hasattr(default_value, 'id'):
                    result['default'] = default_value.id
            elif isinstance(default_value, str):
                # String representation
                result['default'] = default_value
        
        return result
    
    def _iter_function_parameters(
        self, func_node: ast.FunctionDef
    ):
        """Yield ``(name, annotation, default_node)`` for a function signature.

        Includes positional-only parameters and ``**kwargs``. ``self`` is omitted.
        ``default_node`` is the AST node for the default, or None when absent.
        """
        positional = list(func_node.args.posonlyargs) + list(func_node.args.args)
        for index, arg in enumerate(positional):
            if arg.arg == "self":
                continue
            yield (
                arg.arg,
                arg.annotation,
                self._get_default_value_from_ast(func_node, index),
            )

        if func_node.args.vararg:
            vararg = func_node.args.vararg
            yield f"*{vararg.arg}", vararg.annotation, None

        kw_defaults = list(func_node.args.kw_defaults or [])
        for index, arg in enumerate(func_node.args.kwonlyargs):
            default_value = kw_defaults[index] if index < len(kw_defaults) else None
            yield arg.arg, arg.annotation, default_value

        if func_node.args.kwarg:
            kwarg = func_node.args.kwarg
            yield f"**{kwarg.arg}", kwarg.annotation, None

    def _append_signature_parameter(
        self,
        parameters: List[Tuple[str, str]],
        parameter_defaults: Dict[str, str],
        parameter_enums: Dict[str, Dict[str, Any]],
        param_name: str,
        annotation: Optional[ast.AST],
        default_value: Any,
        module_globals: Optional[dict],
    ) -> None:
        """Record one parameter's type, default, and enum metadata."""
        param_type = self._ast_type_to_string(annotation) if annotation else "Any"
        parameters.append((param_name, param_type))
        if default_value is not None:
            default_str = self._extract_default_value(default_value)
            if default_str:
                parameter_defaults[param_name] = default_str
        if annotation and module_globals is not None:
            enum_class = self._resolve_ast_type_to_class(annotation, module_globals)
            if enum_class and issubclass(enum_class, enum.Enum):
                enum_info = self._extract_enum_info(enum_class, default_value)
                if enum_info:
                    parameter_enums[param_name] = enum_info

    def _get_default_value_from_ast(self, func_node: ast.FunctionDef, param_index: int) -> Optional[Any]:
        """Extract default value from AST function node for a parameter.

        ``param_index`` is the index in ``posonlyargs + args`` (``self`` included).
        """
        if not func_node.args.defaults:
            return None
        
        # defaults correspond to the last N positional parameters, including
        # positional-only arguments. Counting only args.args shifts defaults
        # whenever a `/` is present and drops those parameters entirely.
        num_args = len(func_node.args.posonlyargs) + len(func_node.args.args)
        num_defaults = len(func_node.args.defaults)
        default_start_index = num_args - num_defaults
        
        if param_index < default_start_index:
            return None
        
        default_index = param_index - default_start_index
        if default_index < len(func_node.args.defaults):
            return func_node.args.defaults[default_index]
        
        return None

    def _extract_library_info(
        self, tree: ast.AST, file_path: str, module_globals: dict = None
    ) -> LibraryInfo:
        """
        Extract library information from AST.
        
        NOTE: This method is used as a fallback when LibraryDocumentation API
        cannot be used. It performs custom AST parsing to extract library metadata.
        This is kept for backward compatibility and edge cases where the library
        cannot be imported or doesn't follow standard Robot Framework patterns.
        """
        if module_globals is None:
            module_globals = {}

        module_vars = self._extract_module_variables(tree)

        module_vars.update(module_globals)

        library_classes = [
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and self._is_robot_library_class(node)
        ]
        if library_classes:
            library_classes.sort(key=self._ast_library_class_score, reverse=True)
            return self._parse_library_class(library_classes[0], module_vars)

        filename = Path(file_path).stem
        return LibraryInfo(
            name=filename,
            version=self._get_module_attribute(
                "ROBOT_LIBRARY_VERSION", module_vars, ""
            ),
            scope=self._get_module_attribute(
                "ROBOT_LIBRARY_SCOPE", module_vars, "TEST"
            ),
            description=self._normalize_library_description(
                self._get_module_docstring(tree)
            ),
            keywords=self._extract_module_keywords(tree),
        )

    def _extract_module_variables(self, tree: ast.AST) -> dict:
        """
        Extract module-level variable assignments.
        
        NOTE: This is used to extract ROBOT_LIBRARY_VERSION and ROBOT_LIBRARY_SCOPE
        from module-level assignments. LibraryDocumentation API provides these
        via lib_doc.version and lib_doc.scope, but we keep this for the fallback path.
        """
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
        for base in class_node.bases:
            if self._ast_base_name(base) in {
                "DynamicCore",
                "HybridCore",
                "StaticCore",
            }:
                return True

        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                if node.name == "get_keyword_names":
                    return True
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
        """
        Parse a Robot Framework library class.
        
        NOTE: This method is used as a fallback when LibraryDocumentation API
        cannot extract library information. It performs custom AST parsing.
        LibraryDocumentation API (used in _parse_with_libdoc_api) is preferred
        as it uses the same logic as Libdoc.
        """
        if module_vars is None:
            module_vars = {}

        version = self._get_class_attribute(
            class_node, "ROBOT_LIBRARY_VERSION", "", module_vars
        )
        scope = self._get_class_attribute(
            class_node, "ROBOT_LIBRARY_SCOPE", "TEST", module_vars
        )

        if version in module_vars:
            version = module_vars[version]
        if scope in module_vars:
            scope = module_vars[scope]

        description = self._normalize_library_description(
            self._get_class_docstring(class_node)
        )

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
                    parameter_enums = {}
                    parameter_defaults = {}

                    for param_name, annotation, default_value in self._iter_function_parameters(
                        node
                    ):
                        self._append_signature_parameter(
                            parameters,
                            parameter_defaults,
                            parameter_enums,
                            param_name,
                            annotation,
                            default_value,
                            module_vars,
                        )

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
                            "parameter_enums": parameter_enums,
                            "parameter_defaults": parameter_defaults,
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
                    parameter_enums=data.get("parameter_enums", {}),
                    parameter_defaults=data.get("parameter_defaults", {}),
                )
            )

        init_params, init_defaults, init_enums = self._extract_init_signature_from_ast(
            class_node, module_vars
        )
        init_doc = ""
        for child in class_node.body:
            if isinstance(child, ast.FunctionDef) and child.name == "__init__":
                init_doc = self._normalize_short_doc(ast.get_docstring(child) or "")
                break
        inits: List[InitInfo] = []
        if init_params or init_doc:
            inits.append(
                InitInfo(
                    description=init_doc,
                    parameters=init_params,
                    parameter_defaults=init_defaults,
                    parameter_enums=init_enums,
                )
            )

        library_info = LibraryInfo(
            name=class_node.name,
            version=version,
            scope=scope,
            description=description,
            keywords=keywords,
            inits=inits,
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
        
        # Handle regular positional arguments
        for arg in func_node.args.args:
            if arg.arg == "self":
                continue
            param_name = arg.arg
            param_type = (
                self._ast_type_to_string(arg.annotation) if arg.annotation else "Any"
            )
            parameters.append((param_name, param_type))
        
        # Handle *args (variadic arguments)
        if func_node.args.vararg:
            vararg = func_node.args.vararg
            param_name = f"*{vararg.arg}"
            param_type = (
                self._ast_type_to_string(vararg.annotation) if vararg.annotation else "Any"
            )
            parameters.append((param_name, param_type))
        
        # Handle keyword-only arguments (after *args or *)
        if func_node.args.kwonlyargs:
            for kw_arg in func_node.args.kwonlyargs:
                param_name = kw_arg.arg
                param_type = (
                    self._ast_type_to_string(kw_arg.annotation) if kw_arg.annotation else "Any"
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

    @staticmethod
    def _markdown_block_kind(stripped: str) -> Optional[str]:
        """Classify a line as a markdown block marker, or None for prose."""
        if stripped.startswith("|"):
            return "table"
        # Require a space after *, -, + so **bold** headings stay prose.
        if re.match(r"^[-*+]\s", stripped):
            return "list-ul"
        if re.match(r"^\d+\.\s", stripped):
            return "list-ol"
        if stripped.startswith("!!!"):
            return "admonition"
        # Definition-list values (`:   definition`) and footnote defs stay blocks.
        if re.match(r"^:\s", stripped) or re.match(r"^\[\^[^\]]+\]:", stripped):
            return "deflist"
        if stripped.startswith("#"):
            return "heading"
        if stripped.startswith(">"):
            return "quote"
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", stripped):
            return "hr"
        if re.match(r"^(Arguments|Returns|Examples?)\s*:?\s*$", stripped, re.I):
            return "label"
        return None

    @staticmethod
    def _markdown_block_compatible(prev_kind: Optional[str], kind: str) -> bool:
        """Whether two block kinds may sit adjacent without a blank line."""
        if prev_kind == kind:
            return True
        # Nested ul/ol under the same list section can stay tight when indented;
        # switching ul ↔ ol at the same level still needs a blank line.
        if {prev_kind, kind} <= {"list-ul", "list-ol"}:
            return False
        return False

    def _join_soft_wrapped_lines(self, text: str) -> str:
        """Join soft-wrapped RF doc lines into paragraphs.

        Blank lines and list/code/table markers still start new blocks.
        Lines inside fenced code blocks (``` ... ```) are left untouched so
        indentation, blank lines, and statement boundaries stay intact.

        Python-Markdown needs a blank line before tables and lists; insert one
        when a block marker follows prose or a different block kind.
        """
        if not text:
            return ""

        lines = textwrap.dedent(text).splitlines()
        out: List[str] = []
        buffer: List[str] = []
        in_fence = False

        def flush() -> None:
            if buffer:
                out.append(" ".join(buffer))
                buffer.clear()

        def emit_block(content: str, kind: str) -> None:
            flush()
            if out and out[-1] != "":
                prev_kind = self._markdown_block_kind(out[-1].lstrip())
                if not self._markdown_block_compatible(prev_kind, kind):
                    out.append("")
            out.append(content)

        for line in lines:
            stripped = line.strip()

            # Toggle fence state on opening/closing fences. Fence marker lines
            # themselves are emitted as-is (stripped) like other block markers.
            if stripped.startswith("```"):
                flush()
                # Blank line only before an opening fence (markdown block rule).
                if not in_fence and out and out[-1] != "":
                    out.append("")
                out.append(stripped)
                in_fence = not in_fence
                continue

            if in_fence:
                # Preserve relative indentation and blank lines inside the fence.
                out.append(line)
                continue

            if not stripped:
                flush()
                out.append("")
                continue

            kind = self._markdown_block_kind(stripped)
            if kind:
                # Keep leading spaces so nested markdown lists stay nested.
                if kind in {"list-ul", "list-ol"}:
                    leading = len(line) - len(line.lstrip(" "))
                    emit_block((" " * leading) + stripped, kind)
                else:
                    emit_block(stripped, kind)
                continue

            leading = len(line) - len(line.lstrip(" "))
            # Indented continuations (admonition bodies, nested prose) must keep
            # their indent and must not be soft-joined into the previous line.
            if leading >= 4:
                flush()
                out.append(line.rstrip())
                continue

            buffer.append(stripped)
        flush()
        return "\n".join(out)

    @staticmethod
    def _looks_like_html_fragment(text: str) -> bool:
        """Return True when *text* already looks like rendered HTML documentation."""
        stripped = (text or "").lstrip()
        if not stripped.startswith("<"):
            return False
        return bool(
            re.match(
                r"<(p|div|h[1-6]|ul|ol|pre|table|section|blockquote)\b",
                stripped,
                re.I,
            )
        )

    def _normalize_library_description(self, description: str) -> str:
        """Render library-level docs to HTML without double-processing HTML input."""
        if not description:
            return ""
        if self._looks_like_html_fragment(description):
            return description
        rendered, _ = self._parse_docstring(description, self.config)
        return rendered

    def _parse_docstring(self, docstring: str, config: dict = None) -> Tuple[str, str]:
        """Parse docstring using markdown when available, else custom syntax."""
        if not docstring:
            return "", ""

        normalized = self._join_soft_wrapped_lines(docstring)
        if MARKDOWN_AVAILABLE:
            return self._render_docstring_with_markdown(normalized, config), ""
        return self._parse_custom_syntax(normalized, config), ""

    def _render_docstring_with_markdown(
        self, docstring: str, config: dict = None
    ) -> str:
        """Convert a docstring to HTML using the markdown package with custom code highlighting."""
        if not MARKDOWN_AVAILABLE:
            return self._parse_custom_syntax(docstring, config)

        content = textwrap.dedent(docstring).strip("\n")
        if not content:
            return ""

        # We must strictly separate text segments from fenced code blocks.
        # Do not run identifier protection or other substitutions on code blocks.
        code_pattern = re.compile(r"```(?P<lang>[^\n`]*)\n(?P<code>.*?)```", re.DOTALL)
        segments: List[str] = []
        last_end = 0

        for match in code_pattern.finditer(content):
            # Text before the code fence: safe to run identifier protection and markdown conversion
            text_chunk = content[last_end : match.start()]
            text_chunk = re.sub(
                r"``([A-Za-z0-9_./+-]+)\*\*(?!\*)", r"``\1``", text_chunk
            )
            text_chunk = self._protect_identifier_tokens(text_chunk)
            text_html = self._markdown_to_html(text_chunk)
            if text_html:
                segments.append(text_html)

            # Code block content: do not run identifier protections here — render as code only
            lang = (match.group("lang") or "text").strip()
            code_block = textwrap.dedent(match.group("code") or "").rstrip("\n")
            if code_block:
                segments.append(self._render_code_block(code_block, lang, config))

            last_end = match.end()

        # Remainder after last code fence
        remainder = content[last_end:]
        remainder = re.sub(
            r"``([A-Za-z0-9_./+-]+)\*\*(?!\*)", r"``\1``", remainder
        )
        remainder = self._protect_identifier_tokens(remainder)
        remainder_html = self._markdown_to_html(remainder)
        if remainder_html:
            segments.append(remainder_html)

        return "\n".join(segments)

    # Python-Markdown extensions aligned with RF Libdoc 7.5+ plus common extras.
    # Fenced code / codehilite are handled separately so Robot highlighting stays
    # consistent with Example / sample-usage blocks.
    _MARKDOWN_EXTENSIONS = [
        "sane_lists",
        "tables",
        "toc",
        "admonition",
        "def_list",
        "footnotes",
        "abbr",
        "attr_list",
        "md_in_html",
    ]
    _MARKDOWN_EXTENSION_CONFIGS = {
        # toc_depth is measured on the *output* heading level after baselevel,
        # so depth 6 is required for ### / #### sections to appear in %TOC%.
        "toc": {"baselevel": 2, "toc_depth": 6, "marker": "%TOC%"},
    }

    def _markdown_to_html(self, text: str) -> str:
        """Convert markdown text (without fenced code blocks) to HTML."""
        cleaned = textwrap.dedent(text).strip()
        if not cleaned:
            return ""

        # Only close unclosed ``identifier** forms. Do not let the capture span
        # across commas/spaces to a later **bold** marker on the same line.
        cleaned = re.sub(r"``([A-Za-z0-9_./+-]+)\*\*(?!\*)", r"``\1``", cleaned)

        cleaned = re.sub(r"!\s+\[", "![", cleaned)

        def convert_image(match):
            alt_text = match.group(1)
            url = match.group(2)
            import html

            alt_text = html.escape(alt_text)
            return f'<img alt="{alt_text}" src="{url}" />'

        image_pattern = r"!\[([^\]]+)\]\(([^\)]+)\)"
        cleaned = re.sub(image_pattern, convert_image, cleaned)

        html_out = markdown.markdown(
            cleaned,
            extensions=list(self._MARKDOWN_EXTENSIONS),
            extension_configs=dict(self._MARKDOWN_EXTENSION_CONFIGS),
            output_format="html",
        )
        return self._linkify_bare_urls(html_out)

    @staticmethod
    def _linkify_bare_urls(html_text: str) -> str:
        """Turn bare http(s) URLs in text nodes into links (RF Linkify-style)."""
        if not html_text or "http" not in html_text:
            return html_text

        url_re = re.compile(r"(https?://[^\s<>\"']+[^\s<>\"'.,);:])")
        parts = re.split(r"(<[^>]+>)", html_text)
        out: List[str] = []
        in_anchor = 0
        for part in parts:
            if not part:
                continue
            if part.startswith("<"):
                lower = part.lower()
                if lower.startswith("<a ") or lower.startswith("<a>"):
                    in_anchor += 1
                elif lower.startswith("</a"):
                    in_anchor = max(0, in_anchor - 1)
                out.append(part)
                continue
            if in_anchor:
                out.append(part)
                continue

            def repl(match: re.Match) -> str:
                url = match.group(1)
                import html as html_lib

                safe = html_lib.escape(url, quote=True)
                return f'<a href="{safe}">{safe}</a>'

            out.append(url_re.sub(repl, part))
        return "".join(out)

    def _render_code_block(self, code: str, language: str, config: dict = None) -> str:
        """Render a fenced code block with appropriate syntax highlighting."""
        language = (language or "text").strip() or "text"
        normalized = language.lower().replace("_", "-")

        code = code.rstrip()

        # Use Docgen's Robot highlighter for all RF fence aliases so docstring
        # examples match the dedicated Example section / sample-usage style.
        robot_aliases = {
            "robot",
            "robotframework",
            "robot-framework",
            "rf",
        }
        if normalized in robot_aliases:
            highlighted = self._highlight_robot_framework(code, config)
            css_lang = "robot"
        else:
            highlighted = self._highlight_with_pygments(code, normalized, config)
            css_lang = language

        highlighted = highlighted.rstrip()

        return (
            f'<div class="code-block"><pre class="language-{css_lang}">'
            f"{highlighted}"
            "</pre></div>"
        )

    def _protect_identifier_tokens(self, text: str) -> str:
        """Wrap underscore-based identifier tokens in backticks to prevent accidental emphasis.

        Existing ``code`` / `code` spans are left untouched so Robot docs like
        ``USER_CREDS`` and ``workflow/login_workflow.robot`` stay intact.
        """
        if not text:
            return ""

        placeholders: List[str] = []

        def stash(match: re.Match) -> str:
            placeholders.append(match.group(0))
            return f"\x00CODE{len(placeholders) - 1}\x00"

        # Preserve existing code spans (double backticks first).
        protected = re.sub(r"``[^`]+``", stash, text)
        protected = re.sub(r"`[^`]+`", stash, protected)
        # Keep URLs / markdown links / images intact so underscores in paths
        # (e.g. rf_favicon.png) are not wrapped as identifiers.
        protected = re.sub(r"!\[[^\]]*\]\([^)]+\)", stash, protected)
        protected = re.sub(r"\[[^\]]*\]\([^)]+\)", stash, protected)
        protected = re.sub(r"https?://[^\s<>\]]+", stash, protected)

        segments = protected.split("`")
        for idx in range(0, len(segments), 2):
            segments[idx] = self._identifier_pattern.sub(
                lambda m: f"`{m.group(0)}`",
                segments[idx],
            )

        reconstructed: List[str] = []
        for idx, segment in enumerate(segments):
            reconstructed.append(segment)
            if idx < len(segments) - 1:
                reconstructed.append("`")
        protected = "".join(reconstructed)

        for index, original in enumerate(placeholders):
            protected = protected.replace(f"\x00CODE{index}\x00", original)

        return protected

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
        """Parse inline formatting like bold, italic, links, etc.

        Code spans are protected before emphasis rules run so identifiers such as
        ``USER_CREDS`` / ``${e_type}`` are not turned into italics.
        Underscore emphasis only applies at word boundaries (not mid-identifier).
        """
        if not text:
            return ""

        text = self._escape_html(text)

        placeholders: List[str] = []

        def stash_code(inner: str) -> str:
            placeholders.append(f"<code>{inner}</code>")
            return f"\x00PH{len(placeholders) - 1}\x00"

        # Robot Framework docs use ``code``; handle before single-backtick markdown.
        text = re.sub(r"``([^`]+)``", lambda m: stash_code(m.group(1)), text)
        text = re.sub(r"`([^`]+)`", lambda m: stash_code(m.group(1)), text)

        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)

        text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
        # Mid-identifier underscores (USER_CREDS, ${e_type}) must not become italics.
        text = re.sub(
            r"(?<![A-Za-z0-9_])_(?!_)([^_\n]+?)(?<!_)_(?![A-Za-z0-9_])",
            r"<em>\1</em>",
            text,
        )

        text = re.sub(r"\+\+(.+?)\+\+", r"<u>\1</u>", text)
        text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)

        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)

        for index, replacement in enumerate(placeholders):
            text = text.replace(f"\x00PH{index}\x00", replacement)

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

        # Dark styles stay readable on docgen's dark/light themes; "default"
        # emits pure-green tokens that vanish on graphite/midnight backgrounds.
        formatter = HtmlFormatter(
            nowrap=True,
            noclasses=True,
            style="monokai",
        )

        code = code.rstrip()

        highlighted = highlight(code, lexer, formatter)

        highlighted = highlighted.replace('<div class="highlight"><pre>', "").replace(
            "</pre></div>", ""
        )

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
        pending = list(self._pending_library_keywords or [])
        library_keyword_names: List[str] = []
        if self.library_info and self.library_info.keywords:
            library_keyword_names = [kw.name for kw in self.library_info.keywords]
        known_library_names = library_keyword_names + pending

        if self._cached_keywords is not None:
            if known_library_names and any(
                kw not in self._cached_keywords for kw in known_library_names
            ):
                self._cached_keywords = None
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

            all_keywords.extend(known_library_names)

            all_keywords = sorted(set(all_keywords))
            self._cached_keywords = all_keywords
            return all_keywords

        except ImportError:
            print(
                "Error: robot.libdocpkg not available. Robot Framework must be installed."
            )
            self._cached_keywords = []
            return []

    # Local settings that take a keyword call as their value.
    _LOCAL_SETTINGS_WITH_KEYWORD = frozenset(
        {
            "[Setup]",
            "[Teardown]",
            "[Template]",
            "[Test Setup]",
            "[Test Teardown]",
            "[Suite Setup]",
            "[Suite Teardown]",
            "[Task Setup]",
            "[Task Teardown]",
        }
    )

    def _split_first_robot_cell(self, content: str) -> Tuple[Optional[str], str]:
        """Split RF cell separator (2+ spaces or tab). Returns (first_cell, rest)."""
        if not content:
            return None, ""
        match = re.match(r"^(.*?)(\s{2,}|\t)(.*)$", content, flags=re.DOTALL)
        if match:
            return match.group(1), match.group(2) + match.group(3)
        return content, ""

    @staticmethod
    def _rf_span(css_class: str, text: str) -> str:
        """Wrap text in a themeable Robot Framework syntax span."""
        return f'<span class="{css_class}">{text}</span>'

    def _keyword_span(self, keyword: str, rest: str, config: dict = None) -> str:
        """Render a keyword call name + remainder with the usual colors."""
        css_class = (
            "rf-control"
            if keyword in self.RESERVED_CONTROL_KEYWORDS
            else "rf-keyword"
        )
        keyword_html = self._rf_span(css_class, keyword)
        if rest:
            rest = self._highlight_variables_only(rest, config)
            return f"{keyword_html}{rest}"
        return keyword_html

    def _match_known_keyword(
        self, content: str, config: dict = None
    ) -> Tuple[Optional[str], str]:
        """Match a known library/BuiltIn keyword at the start of content."""
        robot_keywords = list(self._get_robot_framework_keywords(config))
        robot_keywords.extend(self.RESERVED_CONTROL_KEYWORDS)
        for keyword in sorted(robot_keywords, key=len, reverse=True):
            if content.startswith(keyword):
                next_char_pos = len(keyword)
                if next_char_pos >= len(content) or content[next_char_pos] == " ":
                    return keyword, content[next_char_pos:]
        return None, content

    def _highlight_call_position(
        self, content: str, config: dict = None
    ) -> str:
        """
        Highlight a keyword in call position.

        Prefer a known-keyword match (handles single-spaced multi-word BuiltIns),
        otherwise treat the first RF cell as a keyword — so example/dummy names
        still get teal without a config list.
        """
        if not content:
            return ""

        if content.startswith("..."):
            # Continuation row: highlight any call in the following cells.
            dots, rest = self._split_first_robot_cell(content)
            if rest.lstrip() and not rest.lstrip().startswith("#"):
                leading = rest[: len(rest) - len(rest.lstrip())]
                return (
                    f"{dots}{leading}"
                    f"{self._highlight_call_position(rest.lstrip(), config)}"
                )
            return self._highlight_variables_only(content, config)

        if content.startswith("["):
            setting_cell, rest = self._split_first_robot_cell(content)
            if setting_cell is None:
                return self._highlight_variables_only(content, config)
            setting_html = self._rf_span("rf-setting", setting_cell)
            if not rest:
                return setting_html
            if setting_cell in self._LOCAL_SETTINGS_WITH_KEYWORD:
                # Preserve separator whitespace, then highlight the keyword call.
                leading = rest[: len(rest) - len(rest.lstrip())]
                return (
                    f"{setting_html}{leading}"
                    f"{self._highlight_call_position(rest.lstrip(), config)}"
                )
            return f"{setting_html}{self._highlight_variables_only(rest, config)}"

        keyword, rest = self._match_known_keyword(content, config)
        if keyword:
            return self._keyword_span(keyword, rest, config)

        # Structural fallback: first cell is the call name (Libdoc-style).
        cell, rest = self._split_first_robot_cell(content)
        if not cell or cell.startswith("#"):
            return self._highlight_variables_only(content, config)
        return self._keyword_span(cell, rest, config)

    def _highlight_assignment_line(
        self, content: str, config: dict = None
    ) -> str:
        """Highlight `${var}=    Keyword    args` style assignment calls."""
        match = re.match(
            r"^((?:\$\{[^}]+\}|@\{[^}]+\}|&\{[^}]+\}))(\s*=\s*)(.*)$",
            content,
        )
        if not match:
            return self._highlight_variables_only(content, config)
        var, equals, rhs = match.group(1), match.group(2), match.group(3)
        var_html = self._rf_span("rf-variable", var)
        if not rhs.strip():
            return f"{var_html}{equals}"
        leading = rhs[: len(rhs) - len(rhs.lstrip())]
        return (
            f"{var_html}{equals}{leading}"
            f"{self._highlight_call_position(rhs.lstrip(), config)}"
        )

    def _highlight_robot_line(self, line: str, config: dict = None) -> str:
        """Highlight a single Robot Framework line with clean, non-overlapping highlighting."""
        if not line:
            return ""

        line = self._escape_html(line)

        if line.strip().startswith("#"):
            return self._rf_span("rf-comment", line)

        if line.strip().startswith("***"):
            return self._rf_span("rf-section", line)

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
                    # Preserve the original spacing after the setting keyword
                    # Find the actual spacing in the original line
                    indent = line[: len(line) - len(line.lstrip())]
                    # Get the part after the setting keyword, preserving spaces
                    after_setting = line[len(indent) + len(setting):]
                    # Extract leading spaces and the rest
                    leading_spaces = ""
                    for char in after_setting:
                        if char == " ":
                            leading_spaces += " "
                        else:
                            break
                    value_part = after_setting[len(leading_spaces):]
                    return (
                        f"{indent}{self._rf_span('rf-setting', setting)}"
                        f"{leading_spaces}{value_part}"
                    )
                elif setting_end_pos == len(stripped_line):
                    indent = line[: len(line) - len(line.lstrip())]
                    return f"{indent}{self._rf_span('rf-setting', setting)}"
                continue

        if (
            not line.startswith("    ")
            and not line.startswith("\t")
            and not line.startswith("***")
            and line.strip()
            and not line.startswith("[")
        ):
            # Ensure variables and keyword-args are highlighted inside non-indented
            # Robot lines as well. Previously these lines were returned raw which
            # could leave internal marker tokens like __VAR_MARKER_0__ in output.
            processed = self._highlight_variables_only(line, config)
            return self._rf_span("rf-name", processed)

        if line.startswith("    ") or line.startswith("\t"):
            indent = ""
            for i, char in enumerate(line):
                if char in " \t":
                    indent += char
                else:
                    break

            content = line[len(indent) :]

            if (
                content.startswith("${")
                or content.startswith("@{")
                or content.startswith("&{")
            ):
                return f"{indent}{self._highlight_assignment_line(content, config)}"

            return f"{indent}{self._highlight_call_position(content, config)}"

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
            marker = f"::VAR_MARKER_{var_counter}::"
            var_markers[marker] = self._rf_span("rf-variable", var)
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
                marker_pattern = "::KW_MARKER_\\d+::"
                if not re.search(marker_pattern.replace("\\d+", ".*"), text):
                    escaped_keyword = re.escape(keyword)
                    pattern = r"\b" + escaped_keyword + r"(?=\s|$|[^a-zA-Z0-9_])"

                    def mark_keyword(match):
                        nonlocal keyword_counter
                        kw = match.group(0)
                        marker = f"::KW_MARKER_{keyword_counter}::"
                        keyword_markers[marker] = self._rf_span("rf-keyword", kw)
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

            marker = f"::ARG_MARKER_{arg_counter}::"
            arg_markers[marker] = f"{self._rf_span('rf-arg', arg_name)}={arg_value}"
            arg_counter += 1
            return marker

        arg_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(::VAR_MARKER_\d+::|::KW_MARKER_\d+::|"[^"]*"|\'[^\']*\'|[^\s<]+)'
        text = re.sub(arg_pattern, mark_keyword_arg, text)

        for marker, html in var_markers.items():
            text = text.replace(marker, html)
        for marker, html in keyword_markers.items():
            text = text.replace(marker, html)
        for marker, html in arg_markers.items():
            text = text.replace(marker, html)

        def highlight_comment(match):
            comment = match.group(0)
            return self._rf_span("rf-comment", comment)

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

