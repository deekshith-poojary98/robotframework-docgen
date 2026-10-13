#!/usr/bin/env python3
"""
CLI entry point for Robot Framework Documentation Generator
"""

import argparse
import json
import os
import shutil
import sys
import http.server
import socketserver
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

from robotframework_docgen._meta import __version__
from robotframework_docgen.parser import RobotFrameworkDocParser, LibraryInfo
from robotframework_docgen.generator import DocumentationGenerator
from robotframework_docgen.dashboard import generate_dashboard, add_dashboard_navigation
from robotframework_docgen.diff import diff_paths
from robotframework_docgen.coverage import coverage_for_path
from robotframework_docgen.catalog import load_catalog_bundle
from robotframework_docgen.examples import attach_examples_to_library
from robotframework_docgen.config_validation import (
    format_validation_errors,
    validate_multi_lib_config,
    validate_single_lib_config,
)
from robotframework_docgen.errors import (
    RICH_AVAILABLE,
    console,
    REPOSITORY_URL,
    error_multi_lib_no_config,
    error_config_mismatch,
    error_missing_input_file,
    error_parse_file,
    error_no_keywords,
)

# Import Rich components for success messages (not errors)
if RICH_AVAILABLE:
    from rich.align import Align
    from rich.panel import Panel
    from rich.text import Text

DOCGEN_BANNER = r"""
$$$$$$$\                       $$$$$$\                      
$$  __$$\                     $$  __$$\                     
$$ |  $$ | $$$$$$\   $$$$$$$\ $$ /  \__| $$$$$$\  $$$$$$$\  
$$ |  $$ |$$  __$$\ $$  _____|$$ |$$$$\ $$  __$$\ $$  __$$\ 
$$ |  $$ |$$ /  $$ |$$ /      $$ |\_$$ |$$$$$$$$ |$$ |  $$ |
$$ |  $$ |$$ |  $$ |$$ |      $$ |  $$ |$$   ____|$$ |  $$ |
$$$$$$$  |\$$$$$$  |\$$$$$$$\ \$$$$$$  |\$$$$$$$\ $$ |  $$ |
\_______/  \______/  \_______| \______/  \_______|\__|  \__|
""".strip(
    "\n"
)


def _print_cli_banner() -> None:
    """Print the DocGen ASCII banner centered for interactive CLI sessions."""
    if not sys.stdout.isatty():
        return
    tagline = f"Robot Framework Documentation Generator v{__version__}"
    if RICH_AVAILABLE:
        console.print()
        console.print(Align.center(Text(DOCGEN_BANNER, style="bold cyan")))
        console.print()
        console.print(Align.center(Text(tagline, style="dim")))
        console.print()
    else:
        width = shutil.get_terminal_size((80, 24)).columns
        print()
        for line in DOCGEN_BANNER.splitlines():
            print(line.rstrip().center(width))
        print()
        print(tagline.center(width))
        print()


def load_config(config_file: str) -> dict:
    """Load configuration from a JSON or YAML file.

    Raises:
        FileNotFoundError: when the config path does not exist
        ValueError: when the file is invalid or not an object/mapping
    """
    from robotframework_docgen.config_io import load_mapping_file

    config = load_mapping_file(config_file)
    # Used to resolve relative theme_file / theme paths.
    config["_config_dir"] = str(Path(config_file).resolve().parent)
    return config


def _print_config_validation_errors(errors: list[str]) -> None:
    """Print config validation errors and exit-friendly formatting."""
    message = "Invalid configuration:\n" + format_validation_errors(errors)
    if RICH_AVAILABLE:
        console.print(f"[red]{message}[/red]")
    else:
        print(message)


def is_multi_library_mode(config: dict) -> bool:
    """
    Check if config indicates multi-library mode.

    Multi-library mode is active when config contains a non-empty
    ``libraries`` and/or ``resources`` array.
    """
    return len(get_documentation_entries(config)) > 0


def get_documentation_entries(config: dict) -> list[dict]:
    """
    Collect documentation entries from ``libraries`` and ``resources``.

    Each returned dict is a shallow copy of the config entry with
    ``_entry_kind`` set to ``\"library\"`` or ``\"resource\"``.
    """
    entries: list[dict] = []
    for section, kind in (("libraries", "library"), ("resources", "resource")):
        items = config.get(section)
        if items is None:
            continue
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            entry = dict(item)
            entry["_entry_kind"] = kind
            if kind == "resource" and not entry.get("group"):
                entry["group"] = "Resources"
            entries.append(entry)
    return entries


def has_single_library_forbidden_keys(config: dict) -> tuple[bool, list[str]]:
    """
    Check if config contains keys that are not allowed in single-library mode.

    In single-library mode, ``site``, ``libraries``, and ``resources`` are forbidden.
    In multi-library mode, ``site`` is required and at least one of
    ``libraries`` / ``resources`` must be present.

    Returns: (has_forbidden_keys, list_of_forbidden_keys)
    """
    forbidden_keys = []
    if "site" in config:
        forbidden_keys.append("site")
    if "libraries" in config:
        forbidden_keys.append("libraries")
    if "resources" in config:
        forbidden_keys.append("resources")
    return len(forbidden_keys) > 0, forbidden_keys


def resolve_library_output_filename(library: dict, default_format: str) -> str:
    """
    Resolve output filename for a library.
    
    Priority:
    1. library.output_file (if specified)
    2. Default based on format (index.html or index.md)
    """
    if "output_file" in library and library["output_file"]:
        return library["output_file"]
    
    # Default filename based on format
    if default_format == "markdown":
        return "index.md"
    return "index.html"


def resolve_library_output_format(library: dict, cli_format: str, default_format: str) -> str:
    """
    Resolve output format for a library.
    
    Priority:
    1. library.output_format (if specified)
    2. CLI -f/--format (if provided)
    3. Default format
    """
    if "output_format" in library and library["output_format"]:
        return library["output_format"]
    
    # Use CLI format if it was explicitly provided (not default)
    # We check if cli_format differs from default to know if user specified it
    if cli_format != default_format:
        return cli_format
    
    return default_format


def _strip_html_tags(html_text: str) -> str:
    """Strip HTML tags from text for plain text display."""
    if not html_text:
        return ""
    import re
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html_text)
    # Decode common HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    return text.strip()


def _truncate_text(text: str, max_length: int = 150) -> str:
    """
    Truncate text to max_length, trying to break at word boundaries.
    Adds '...' if text was truncated.
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    # Try to find a word boundary near max_length
    truncated = text[:max_length]
    # Look for the last space, period, or newline before max_length
    last_space = truncated.rfind(' ')
    last_period = truncated.rfind('.')
    last_newline = truncated.rfind('\n')
    
    # Use the latest break point found
    break_point = max(last_space, last_period, last_newline)
    
    if break_point > max_length * 0.7:  # Only use if it's not too early
        truncated = text[:break_point].rstrip()
    else:
        # No good break point, just truncate at max_length
        truncated = text[:max_length].rstrip()
    
    return truncated + "..."


def _collect_library_metadata(
    library_info: LibraryInfo,
    library_name: str,
    library_url: str,
    library_config: Optional[dict] = None,
    merged_config: Optional[dict] = None
) -> Dict[str, Any]:
    """
    Collect metadata for a library for dashboard generation.
    
    Returns: Dictionary with library metadata
    """
    # Extract keyword metadata
    keywords_meta = []
    for kw in library_info.keywords:
        # Get description, strip HTML tags, and truncate intelligently
        if kw.description:
            # Strip HTML tags first to get plain text
            plain_text = _strip_html_tags(kw.description)
            # Take up to 3 lines or 150 characters, whichever is more
            lines = plain_text.split('\n')
            # Combine first few lines (up to 3) or until we hit a reasonable length
            combined_text = ""
            for line in lines[:3]:  # Take first 3 lines
                if combined_text:
                    combined_text += " " + line.strip()
                else:
                    combined_text = line.strip()
                # If we already have enough content, stop
                if len(combined_text) >= 150:
                    break
            
            # Truncate at word boundaries with ellipsis
            short_doc = _truncate_text(combined_text, max_length=150)
        else:
            short_doc = ""
        keywords_meta.append({
            "name": kw.name,
            "doc": short_doc
        })
    
    # Collect additional metadata from config (library-specific overrides global)
    config_source = merged_config if merged_config else library_config
    
    # Get description from config (library-specific first, then site-level, then library docstring)
    lib_description = ""
    if library_config and library_config.get("description"):
        lib_description = library_config.get("description")
    elif merged_config and merged_config.get("description"):
        lib_description = merged_config.get("description")
    elif library_info.description:
        lib_description = library_info.description.split('\n')[0].strip()
        lib_description = _strip_html_tags(lib_description)
    
    metadata = {
        "name": library_name,  # Use the name from config, not the class name
        "url": library_url,
        "keywords": keywords_meta,
        "description": lib_description,
        "version": (
            (library_info.version if library_info.version and library_info.version.lower() != "unknown" else "")
            or ((library_config.get("version") if library_config else "") or "")
        ),
        "keyword_count": len(library_info.keywords),
        "author": config_source.get("author") if config_source else None,
        "maintainer": config_source.get("maintainer") if config_source else None,
        "license": config_source.get("license") if config_source else None,
        "robot_framework": config_source.get("robot_framework") if config_source else None,
        "python": config_source.get("python") if config_source else None,
        "group": config_source.get("group") if config_source else None,
        "kind": (
            (library_config or {}).get("_entry_kind")
            or ("resource" if (library_info.source_type or "").upper() in {"RESOURCE", "SUITE"} else "library")
        ),
    }
    
    return metadata


def generate_single_library(
    input_file: str,
    output_file: Optional[str],
    output_format: str,
    config: dict,
    library_config: Optional[dict] = None,
    return_metadata: bool = False,
    examples_from: Optional[List[str]] = None,
) -> tuple[bool, str, int, Optional[Dict[str, Any]]]:
    """
    Generate documentation for a single library.
    
    Args:
        return_metadata: If True, also return library metadata for dashboard
        examples_from: Optional suite paths used to harvest keyword examples
    
    Returns: (success, output_file_path, keyword_count, metadata)
    """
    # Merge library-specific config with global config
    merged_config = config.copy()
    
    # Merge library-specific config (including name) into merged_config
    if library_config:
        # Library-specific config overrides global config
        for key, value in library_config.items():
            if value:  # Only override if value is not empty
                merged_config[key] = value
    
    # Merge site-level metadata into top-level config for generator access
    # The generator expects metadata fields (author, maintainer, license, etc.) at the top level
    if "site" in config and isinstance(config["site"], dict):
        site_config = config["site"]
        # Merge site-level metadata fields into top-level config
        metadata_fields = [
            "author",
            "maintainer",
            "license",
            "robot_framework",
            "python",
            "github_url",
            "library_url",
            "support_email",
            "github_branch",
            "github_file",
            "source_links",
            "theme",
            "theme_file",
        ]
        for field in metadata_fields:
            if field in site_config and field not in merged_config:
                merged_config[field] = site_config[field]
    
    if library_config:
        # Library-specific config overrides global config (including site-level defaults).
        # Use update() so falsey values like source_links: false still override.
        merged_config.update(library_config)
        # Preserve site-level config object
        if "site" in config:
            merged_config["site"] = config["site"]

    # Ensure source path is available for Sample Usage + GitHub source links.
    if not merged_config.get("source"):
        merged_config["source"] = input_file
    
    doc_parser = RobotFrameworkDocParser(merged_config)
    try:
        library_info = doc_parser.parse_file(input_file)
    except Exception as e:
        error_parse_file(input_file, e)
        return (False, "", 0, None)
    
    if len(library_info.keywords) == 0:
        error_no_keywords(libdoc_error=getattr(doc_parser, "_last_libdoc_error", None))
        return (False, "", 0, None)

    example_paths: List[str] = []
    if examples_from:
        example_paths.extend(examples_from)
    config_examples = merged_config.get("examples_from_tests")
    if isinstance(config_examples, str):
        example_paths.append(config_examples)
    elif isinstance(config_examples, list):
        example_paths.extend(str(path) for path in config_examples if path)
    if example_paths:
        attach_examples_to_library(library_info, example_paths)
    
    doc_generator = DocumentationGenerator(library_info, doc_parser, merged_config)
    
    if output_format == "markdown":
        content = doc_generator.generate_markdown()
        if not output_file:
            output_file = f"{Path(input_file).stem}.md"
    else:
        content = doc_generator.generate_html()
        if not output_file:
            output_file = f"{Path(input_file).stem}.html"
    
    # Ensure output directory exists
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Collect metadata if requested (for dashboard mode)
    metadata = None
    if return_metadata and output_format == "html":
        # Use name from config if available, otherwise fall back to class name
        library_name = library_config.get("name") if library_config else None
        if not library_name:
            library_name = library_info.name
        # Build relative URL from output_base_dir
        # output_file is like "output/LibraryName/index.html"
        # We need "LibraryName/index.html"
        relative_url = "/".join(output_path.parts[-2:]) if len(output_path.parts) >= 2 else output_path.name
        metadata = _collect_library_metadata(library_info, library_name, relative_url, library_config, merged_config)
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    if return_metadata:
        return True, output_file, len(library_info.keywords), metadata
    return True, output_file, len(library_info.keywords), None


def _process_library_worker(
    library: dict,
    output_base_dir: Path,
    config: dict,
    cli_format: str,
    default_format: str,
    enable_dashboard: bool = False,
    examples_from: Optional[List[str]] = None,
) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str], Optional[str], Optional[Dict[str, Any]]]:
    """
    Worker function to process a single library in parallel.
    
    Returns: (library_name, output_path, kw_count, library_format, error_message, metadata)
    Returns None values on failure.
    """
    try:
        source_file = library["source"]
        library_name = library.get("name", Path(source_file).stem)
        
        # Resolve output format for this library
        library_format = resolve_library_output_format(
            library, cli_format, default_format
        )
        
        # Resolve output filename for this library
        library_filename = resolve_library_output_filename(
            library, library_format
        )
        
        # Create library-specific output directory
        library_output_dir = output_base_dir / library_name
        library_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Full output path
        library_output_path = library_output_dir / library_filename
        
        # Generate documentation for this library
        success, output_path, kw_count, metadata = generate_single_library(
            input_file=source_file,
            output_file=str(library_output_path),
            output_format=library_format,
            config=config,
            library_config=library,
            return_metadata=enable_dashboard,
            examples_from=examples_from,
        )
        
        if success:
            return (library_name, output_path, kw_count, library_format, None, metadata)
        else:
            return (library_name, None, None, None, "Failed to generate documentation", None)
    except Exception as e:
        library_name = library.get("name", library.get("source", "Unknown"))
        return (library_name, None, None, None, f"Error: {str(e)}", None)


def serve_dashboard(output_dir: Path, host: str, port: int, use_rich: bool = False) -> None:
    """
    Start a web server to serve the generated dashboard.
    
    Args:
        output_dir: Directory containing the dashboard files
        host: Host IP address to bind to
        port: Port number to bind to
        use_rich: Whether to use Rich for output formatting
    """
    class DashboardHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(output_dir), **kwargs)
        
        def log_message(self, format, *args):
            # Suppress default logging
            pass

    # Allow quick restart after Ctrl+C (avoids macOS TIME_WAIT "Address already in use").
    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True
    
    try:
        with ReusableTCPServer((host, port), DashboardHTTPRequestHandler) as httpd:
            server_url = f"http://{host}:{port}"
            
            if use_rich:
                from rich.panel import Panel
                from rich.text import Text
                
                serve_text = Text()
                serve_text.append("Dashboard server started successfully\n\n", style="green")
                serve_text.append("Server URL: ", style="bold")
                serve_text.append(f"{server_url}\n", style="bold cyan")
                serve_text.append("\n", style="")
                serve_text.append("Press ", style="dim")
                serve_text.append("Ctrl+C", style="bold yellow")
                serve_text.append(" to stop the server\n", style="dim")
                
                console.print(
                    Panel(
                        serve_text,
                        title="[bold green]Dashboard Server Running[/bold green]",
                        border_style="green",
                    )
                )
            else:
                print("Dashboard server started successfully")
                print(f"Server URL: {server_url}")
                print("Press Ctrl+C to stop the server")
            
            # Try to open browser automatically
            try:
                webbrowser.open(server_url)
            except Exception:
                pass  # Silently fail if browser can't be opened
            
            # Start server
            httpd.serve_forever()
    except OSError as e:
        if "Address already in use" in str(e):
            if use_rich:
                console.print(f"[red]Error:[/red] Port {port} is already in use. Please use a different port with --port")
            else:
                print(f"Error: Port {port} is already in use. Please use a different port with --port")
        else:
            if use_rich:
                console.print(f"[red]Error:[/red] Failed to start server: {e}")
            else:
                print(f"Error: Failed to start server: {e}")
    except KeyboardInterrupt:
        if use_rich:
            console.print("\n[yellow]Server stopped by user[/yellow]")
        else:
            print("\nServer stopped by user")


def _maybe_export_catalog(export_path: Optional[str], source_path: str, label: str = "") -> None:
    """Write a catalog JSON when --export-catalog is requested."""
    if not export_path:
        return
    bundle = load_catalog_bundle(source_path, label=label or Path(source_path).name)
    output_path = Path(export_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bundle.write_json(output_path)
    total_keywords = sum(len(lib.keywords) for lib in bundle.libraries)
    if RICH_AVAILABLE:
        console.print(
            f"[green]✓[/green] Exported catalog "
            f"({len(bundle.libraries)} libraries / {total_keywords} keywords) → {output_path}"
        )
    else:
        print(
            f"✓ Exported catalog "
            f"({len(bundle.libraries)} libraries / {total_keywords} keywords) → {output_path}"
        )


def run_catalog_cli(argv: List[str]) -> int:
    """Export a machine-readable keyword catalog JSON."""
    parser = argparse.ArgumentParser(
        prog="docgen catalog",
        description=(
            "Export KeywordMetadata-shaped JSON for libraries/resources. "
            "Suitable for Studio Library Explorer ingestion and docgen diff/coverage."
        ),
    )
    parser.add_argument(
        "path",
        help="Source file, directory, or multi-lib config to export",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        required=True,
        help="Output catalog JSON path",
    )
    parser.add_argument(
        "--label",
        default="",
        help="Optional label stored in the catalog bundle",
    )
    args = parser.parse_args(argv)

    try:
        bundle = load_catalog_bundle(args.path, label=args.label or Path(args.path).name)
    except Exception as exc:
        if RICH_AVAILABLE:
            console.print(f"[red]Error:[/red] {exc}")
        else:
            print(f"Error: {exc}")
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bundle.write_json(output_path)

    total_keywords = sum(len(lib.keywords) for lib in bundle.libraries)
    if RICH_AVAILABLE:
        console.print(
            f"[green]✓[/green] Exported {len(bundle.libraries)} libraries / "
            f"{total_keywords} keywords → {output_path}"
        )
    else:
        print(
            f"✓ Exported {len(bundle.libraries)} libraries / "
            f"{total_keywords} keywords → {output_path}"
        )
    return 0


def run_coverage_cli(argv: List[str]) -> int:
    """Generate a documentation coverage report for libraries/resources."""
    parser = argparse.ArgumentParser(
        prog="docgen coverage",
        description=(
            "Report missing keyword docs, undeclared argument types, "
            "and parameters not mentioned in documentation."
        ),
    )
    parser.add_argument(
        "path",
        help="Source file, directory, multi-lib config, or catalog JSON to analyze",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Optional report output path",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["text", "markdown", "json"],
        default="text",
        help="Report format (default: text)",
    )
    parser.add_argument(
        "--fail-under",
        type=float,
        default=None,
        metavar="PERCENT",
        help="Exit with code 1 when documentation coverage is below this percent",
    )
    parser.add_argument(
        "--label",
        default="",
        help="Label used in the report title",
    )
    args = parser.parse_args(argv)

    try:
        report = coverage_for_path(args.path, label=args.label)
    except Exception as exc:
        if RICH_AVAILABLE:
            console.print(f"[red]Error:[/red] {exc}")
        else:
            print(f"Error: {exc}")
        return 1

    if args.format == "json":
        content = json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
    elif args.format == "markdown":
        content = report.to_markdown()
    else:
        content = report.to_text()

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        if RICH_AVAILABLE:
            console.print(f"[green]✓[/green] Wrote coverage report to {output_path}")
        else:
            print(f"✓ Wrote coverage report to {output_path}")
    else:
        print(content, end="")

    if args.fail_under is not None and report.documentation_coverage < args.fail_under:
        if RICH_AVAILABLE:
            console.print(
                f"[red]Coverage {report.documentation_coverage}% "
                f"is below --fail-under {args.fail_under}%[/red]"
            )
        else:
            print(
                f"Coverage {report.documentation_coverage}% "
                f"is below --fail-under {args.fail_under}%"
            )
        return 1
    return 0


def run_diff_cli(argv: List[str]) -> int:
    """Compare two library/resource snapshots and print a keyword changelog."""
    parser = argparse.ArgumentParser(
        prog="docgen diff",
        description=(
            "Compare two Robot Framework library versions and report "
            "added, removed, and changed keyword signatures."
        ),
    )
    parser.add_argument(
        "old",
        help="Old version: source file, directory, multi-lib config, or catalog JSON",
    )
    parser.add_argument(
        "new",
        help="New version: source file, directory, multi-lib config, or catalog JSON",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Optional report output path",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["text", "markdown", "json"],
        default="text",
        help="Report format (default: text)",
    )
    parser.add_argument(
        "--old-label",
        default="",
        help="Label for the old version in the report",
    )
    parser.add_argument(
        "--new-label",
        default="",
        help="Label for the new version in the report",
    )
    args = parser.parse_args(argv)

    try:
        report = diff_paths(
            args.old,
            args.new,
            old_label=args.old_label,
            new_label=args.new_label,
        )
    except Exception as exc:
        if RICH_AVAILABLE:
            console.print(f"[red]Error:[/red] {exc}")
        else:
            print(f"Error: {exc}")
        return 1

    if args.format == "json":
        content = json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
    elif args.format == "markdown":
        content = report.to_markdown()
    else:
        content = report.to_text()

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        if RICH_AVAILABLE:
            console.print(f"[green]✓[/green] Wrote changelog to {output_path}")
        else:
            print(f"✓ Wrote changelog to {output_path}")
    else:
        print(content, end="")

    return 0


def main(argv: Optional[List[str]] = None):
    """Main function to run the documentation parser."""
    argv = list(sys.argv[1:] if argv is None else argv)
    _print_cli_banner()
    if argv and argv[0] == "diff":
        return run_diff_cli(argv[1:])
    if argv and argv[0] == "coverage":
        return run_coverage_cli(argv[1:])
    if argv and argv[0] == "catalog":
        return run_catalog_cli(argv[1:])

    parser = argparse.ArgumentParser(
        description="Generate professional documentation from Robot Framework library files",
        epilog="""
Examples:
  # Single-library mode: Generate HTML documentation (default)
  docgen my_library.py -o docs.html -c config.json
  
  # Single-library mode: Document a Robot Framework resource file
  docgen helpers.resource -o helpers.html
  
  # Diff keyword signatures between two versions
  docgen diff v1/ v2/
  docgen diff old_lib.py new_lib.py -f markdown -o changelog.md
  
  # Documentation coverage report
  docgen coverage my_library.py
  docgen coverage sample_libs/ -f markdown -o coverage.md --fail-under 80
  
  # Export machine-readable keyword catalog JSON
  docgen catalog my_library.py -o catalog.json
  docgen catalog multi_lib_config.json -o catalogs/all.json
  docgen catalog sample_libs/ -o catalogs/sample.json
  
  # Harvest usage examples from Robot Framework test suites
  docgen helpers.resource --examples-from tests/ -o helpers.html
  
  # Single-library mode: Generate Markdown documentation
  docgen my_library.py -f markdown -o README.md
  
  # Single-library mode: Generate with default settings (HTML format)
  docgen my_library.py
  
  # Single-library mode: Specify output directory
  docgen my_library.py -d docs -o my_library.html
  
  # Multi-library mode: Generate documentation for multiple libraries
  docgen -c multi_lib_config.json --multi-lib
  
  # Multi-library mode: Specify custom output directory
  docgen -c multi_lib_config.json --multi-lib -d docs

For more information, visit: """ + REPOSITORY_URL + """
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        help="Path to a Python library (.py) or Robot Framework resource/suite file (.resource, .robot) containing keywords (required for single-library mode, optional for multi-library mode)"
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Output file path. If not specified, defaults to input_file.html (for HTML) or input_file.md (for markdown). Ignored in multi-library mode."
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
        help="Path to JSON or YAML configuration file (.json/.yaml/.yml). Optional fields include: github_url, library_url, support_email, author, maintainer, license, robot_framework, python, examples_from_tests, theme"
    )
    parser.add_argument(
        "--multi-lib",
        action="store_true",
        help="Enable multi-library mode. Requires config file with 'libraries' and/or 'resources' arrays."
    )
    parser.add_argument(
        "-d",
        "--dir",
        metavar="DIR",
        help="Output directory. In multi-library mode, defaults to 'output' if not specified. In single-library mode, used as the directory for the output file."
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Enable parallel processing for multi-library mode. Uses multiple threads to process libraries concurrently."
    )
    parser.add_argument(
        "--workers",
        type=int,
        metavar="N",
        default=None,
        help="Number of parallel workers to use (default: min(32, num_libraries, CPU_count * 2)). Only used with --parallel."
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Generate dashboard UI for multi-library mode. Automatically enables multi-library mode. Creates a homepage with library listing and global keyword search."
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start a web server to serve the generated dashboard. Requires --dashboard flag. Serves on http://localhost:8000 by default."
    )
    parser.add_argument(
        "--host",
        metavar="IP",
        default="localhost",
        help="Host IP address to bind the server to (default: localhost). Use 0.0.0.0 to serve on all interfaces."
    )
    parser.add_argument(
        "--port",
        metavar="PORT",
        type=int,
        default=8000,
        help="Port number to bind the server to (default: 8000)."
    )
    parser.add_argument(
        "--export-catalog",
        metavar="FILE",
        help="Also write a machine-readable keyword catalog JSON while generating docs",
    )
    parser.add_argument(
        "--examples-from",
        metavar="PATH",
        action="append",
        default=[],
        help=(
            "Suite/resource path used to harvest keyword usage examples. "
            "May be provided multiple times. Also configurable via "
            "'examples_from_tests' in JSON config."
        ),
    )

    args = parser.parse_args(argv)

    config = {}
    if args.config:
        try:
            config = load_config(args.config)
        except FileNotFoundError:
            if RICH_AVAILABLE:
                console.print(f"[red]Error:[/red] Config file not found: {args.config}")
            else:
                print(f"Error: Config file not found: {args.config}")
            return 1
        except ValueError as exc:
            if RICH_AVAILABLE:
                console.print(f"[red]Error:[/red] {exc}")
            else:
                print(f"Error: {exc}")
            return 1
    elif args.multi_lib:
        error_multi_lib_no_config()
        return 1

    # Validate mode matches config BEFORE determining mode
    # Multi-library mode requires explicit --multi-lib flag OR --dashboard flag
    # (--dashboard is an extension of multi-library mode)
    if args.multi_lib or args.dashboard:
        validation_errors = validate_multi_lib_config(config)
        if validation_errors:
            _print_config_validation_errors(validation_errors)
            return 1

        # Valid: --multi-lib or --dashboard flag + validated libraries/resources + site
        is_multi_lib = True
    else:
        # No --multi-lib or --dashboard flag: must be single-library mode
        # Check for forbidden keys (site, libraries, or resources)
        has_forbidden, forbidden_keys = has_single_library_forbidden_keys(config)
        if has_forbidden:
            error_config_mismatch(forbidden_keys)
            return 1
        validation_errors = validate_single_lib_config(config)
        if validation_errors:
            _print_config_validation_errors(validation_errors)
            return 1
        # Valid: no --multi-lib or --dashboard flag + no forbidden keys
        is_multi_lib = False
    
    # Warn if --parallel is used in single-library mode
    if not is_multi_lib and args.parallel:
        if RICH_AVAILABLE:
            console.print(
                "[yellow]Note:[/yellow] --parallel flag is only effective in multi-library mode. "
                "Ignoring --parallel for single-library mode.",
                style="dim"
            )
        else:
            print("Note: --parallel flag is only effective in multi-library mode. Ignoring for single-library mode.")

    # Warn if --dashboard is used without multi-library config
    if args.dashboard and not is_multi_lib:
        if RICH_AVAILABLE:
            console.print(
                "[yellow]Note:[/yellow] --dashboard flag requires multi-library mode configuration. "
                "Please ensure your config file contains 'site' and 'libraries'/'resources' keys.",
                style="dim"
            )
        else:
            print("Note: --dashboard flag requires multi-library mode configuration.")
    
    # Validate input_file for single-library mode
    if not is_multi_lib and not args.input_file:
        error_missing_input_file()
        return 1
    if not is_multi_lib and args.input_file and not Path(args.input_file).is_file():
        if RICH_AVAILABLE:
            console.print(f"[red]Error:[/red] Input file not found: {args.input_file}")
        else:
            print(f"Error: Input file not found: {args.input_file}")
        return 1

    # Detect multi-library mode
    if is_multi_lib:
        # Multi-library mode: -o/--output is ignored to prevent overwriting
        # Multiple libraries would write to the same file, so we use directory-based output
        # This is intentional behavior, not an error
        if args.output:
            if RICH_AVAILABLE:
                console.print(
                    "[yellow]Note:[/yellow] -o/--output flag is ignored in multi-library mode. "
                    "Each library writes to its own directory.",
                    style="dim"
                )
            # Silently ignore -o, don't treat as error
        
        # Output directory: use -d/--dir if provided, otherwise default to "output"
        output_base_dir = Path(args.dir) if args.dir else Path("output")
        output_base_dir.mkdir(parents=True, exist_ok=True)
        
        # Track results for summary
        results = []
        total_keywords = 0
        # Track metadata for dashboard generation (if --dashboard is enabled)
        libraries_metadata = []
        
        # Collect libraries + resources into one processing list
        doc_entries = get_documentation_entries(config)

        # Determine number of workers for parallel processing
        num_libraries = len(doc_entries)
        use_parallel = args.parallel and num_libraries > 1
        
        if use_parallel:
            # Calculate optimal number of workers
            if args.workers:
                max_workers = max(1, min(args.workers, num_libraries))
            else:
                # Default: min(32, num_libraries, CPU_count * 2)
                cpu_count = os.cpu_count() or 4
                max_workers = min(32, num_libraries, cpu_count * 2)
            
            if RICH_AVAILABLE:
                console.print(f"[cyan]Processing {num_libraries} libraries/resources in parallel with {max_workers} workers...[/cyan]")
            else:
                print(f"Processing {num_libraries} libraries/resources in parallel with {max_workers} workers...")
            
            # Process libraries in parallel
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_library = {
                    executor.submit(
                        _process_library_worker,
                        library,
                        output_base_dir,
                        config,
                        args.format,
                        "html",
                        args.dashboard,  # Pass dashboard flag to worker
                        args.examples_from,
                    ): library
                    for library in doc_entries
                }
                
                # Collect results as they complete
                completed = 0
                for future in as_completed(future_to_library):
                    completed += 1
                    library_name, output_path, kw_count, library_format, error_msg, metadata = future.result()
                    
                    if output_path and kw_count is not None:
                        results.append((library_name, output_path, kw_count, library_format))
                        total_keywords += kw_count
                        # Collect metadata for dashboard
                        if metadata:
                            libraries_metadata.append(metadata)
                        if RICH_AVAILABLE:
                            console.print(f"[green]✓[/green] [{completed}/{num_libraries}] {library_name}: {kw_count} keywords", end="\n")
                        else:
                            print(f"✓ [{completed}/{num_libraries}] {library_name}: {kw_count} keywords")
                    else:
                        if RICH_AVAILABLE:
                            error_text = Text()
                            error_text.append("Failed to generate documentation for ", style="red")
                            error_text.append(library_name, style="bold")
                            if error_msg:
                                error_text.append(f": {error_msg}", style="dim")
                            console.print(
                                Panel(
                                    error_text,
                                    title="[bold red]Generation Failed[/bold red]",
                                    border_style="red",
                                )
                            )
                        else:
                            print(f"✗ [{completed}/{num_libraries}] Failed: {library_name}")
                            if error_msg:
                                print(f"  Error: {error_msg}")
        else:
            # Sequential processing (original behavior)
            for library in doc_entries:
                source_file = library["source"]
                library_name = library.get("name", Path(source_file).stem)
                
                # Resolve output format for this library
                library_format = resolve_library_output_format(
                    library, args.format, "html"
                )
                
                # Resolve output filename for this library
                library_filename = resolve_library_output_filename(
                    library, library_format
                )
                
                # Create library-specific output directory
                library_output_dir = output_base_dir / library_name
                library_output_dir.mkdir(parents=True, exist_ok=True)
                
                # Full output path
                library_output_path = library_output_dir / library_filename
                
                # Generate documentation for this library
                if args.dashboard:
                    success, output_path, kw_count, metadata = generate_single_library(
                        input_file=source_file,
                        output_file=str(library_output_path),
                        output_format=library_format,
                        config=config,
                        library_config=library,
                        return_metadata=True,
                        examples_from=args.examples_from,
                    )
                else:
                    success, output_path, kw_count, _ = generate_single_library(
                        input_file=source_file,
                        output_file=str(library_output_path),
                        output_format=library_format,
                        config=config,
                        library_config=library,
                        return_metadata=False,
                        examples_from=args.examples_from,
                    )
                    metadata = None
                
                if success:
                    results.append((library_name, output_path, kw_count, library_format))
                    total_keywords += kw_count
                    # Collect metadata for dashboard
                    if metadata:
                        libraries_metadata.append(metadata)
                else:
                    if RICH_AVAILABLE:
                        error_text = Text()
                        error_text.append("Failed to generate documentation for ", style="red")
                        error_text.append(library_name, style="bold")
                        console.print(
                            Panel(
                                error_text,
                                title="[bold red]Generation Failed[/bold red]",
                                border_style="red",
                            )
                        )
                    else:
                        print(f"Failed to generate documentation for {library_name}")
        
        # ===== Dashboard generation (if --dashboard is enabled) =====
        dashboard_generated = False
        if args.dashboard and libraries_metadata:
            if RICH_AVAILABLE:
                console.print("[cyan]Generating dashboard...[/cyan]")
            else:
                print("Generating dashboard...")
            
            # Get site config for dashboard (theme may live on site or top-level)
            site_config = dict(config.get("site") or {})
            site_config.setdefault("name", "Robot Framework Libraries")
            site_config.setdefault(
                "description", "Documentation for Robot Framework libraries"
            )
            if "theme" not in site_config and config.get("theme") is not None:
                site_config["theme"] = config["theme"]
            if "theme_file" not in site_config and config.get("theme_file"):
                site_config["theme_file"] = config["theme_file"]
            if config.get("_config_dir"):
                site_config["_config_dir"] = config["_config_dir"]

            # Generate dashboard files
            generate_dashboard(output_base_dir, libraries_metadata, site_config)
            
            # Add navigation to library pages
            for library_name, output_path, kw_count, library_format in results:
                if library_format == "html":
                    # Read the generated HTML
                    html_content = Path(output_path).read_text(encoding="utf-8")
                    # Add dashboard navigation
                    html_content = add_dashboard_navigation(html_content, "../index.html")
                    # Write back
                    Path(output_path).write_text(html_content, encoding="utf-8")
            
            dashboard_generated = True
        
        # Print summary
        if args.dashboard and dashboard_generated:
            # Dashboard-specific success message
            if RICH_AVAILABLE:
                dashboard_text = Text()
                dashboard_text.append("✓ Dashboard generated successfully\n", style="green")
                dashboard_text.append(f"✓ Libraries documented: {len(results)}\n", style="green")
                dashboard_text.append(f"✓ Total keywords: {total_keywords}\n", style="green")
                dashboard_text.append("✓ Dashboard URL: ", style="green")
                dashboard_url = str(output_base_dir / "index.html")
                dashboard_text.append(f"{dashboard_url}\n\n", style="bold cyan")
                
                dashboard_text.append("Documented libraries:\n", style="bold")
                for lib_name, out_path, kw_count, fmt in results:
                    dashboard_text.append(f"  • {lib_name}: ", style="")
                    dashboard_text.append(f"{kw_count} keywords", style="cyan")
                    dashboard_text.append(f" → {out_path}\n", style="dim")
                
                console.print(
                    Panel(
                        dashboard_text,
                        title="[bold green]Dashboard Generated Successfully[/bold green]",
                        border_style="green",
                    )
                )
            else:
                print("✓ Dashboard generated successfully")
                print(f"✓ Libraries documented: {len(results)}")
                print(f"✓ Total keywords: {total_keywords}")
                print(f"✓ Dashboard URL: {output_base_dir / 'index.html'}")
                print("\nDocumented libraries:")
                for lib_name, out_path, kw_count, fmt in results:
                    print(f"  • {lib_name}: {kw_count} keywords → {out_path}")
        
        # ===== Serve dashboard (if --serve is enabled) =====
        if args.serve:
            if not dashboard_generated:
                if RICH_AVAILABLE:
                    console.print("[red]Error:[/red] --serve requires --dashboard flag. Dashboard must be generated first.")
                else:
                    print("Error: --serve requires --dashboard flag. Dashboard must be generated first.")
                return 1
            
            # Start web server
            serve_dashboard(output_base_dir, args.host, args.port, RICH_AVAILABLE)
        elif RICH_AVAILABLE and results:
            # Multi-library summary (when dashboard is not generated)
            summary_text = Text()
            summary_text.append(f"✓ Generated documentation for {len(results)} libraries\n", style="green")
            summary_text.append(f"✓ Total keywords: {total_keywords}\n", style="green")
            summary_text.append(f"✓ Output directory: {output_base_dir}\n\n", style="green")
            
            for lib_name, out_path, kw_count, fmt in results:
                summary_text.append(f"  • {lib_name}: ", style="")
                summary_text.append(f"{kw_count} keywords", style="cyan")
                summary_text.append(f" → {out_path}", style="dim")
                summary_text.append("\n", style="")

            console.print(
                Panel(
                    summary_text,
                    title="[bold green]Multi-Library Documentation Generated[/bold green]",
                    border_style="green",
                )
            )
        elif results:
            print(f"✓ Generated documentation for {len(results)} libraries")
            print(f"✓ Total keywords: {total_keywords}")
            print(f"✓ Output directory: {output_base_dir}")
            for lib_name, out_path, kw_count, fmt in results:
                print(f"  • {lib_name}: {kw_count} keywords → {out_path}")

        if results and args.export_catalog and args.config:
            _maybe_export_catalog(args.export_catalog, args.config, label="multi-lib")
        
        return 0 if results else 1
    
    else:
        # Single-library mode: preserve existing behavior, but support -d/--dir
        # Resolve output file path: combine -d/--dir with -o/--output if needed
        output_file = args.output
        
        if args.dir:
            # -d/--dir provided: use it as base output directory
            output_dir = Path(args.dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if output_file:
                # -o/--output provided: check if it's absolute path
                output_path = Path(output_file)
                if output_path.is_absolute():
                    # Absolute path: use as-is (ignore -d/--dir)
                    output_file = str(output_path)
                else:
                    # Relative path: combine with -d/--dir
                    # This handles both "file.html" and "subdir/file.html"
                    output_file = str(output_dir / output_path)
            else:
                # No -o/--output: use default filename in -d/--dir
                default_filename = f"{Path(args.input_file).stem}.{args.format if args.format == 'markdown' else 'html'}"
                output_file = str(output_dir / default_filename)
        else:
            # No -d/--dir: use -o/--output as-is or default in current directory
            if not output_file:
                output_file = f"{Path(args.input_file).stem}.{args.format if args.format == 'markdown' else 'html'}"
        
        success, output_file, kw_count, _ = generate_single_library(
            input_file=args.input_file,
            output_file=output_file,
            output_format=args.format,
            config=config,
            return_metadata=False,
            examples_from=args.examples_from,
        )
        
        if not success:
            return 1

        # Print summary (preserve existing format)
        if RICH_AVAILABLE:
            summary_text = Text()
            summary_text.append("✓ ", style="green")
            summary_text.append(f"Parsed {kw_count} keywords from ", style="")
            
            # Get library name from parsed info
            doc_parser = RobotFrameworkDocParser(config)
            try:
                library_info = doc_parser.parse_file(args.input_file)
                summary_text.append(library_info.name, style="bold cyan")
            except Exception:
                summary_text.append(Path(args.input_file).stem, style="bold cyan")

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
            print(f"✓ Parsed {kw_count} keywords")
            print(f"✓ Documentation generated: {output_file}")

        if args.export_catalog:
            _maybe_export_catalog(args.export_catalog, args.input_file)

        return 0


if __name__ == "__main__":
    exit(main())
