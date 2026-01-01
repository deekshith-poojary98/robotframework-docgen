import re
import importlib.resources
from datetime import datetime
from pathlib import Path
from functools import lru_cache
from robotframework_docgen.parser import LibraryInfo

class DocumentationGenerator:
    """Generate documentation from parsed library information."""

    @staticmethod
    def _get_template_path():
        """Get the path to the HTML template using importlib.resources."""
        try:
            # Python 3.9+ - use importlib.resources
            return importlib.resources.files("robotframework_docgen") / "templates" / "libdoc.html"
        except (AttributeError, ModuleNotFoundError):
            # Python 3.8 fallback - try importlib_resources backport
            try:
                import importlib_resources  # type: ignore[import-untyped]
                return importlib_resources.files("robotframework_docgen") / "templates" / "libdoc.html"
            except (ImportError, ModuleNotFoundError):
                return Path(__file__).resolve().parent / "templates" / "libdoc.html"

    def __init__(self, library_info: LibraryInfo, parser=None, config: dict = None):
        self.library_info = library_info
        self.parser = parser
        self.config = config or {}
    
    @property
    def library_name(self) -> str:
        """Get library display name: config name if available, otherwise class name."""
        return self.config.get("name", self.library_info.name)

    @classmethod
    @lru_cache(maxsize=1)
    def _load_html_template(cls) -> str:
        """Load the HTML template from package resources."""
        try:
            template_path = cls._get_template_path()
            return template_path.read_text(encoding="utf-8")
        except (FileNotFoundError, AttributeError) as exc:
            try:
                template_path = Path(__file__).resolve().parent / "templates" / "libdoc.html"
                return template_path.read_text(encoding="utf-8")
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"HTML template not found. Tried: {template_path}"
                ) from exc

    def _html_to_markdown(self, html_content: str) -> str:
        """Convert basic HTML tags to markdown format."""
        if not html_content:
            return ""
        
        html_content = re.sub(
            r'<div class="code-block"><pre class="language-([^"]+)">(.*?)</pre></div>',
            lambda m: f"```{m.group(1)}\n{self._strip_html_tags(m.group(2)).strip()}\n```",
            html_content,
            flags=re.DOTALL
        )
        
        html_content = re.sub(r'<code>(.*?)</code>', r'`\1`', html_content)
        
        html_content = re.sub(r'<strong>(.*?)</strong>', r'**\1**', html_content)
        
        html_content = re.sub(r'<em>(.*?)</em>', r'*\1*', html_content)
        html_content = re.sub(r'<i>(.*?)</i>', r'*\1*', html_content)

        html_content = re.sub(r'<p>(.*?)</p>', r'\1\n\n', html_content, flags=re.DOTALL)
        
        html_content = re.sub(r'<ul>(.*?)</ul>', r'\1', html_content, flags=re.DOTALL)
        html_content = re.sub(r'<ol>(.*?)</ol>', r'\1', html_content, flags=re.DOTALL)
        html_content = re.sub(r'<li>(.*?)</li>', r'- \1\n', html_content, flags=re.DOTALL)
        
        html_content = re.sub(r'<table[^>]*>(.*?)</table>', self._convert_table_to_markdown, html_content, flags=re.DOTALL)
        
        html_content = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)', html_content)
        
        html_content = re.sub(r'<h([1-6])>(.*?)</h[1-6]>', lambda m: '#' * int(m.group(1)) + ' ' + m.group(2) + '\n', html_content)
        
        html_content = self._strip_html_tags(html_content)
        
        html_content = re.sub(r'\n{3,}', '\n\n', html_content)
        html_content = html_content.strip()
        
        return html_content
    
    def _strip_html_tags(self, text: str) -> str:
        """Remove HTML tags and decode entities."""
        
        text = text.replace('&quot;', '"')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&nbsp;', ' ')
        
        text = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '', text)
        
        return text
    
    def _convert_table_to_markdown(self, match) -> str:
        """Convert HTML table to markdown table."""
        table_html = match.group(1)
        
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
        
        md_rows = []
        for i, row in enumerate(rows):
            md_row = '| ' + ' | '.join(row) + ' |'
            md_rows.append(md_row)
            if i == 0:
                separator = '| ' + ' | '.join(['---'] * len(row)) + ' |'
                md_rows.append(separator)
        
        return '\n'.join(md_rows) + '\n\n'

    def generate_markdown(self) -> str:
        """Generate markdown documentation."""
        md_content = []

        md_content.append(f"# {self.library_name}")
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
Library    {self.library_name}

*** Test Cases ***
Example
    [Documentation]    Demonstrates using {self.library_name}
    # add your keyword calls here"""

        if self.parser:
            sample_usage_highlighted = self.parser._highlight_robot_framework(
                sample_usage_code, self.config
            )
        else:
            sample_usage_highlighted = sample_usage_code

        replacements = {
            "{{LIBRARY_NAME}}": self.library_name,
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


