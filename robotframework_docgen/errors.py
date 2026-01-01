"""
Error handling and message generation for Robot Framework Documentation Generator
"""

from typing import TYPE_CHECKING, Any

# Import optional dependencies
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None
    # For type hints when Rich is not available
    if TYPE_CHECKING:
        from rich.text import Text
    else:
        Text = Any  # type: ignore

# Repository URL for error messages and documentation links
REPOSITORY_URL = "https://github.com/deekshith-poojary98/robotframework-docgen"


def _add_repository_link(error_text: "Text") -> None:
    """Add repository link to error message."""
    if RICH_AVAILABLE:
        error_text.append("\n", style="")
        error_text.append("For more information and config file structure examples, visit:\n", style="dim")
        error_text.append(REPOSITORY_URL, style="bold cyan")


def _print_error(title: str, error_text: "Text") -> None:
    """Print error message with Rich formatting or plain text fallback."""
    if RICH_AVAILABLE:
        console.print(
            Panel(
                error_text,
                title=f"[bold red]{title}[/bold red]",
                border_style="red",
            )
        )
    else:
        # Plain text fallback
        print(f"Error: {title}")
        # Extract plain text from Rich Text object
        print(str(error_text).replace("\x1b[0m", "").replace("\x1b[1m", "").replace("\x1b[31m", "").replace("\x1b[33m", "").replace("\x1b[36m", "").replace("\x1b[90m", ""))


# Multi-library mode errors

def error_multi_lib_no_config() -> None:
    """Error: --multi-lib mode requires a config file."""
    if RICH_AVAILABLE:
        error_text = Text()
        error_text.append("--multi-lib mode requires a config file.\n\n", style="red")
        error_text.append("Usage: ", style="")
        error_text.append("docgen -c config.json --multi-lib", style="bold cyan")
        error_text.append("\n\n", style="")
        _add_repository_link(error_text)
        _print_error("Error", error_text)
    else:
        print("Error: --multi-lib mode requires a config file. Use -c/--config to specify it.")
        print(f"For more information, visit: {REPOSITORY_URL}")


def error_missing_libraries_array(config: dict) -> None:
    """Error: Multi-library mode requires a 'libraries' array."""
    libraries = config.get("libraries")
    if RICH_AVAILABLE:
        error_text = Text()
        error_text.append("Multi-library mode requires a 'libraries' array in the config file.\n\n", style="red")
        if "libraries" not in config or libraries is None:
            error_text.append("Missing: ", style="bold")
            error_text.append("'libraries' key is missing from config file.\n\n", style="yellow")
        else:
            error_text.append("Invalid: ", style="bold")
            error_text.append(f"'libraries' must be an array, got {type(libraries).__name__}.\n\n", style="yellow")
        error_text.append("Options:\n", style="bold")
        error_text.append("  1. Use single-library mode: ", style="")
        error_text.append("docgen library.py -c config.json\n", style="cyan")
        error_text.append("  2. Update config file to include a 'libraries' array:\n", style="")
        error_text.append('     "libraries": [\n', style="dim")
        error_text.append('       { "name": "Library1", "source": "lib1.py" },\n', style="dim")
        error_text.append('       { "name": "Library2", "source": "lib2.py" }\n', style="dim")
        error_text.append('     ]\n', style="dim")
        error_text.append("\n", style="")
        _add_repository_link(error_text)
        _print_error("Missing Required Config", error_text)
    else:
        if "libraries" not in config or libraries is None:
            print("Error: Multi-library mode requires a 'libraries' array in the config file.")
        else:
            print(f"Error: 'libraries' must be an array, got {type(libraries).__name__}.")
        print("Please use single-library mode or update your config file to include a 'libraries' array.")
        print(f"For more information, visit: {REPOSITORY_URL}")


def error_empty_libraries_array() -> None:
    """Error: Multi-library mode requires at least one library in the 'libraries' array."""
    if RICH_AVAILABLE:
        error_text = Text()
        error_text.append("Multi-library mode requires at least one library in the 'libraries' array.\n\n", style="red")
        error_text.append("The 'libraries' array is currently empty.\n\n", style="yellow")
        error_text.append("Add library entries to the 'libraries' array:\n", style="bold")
        error_text.append('  "libraries": [\n', style="dim")
        error_text.append('    {\n', style="dim")
        error_text.append('      "name": "Library1",\n', style="cyan")
        error_text.append('      "source": "library1.py"\n', style="cyan")
        error_text.append('    },\n', style="dim")
        error_text.append('    {\n', style="dim")
        error_text.append('      "name": "Library2",\n', style="cyan")
        error_text.append('      "source": "library2.py"\n', style="cyan")
        error_text.append('    }\n', style="dim")
        error_text.append('  ]\n', style="dim")
        error_text.append("\n", style="")
        error_text.append("Required fields for each library:\n", style="bold")
        error_text.append("  - ", style="")
        error_text.append("source", style="bold yellow")
        error_text.append(": Path to library Python file (required)\n", style="")
        error_text.append("\n", style="")
        error_text.append("Optional fields:\n", style="bold")
        error_text.append("  - ", style="")
        error_text.append("name", style="bold yellow")
        error_text.append(": Library name (optional) - if not provided, class name will be used\n", style="")
        error_text.append("\n", style="")
        _add_repository_link(error_text)
        _print_error("Empty Libraries Array", error_text)
    else:
        print("Error: Multi-library mode requires at least one library in the 'libraries' array.")
        print("The 'libraries' array is currently empty.")
        print(f"For more information, visit: {REPOSITORY_URL}")


def error_missing_site_object() -> None:
    """Error: Multi-library mode requires a 'site' object."""
    if RICH_AVAILABLE:
        error_text = Text()
        error_text.append("Multi-library mode requires a 'site' object in the config file.\n\n", style="red")
        error_text.append("The 'site' object contains site-wide metadata such as:\n", style="")
        error_text.append("  - github_url, support_email, author, maintainer\n", style="dim")
        error_text.append("  - license, robot_framework, python\n", style="dim")
        error_text.append("\n", style="")
        error_text.append("Example config structure:\n", style="bold")
        error_text.append('  {\n', style="dim")
        error_text.append('    "site": { ... },\n', style="cyan")
        error_text.append('    "libraries": [ ... ]\n', style="cyan")
        error_text.append('  }\n', style="dim")
        error_text.append("\n", style="")
        _add_repository_link(error_text)
        _print_error("Missing Required Config", error_text)
    else:
        print("Error: Multi-library mode requires a 'site' object in the config file.")
        print("Please add a 'site' object to your config file.")
        print(f"For more information, visit: {REPOSITORY_URL}")


def error_invalid_library_entries(invalid_libraries: list) -> None:
    """Error: Some library entries are missing required fields."""
    if RICH_AVAILABLE:
        error_text = Text()
        error_text.append("Some library entries are missing required fields.\n\n", style="red")
        for lib_idx, missing in invalid_libraries:
            error_text.append(f"Library #{lib_idx} missing: ", style="bold")
            error_text.append(", ".join(f"'{field}'" for field in missing), style="yellow")
            error_text.append("\n", style="")
        error_text.append("\n", style="")
        error_text.append("Required fields for each library entry:\n", style="bold")
        error_text.append("  - ", style="")
        error_text.append("source", style="bold yellow")
        error_text.append(": Path to library Python file (required, string)\n", style="")
        error_text.append("\n", style="")
        error_text.append("Optional fields:\n", style="bold")
        error_text.append("  - ", style="")
        error_text.append("name", style="bold yellow")
        error_text.append(": Library name (optional, string) - if not provided, class name will be used\n", style="")
        error_text.append("\n", style="")
        error_text.append("Example library entry:\n", style="bold")
        error_text.append('  {\n', style="dim")
        error_text.append('    "name": "MyLibrary",  // optional\n', style="cyan")
        error_text.append('    "source": "my_library.py"\n', style="cyan")
        error_text.append('  }\n', style="dim")
        error_text.append("\n", style="")
        _add_repository_link(error_text)
        _print_error("Invalid Library Entries", error_text)
    else:
        print("Error: Some library entries are missing required fields.")
        for lib_idx, missing in invalid_libraries:
            print(f"  Library #{lib_idx} missing: {', '.join(missing)}")
        print("\nRequired fields: 'source' (string)")
        print("Optional fields: 'name' (string) - if not provided, class name will be used")
        print(f"For more information, visit: {REPOSITORY_URL}")


# Single-library mode errors

def error_config_mismatch(forbidden_keys: list) -> None:
    """Error: Config file contains multi-library mode keys but single-library mode is being used."""
    if RICH_AVAILABLE:
        error_text = Text()
        error_text.append("Config file contains multi-library mode keys but single-library mode is being used.\n\n", style="red")
        error_text.append("Forbidden keys found: ", style="bold")
        error_text.append(", ".join(f"'{key}'" for key in forbidden_keys), style="bold yellow")
        error_text.append("\n\n", style="")
        error_text.append("Options:\n", style="bold")
        error_text.append("  1. Use multi-library mode: ", style="")
        error_text.append("docgen -c config.json --multi-lib\n", style="cyan")
        error_text.append("  2. Update config file for single-library mode:\n", style="")
        error_text.append("     - Remove 'site' object/dict (required in multi-lib mode)\n", style="dim")
        error_text.append("     - Remove 'libraries' array (required in multi-lib mode)\n", style="dim")
        error_text.append("\n", style="")
        _add_repository_link(error_text)
        _print_error("Config Mismatch", error_text)
    else:
        print("Error: Config file contains multi-library mode keys but single-library mode is being used.")
        print(f"Forbidden keys found: {', '.join(forbidden_keys)}")
        print("Please use --multi-lib flag or update your config file for single-library mode.")
        print(f"For more information, visit: {REPOSITORY_URL}")


def error_missing_input_file() -> None:
    """Error: input_file is required for single-library mode."""
    if RICH_AVAILABLE:
        error_text = Text()
        error_text.append("input_file is required for single-library mode.\n\n", style="red")
        error_text.append("Usage: ", style="")
        error_text.append("docgen <library.py> -c config.json", style="bold cyan")
        error_text.append("\n\n", style="")
        _add_repository_link(error_text)
        _print_error("Missing Required Argument", error_text)
    else:
        print("Error: input_file is required for single-library mode.")
        print(f"For more information, visit: {REPOSITORY_URL}")


# File and parsing errors

def error_parse_file(input_file: str, error: Exception) -> None:
    """Error: Failed to parse file."""
    if RICH_AVAILABLE:
        error_text = Text()
        error_text.append("Failed to parse file: ", style="red")
        error_text.append(input_file, style="bold")
        error_text.append(f"\n\nError: {error}", style="red")
        error_text.append("\n\n", style="")
        _add_repository_link(error_text)
        _print_error("Parse Error", error_text)
    else:
        print(f"Error: Failed to parse file: {input_file}")
        print(f"Error: {error}")
        print(f"For more information, visit: {REPOSITORY_URL}")


def error_no_keywords() -> None:
    """Error: No keywords found in the library file."""
    if RICH_AVAILABLE:
        error_text = Text()
        error_text.append("No keywords found in the library file.\n\n", style="red")
        error_text.append("Make sure to use the ", style="")
        error_text.append("@keyword", style="bold yellow")
        error_text.append(" decorator from ", style="")
        error_text.append("robot.api.deco", style="bold cyan")
        error_text.append(" to mark your functions as Robot Framework keywords.\n\n", style="")
        error_text.append("Example:\n", style="bold")
        error_text.append("    from robot.api.deco import keyword\n\n", style="dim")
        error_text.append("    # Option 1: Use function name as keyword name\n", style="dim")
        error_text.append("    @keyword\n", style="cyan")
        error_text.append("    def my_keyword(self, arg1):\n", style="")
        error_text.append('        """Documentation here."""\n', style="dim")
        error_text.append("        pass\n\n", style="")
        error_text.append("    # Option 2: Specify custom keyword name\n", style="dim")
        error_text.append('    @keyword("Custom Keyword Name")\n', style="cyan")
        error_text.append("    def my_function(self, arg1):\n", style="")
        error_text.append('        """Documentation here."""\n', style="dim")
        error_text.append("        pass\n", style="")
        error_text.append("\n", style="")
        _add_repository_link(error_text)
        _print_error("No Keywords Found", error_text)
    else:
        print("Error: No keywords found in the library file.")
        print("Make sure to use the @keyword decorator from robot.api.deco to mark your functions as Robot Framework keywords.")
        print(f"For more information, visit: {REPOSITORY_URL}")



