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
        """
        Parse a Python file and extract library information.
        
        Uses Robot Framework's LibraryDocumentation API where possible,
        falling back to AST parsing for information not available via the API
        (e.g., type hints, custom docstring processing).
        """
        # Try to use Robot Framework's LibraryDocumentation API first
        library_info = self._parse_with_libdoc_api(file_path)
        
        if library_info is None:
            # Fallback to AST parsing if LibraryDocumentation API doesn't work
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()

            tree = ast.parse(content)
            module_globals = self._execute_module_safely(file_path)
            library_info = self._extract_library_info(tree, file_path, module_globals)
        
        self.library_info = library_info
        self._cached_keywords = None
        return library_info
    
    def _parse_with_libdoc_api(self, file_path: str) -> Optional[LibraryInfo]:
        """
        Parse library using Robot Framework's LibraryDocumentation API.
        
        Returns LibraryInfo if successful, None if API cannot be used.
        This method uses the same public API that Libdoc uses internally.
        
        NOTE: LibraryDocumentation requires the library to be importable.
        If the library cannot be imported or LibraryDocumentation fails,
        this returns None and the code falls back to AST parsing.
        """
        try:
            from robot.libdocpkg import LibraryDocumentation
            import sys
            import os
            import importlib.util
            
            # Make the library importable by adding its directory to sys.path
            file_dir = os.path.dirname(os.path.abspath(file_path))
            file_name = Path(file_path).stem
            
            if file_dir not in sys.path:
                sys.path.insert(0, file_dir)
            
            # Try to use LibraryDocumentation with file path first
            try:
                lib_doc = LibraryDocumentation(file_path)
            except Exception:
                # If file path doesn't work, try importing as module
                # This is needed because LibraryDocumentation may require importable modules
                spec = importlib.util.spec_from_file_location(file_name, file_path)
                if spec is None or spec.loader is None:
                    return None
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find the library class in the module
                library_class = None
                for attr_name in dir(module):
                    if not attr_name.startswith("_"):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            hasattr(attr, '__module__') and
                            attr.__module__ == file_name):
                            # Check if it has @keyword decorated methods
                            for method_name in dir(attr):
                                method = getattr(attr, method_name, None)
                                if callable(method) and hasattr(method, 'robot_name'):
                                    library_class = attr
                                    break
                            if library_class:
                                break
                
                if library_class is None:
                    return None
                
                # Use module name for LibraryDocumentation
                lib_doc = LibraryDocumentation(f"{file_name}.{library_class.__name__}")
            
            # Extract library metadata from LibraryDocumentation (using public API)
            library_name = lib_doc.name
            library_version = lib_doc.version or "Unknown"
            library_scope = lib_doc.scope or "TEST"
            library_description = lib_doc.doc or ""
            
            # If no keywords found via API, fall back to AST parsing
            # This can happen if the library structure doesn't match what LibraryDocumentation expects
            if len(lib_doc.keywords) == 0:
                return None
            
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
                # First, try to get the module from sys.modules if it was loaded
                module_name = file_name
                if module_name in sys.modules:
                    loaded_module = sys.modules[module_name]
                    module_globals = {name: getattr(loaded_module, name) for name in dir(loaded_module) if not name.startswith("_")}
                else:
                    # Fallback: load the module ourselves
                    spec = importlib.util.spec_from_file_location(file_name, file_path)
                    if spec and spec.loader:
                        temp_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(temp_module)
                        module_globals = {name: getattr(temp_module, name) for name in dir(temp_module) if not name.startswith("_")}
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
                return_type = "None"
                line_number = kw_doc.lineno if hasattr(kw_doc, 'lineno') else 0
                
                if keyword_name in keyword_ast_map:
                    func_node = keyword_ast_map[keyword_name]
                    parameter_defaults = {}
                    
                    # Handle regular positional arguments
                    for arg_index, arg in enumerate(func_node.args.args):
                        if arg.arg == "self":
                            continue
                        param_name = arg.arg
                        param_type = (
                            self._ast_type_to_string(arg.annotation) if arg.annotation else "Any"
                        )
                        parameters.append((param_name, param_type))
                        
                        # Extract default value for all parameters
                        default_value = self._get_default_value_from_ast(func_node, arg_index)
                        if default_value is not None:
                            default_str = self._extract_default_value(default_value)
                            if default_str:
                                parameter_defaults[param_name] = default_str
                        
                        # Check if this parameter is an Enum type
                        if arg.annotation:
                            enum_class = self._resolve_ast_type_to_class(arg.annotation, module_globals)
                            if enum_class and issubclass(enum_class, enum.Enum):
                                enum_info = self._extract_enum_info(enum_class, default_value)
                                if enum_info:
                                    parameter_enums[param_name] = enum_info
                    
                    # Handle *args (variadic arguments)
                    if func_node.args.vararg:
                        vararg = func_node.args.vararg
                        param_name = f"*{vararg.arg}"
                        param_type = (
                            self._ast_type_to_string(vararg.annotation) if vararg.annotation else "Any"
                        )
                        parameters.append((param_name, param_type))
                        
                        # Check if variadic argument is an Enum type
                        if vararg.annotation:
                            enum_class = self._resolve_ast_type_to_class(vararg.annotation, module_globals)
                            if enum_class and issubclass(enum_class, enum.Enum):
                                enum_info = self._extract_enum_info(enum_class, None)
                                if enum_info:
                                    parameter_enums[param_name] = enum_info
                    
                    # Handle keyword-only arguments (after *args or *)
                    if func_node.args.kwonlyargs:
                        kw_defaults = func_node.args.kw_defaults or []
                        for kw_index, kw_arg in enumerate(func_node.args.kwonlyargs):
                            param_name = kw_arg.arg
                            param_type = (
                                self._ast_type_to_string(kw_arg.annotation) if kw_arg.annotation else "Any"
                            )
                            parameters.append((param_name, param_type))
                            
                            # Extract default value for keyword-only arguments
                            if kw_index < len(kw_defaults) and kw_defaults[kw_index] is not None:
                                default_value = kw_defaults[kw_index]
                                default_str = self._extract_default_value(default_value)
                                if default_str:
                                    parameter_defaults[param_name] = default_str
                            
                            # Check if this keyword-only parameter is an Enum type
                            if kw_arg.annotation:
                                enum_class = self._resolve_ast_type_to_class(kw_arg.annotation, module_globals)
                                if enum_class and issubclass(enum_class, enum.Enum):
                                    default_value = None
                                    if kw_index < len(kw_defaults) and kw_defaults[kw_index] is not None:
                                        default_value = kw_defaults[kw_index]
                                    enum_info = self._extract_enum_info(enum_class, default_value)
                                    if enum_info:
                                        parameter_enums[param_name] = enum_info
                    
                    if func_node.returns:
                        return_type = self._ast_type_to_string(func_node.returns)
                else:
                    # Fallback: use args from LibraryDocumentation if AST mapping fails
                    # LibraryDocumentation provides kw_doc.args as a list of argument names
                    if hasattr(kw_doc, 'args') and kw_doc.args:
                        for arg_name in kw_doc.args:
                            parameters.append((arg_name, "Any"))
                
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
                    )
                )
            
            return LibraryInfo(
                name=library_name,
                version=library_version,
                scope=library_scope,
                description=library_description,
                keywords=keywords,
            )
            
        except Exception:
            # LibraryDocumentation API failed, will fall back to AST parsing
            # This is expected for some edge cases (e.g., non-importable modules, 
            # libraries that don't follow standard RF patterns)
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
                                keyword_name = self._function_name_to_keyword_name(class_node.name)
                            elif isinstance(decorator, ast.Call) and isinstance(
                                decorator.func, ast.Name
                            ):
                                if decorator.func.id == "keyword":
                                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                                        keyword_name = decorator.args[0].value
                                    else:
                                        keyword_name = self._function_name_to_keyword_name(
                                            class_node.name
                                        )
                        
                        if keyword_name:
                            keyword_map[keyword_name] = class_node
        
        return keyword_map

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
    
    def _get_default_value_from_ast(self, func_node: ast.FunctionDef, param_index: int) -> Optional[Any]:
        """Extract default value from AST function node for a parameter."""
        if not func_node.args.defaults:
            return None
        
        # Calculate the index in defaults list
        # defaults correspond to the last N parameters
        num_args = len(func_node.args.args)
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
                    parameter_enums = {}
                    parameter_defaults = {}
                    
                    # Handle regular positional arguments
                    for arg_index, arg in enumerate(node.args.args):
                        if arg.arg == "self":
                            continue
                        param_name = arg.arg
                        param_type = (
                            self._ast_type_to_string(arg.annotation)
                            if arg.annotation
                            else "Any"
                        )
                        parameters.append((param_name, param_type))
                        
                        # Extract default value for all parameters
                        default_value = self._get_default_value_from_ast(node, arg_index)
                        if default_value is not None:
                            default_str = self._extract_default_value(default_value)
                            if default_str:
                                parameter_defaults[param_name] = default_str
                        
                        # Check if this parameter is an Enum type
                        if arg.annotation:
                            enum_class = self._resolve_ast_type_to_class(arg.annotation, module_vars)
                            if enum_class and issubclass(enum_class, enum.Enum):
                                enum_info = self._extract_enum_info(enum_class, default_value)
                                if enum_info:
                                    parameter_enums[param_name] = enum_info
                    
                    # Handle *args (variadic arguments)
                    if node.args.vararg:
                        vararg = node.args.vararg
                        param_name = f"*{vararg.arg}"
                        param_type = (
                            self._ast_type_to_string(vararg.annotation) if vararg.annotation else "Any"
                        )
                        parameters.append((param_name, param_type))
                        
                        # Check if variadic argument is an Enum type
                        if vararg.annotation:
                            enum_class = self._resolve_ast_type_to_class(vararg.annotation, module_vars)
                            if enum_class and issubclass(enum_class, enum.Enum):
                                enum_info = self._extract_enum_info(enum_class, None)
                                if enum_info:
                                    parameter_enums[param_name] = enum_info
                    
                    # Handle keyword-only arguments (after *args or *)
                    if node.args.kwonlyargs:
                        kw_defaults = node.args.kw_defaults or []
                        for kw_index, kw_arg in enumerate(node.args.kwonlyargs):
                            param_name = kw_arg.arg
                            param_type = (
                                self._ast_type_to_string(kw_arg.annotation) if kw_arg.annotation else "Any"
                            )
                            parameters.append((param_name, param_type))
                            
                            # Extract default value for keyword-only arguments
                            if kw_index < len(kw_defaults) and kw_defaults[kw_index] is not None:
                                default_value = kw_defaults[kw_index]
                                default_str = self._extract_default_value(default_value)
                                if default_str:
                                    parameter_defaults[param_name] = default_str
                            
                            # Check if this keyword-only parameter is an Enum type
                            if kw_arg.annotation:
                                enum_class = self._resolve_ast_type_to_class(kw_arg.annotation, module_vars)
                                if enum_class and issubclass(enum_class, enum.Enum):
                                    default_value = None
                                    if kw_index < len(kw_defaults) and kw_defaults[kw_index] is not None:
                                        default_value = kw_defaults[kw_index]
                                    enum_info = self._extract_enum_info(enum_class, default_value)
                                    if enum_info:
                                        parameter_enums[param_name] = enum_info

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
                    return f'{indent}<span style="color: #c586c0; font-weight: bold;">{setting}</span>{leading_spaces}{value_part}'
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

