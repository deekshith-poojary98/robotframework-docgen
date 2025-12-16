#!/usr/bin/env python3
"""
CLI entry point for Robot Framework Documentation Generator
"""

import argparse
import json
from pathlib import Path

from robotframework_docgen.parser import RobotFrameworkDocParser
from robotframework_docgen.generator import DocumentationGenerator

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
