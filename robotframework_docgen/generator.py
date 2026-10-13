import html as html_lib
import re
import importlib.resources
from datetime import datetime
from pathlib import Path
from functools import lru_cache
from typing import Dict, List, Optional
from robotframework_docgen.parser import InitInfo, LibraryInfo
from robotframework_docgen.theme import (
    logo_url_for_theme,
    render_theme_override_css,
    resolve_theme_tokens,
)


class DocumentationGenerator:
    """Generate documentation from parsed library information."""

    # Robot Framework docs use [Keyword Name] references. Reject markdown links
    # (`[text](url)`) via negative lookahead for "(".
    _KEYWORD_REF_RE = re.compile(r"\[([^\]]+?)\](?!\()")
    _PROTECTED_HTML_RE = re.compile(
        r"(?is)(<pre\b[^>]*>.*?</pre>|<code\b[^>]*>.*?</code>|<a\b[^>]*>.*?</a>)"
    )

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
        self._keyword_lookup = self._build_keyword_lookup()
    
    @property
    def library_name(self) -> str:
        """Get library display name: config name if available, otherwise class name."""
        return self.config.get("name", self.library_info.name)

    @staticmethod
    def normalize_keyword_key(name: str) -> str:
        """Case/space/underscore-insensitive keyword key (RF matching style)."""
        return re.sub(r"[\s_]+", " ", (name or "").strip().lower())

    def _build_keyword_lookup(self) -> Dict[str, str]:
        """Map normalized keyword keys to canonical keyword display names.

        Ambiguous keys (two distinct display names normalizing equally) are
        omitted so we never invent an incorrect link target.
        """
        grouped: Dict[str, List[str]] = {}
        for keyword in self.library_info.keywords:
            key = self.normalize_keyword_key(keyword.name)
            if not key:
                continue
            grouped.setdefault(key, [])
            if keyword.name not in grouped[key]:
                grouped[key].append(keyword.name)
        return {
            key: names[0] for key, names in grouped.items() if len(names) == 1
        }

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

    @staticmethod
    def _normalize_version(version: Optional[str] = None) -> str:
        """Return a displayable version, or empty when missing/unknown."""
        value = (version or "").strip()
        if not value or value.lower() == "unknown":
            return ""
        return value

    def _is_resource(self) -> bool:
        source_type = (getattr(self.library_info, "source_type", None) or "LIBRARY").upper()
        return source_type in {"RESOURCE", "SUITE"}

    def _entry_kind_label(self) -> str:
        return "Resource" if self._is_resource() else "Library"

    def _format_version_badge(self) -> str:
        """Build the hero version badge, omitted when version is unknown."""
        version = self._normalize_version(self.library_info.version)
        if not version:
            return ""
        return f'<span class="badge">Version {version}</span>'

    def _format_kind_badge(self) -> str:
        return f'<span class="badge badge-kind">{self._entry_kind_label()}</span>'

    def _format_scope_badge(self) -> str:
        """Scope is a library concept; omit for resources/suites."""
        if self._is_resource():
            return ""
        scope = (self.library_info.scope or "").strip()
        if not scope:
            return ""
        return f'<span class="badge">Scope {scope}</span>'

    def _strip_arguments_doc_section(self, html: str) -> str:
        """Remove free-text Arguments blocks when structured args are shown."""
        if not html:
            return ""
        # Cut from <em>Arguments</em> / <strong>Arguments</strong> to end of that paragraph.
        cleaned = re.sub(
            r"\s*<(?:em|strong)>Arguments</(?:em|strong)>[\s\S]*?(?=</p>|$)",
            "",
            html,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"<p>\s*</p>", "", cleaned)
        return cleaned.strip()

    def _strip_examples_doc_section(self, html: str) -> str:
        """Remove docstring Examples headings + fenced blocks.

        Used when a dedicated Example section is already shown so users do
        not see the same usage twice with different styling.
        """
        if not html:
            return ""
        cleaned = re.sub(
            r"(?is)<p>\s*Examples?:?\s*</p>\s*"
            r'(?:<div class="code-block">[\s\S]*?</div>\s*)+',
            "",
            html,
        )
        cleaned = re.sub(
            r"(?is)<h[1-6][^>]*>\s*Examples?\s*</h[1-6]>\s*"
            r'(?:<div class="code-block">[\s\S]*?</div>\s*)+',
            "",
            cleaned,
        )
        cleaned = re.sub(r"<p>\s*</p>", "", cleaned)
        return cleaned.strip()

    def _extract_examples_section_robot(self, html: str) -> Optional[str]:
        """Pull plain Robot source from a docstring Examples fence, if present."""
        if not html:
            return None
        match = re.search(
            r"(?is)(?:<p>\s*Examples?:?\s*</p>|<h[1-6][^>]*>\s*Examples?\s*</h[1-6]>)\s*"
            r'<div class="code-block"><pre class="language-robot[^"]*">(.*?)</pre></div>',
            html,
        )
        if not match:
            return None
        plain = self._strip_html_tags(match.group(1)).strip()
        return plain or None

    def _format_param_type(self, param_type: str) -> str:
        """Omit unknown/Any types so Robot keywords are not all labeled Any."""
        normalized = (param_type or "").strip()
        if not normalized or normalized.lower() in {"any", "none"}:
            return ""
        return normalized

    def _link_keyword_references(self, content: str) -> str:
        """Turn ``[Keyword Name]`` references into in-page links when resolvable.

        Leaves unresolved references untouched. Skips content inside
        ``<pre>``, ``<code>``, and existing ``<a>`` tags.
        """
        if not content or not self._keyword_lookup:
            return content or ""

        def replace_in_text(text: str) -> str:
            def repl(match: re.Match) -> str:
                raw = (match.group(1) or "").strip()
                if not raw:
                    return match.group(0)
                # Avoid turning markdown-ish image leftovers or bare URLs into links.
                if raw.startswith("http://") or raw.startswith("https://"):
                    return match.group(0)
                key = self.normalize_keyword_key(raw)
                target = self._keyword_lookup.get(key)
                if not target:
                    return match.group(0)
                anchor = self.keyword_anchor_id(target)
                label = html_lib.escape(target)
                title = html_lib.escape(f'"{target}" keyword')
                return (
                    f'<a class="kw-ref" href="#{anchor}" title="{title}">{label}</a>'
                )

            return self._KEYWORD_REF_RE.sub(repl, text)

        parts = self._PROTECTED_HTML_RE.split(content)
        out: List[str] = []
        for part in parts:
            if not part:
                continue
            if self._PROTECTED_HTML_RE.fullmatch(part):
                out.append(part)
            else:
                out.append(replace_in_text(part))
        return "".join(out)

    def _render_argument_items(
        self,
        parameters: List,
        parameter_defaults: Optional[Dict[str, str]] = None,
        parameter_docs: Optional[Dict[str, str]] = None,
        parameter_enums: Optional[dict] = None,
    ) -> List[str]:
        """Render structured argument list HTML lines."""
        parameter_defaults = parameter_defaults or {}
        parameter_docs = parameter_docs or {}
        parameter_enums = parameter_enums or {}
        lines: List[str] = [
            '        <div class="arguments-list-container">',
        ]
        for param_name, param_type in parameters:
            enum_info = parameter_enums.get(param_name) if parameter_enums else None
            default_badge = ""
            required_badge = ""
            if enum_info and enum_info.get("default"):
                default_badge = (
                    f' <span class="badge badge-default">default: '
                    f'{html_lib.escape(str(enum_info["default"]))}</span>'
                )
            elif param_name in parameter_defaults:
                default_value = parameter_defaults[param_name]
                default_badge = (
                    f' <span class="badge badge-default">default: '
                    f"{html_lib.escape(str(default_value))}</span>"
                )
            else:
                required_badge = ' <span class="badge badge-required">required</span>'

            display_type = self._format_param_type(param_type)
            arg_doc = parameter_docs.get(param_name) or ""
            item_classes = ["argument-item"]
            if arg_doc:
                item_classes.append("has-doc")
            if enum_info:
                item_classes.append("has-enum")
            lines.append(f'          <div class="{" ".join(item_classes)}">')
            lines.append('            <div class="argument-header">')
            lines.append('              <span class="argument-signature">')
            lines.append(
                f'                <span class="arg-name">{html_lib.escape(param_name)}</span>'
            )
            if display_type:
                lines.append('                <span class="arg-separator">:</span>')
                lines.append(
                    f'                <span class="arg-type">{html_lib.escape(display_type)}</span>'
                )
            lines.append("              </span>")
            if default_badge or required_badge:
                lines.append('              <span class="argument-flags">')
                if default_badge:
                    lines.append(f"                {default_badge}")
                if required_badge:
                    lines.append(f"                {required_badge}")
                lines.append("              </span>")
            lines.append("            </div>")

            if arg_doc:
                linked = self._link_keyword_references(arg_doc)
                lines.append(f'            <div class="argument-doc">{linked}</div>')

            if enum_info:
                lines.append('            <div class="enum-container">')
                lines.append('              <div class="enum-header">')
                lines.append('                <span class="enum-label">Allowed values</span>')
                lines.append(
                    '                <span class="enum-count">'
                    + str(len(enum_info.get("members", [])))
                    + " options</span>"
                )
                lines.append("              </div>")
                lines.append('              <div class="enum-members-grid">')
                for member in enum_info.get("members", []):
                    member_name = member.get("name", "")
                    member_value = member.get("value", "")
                    if isinstance(member_value, str):
                        value_display = f'"{member_value}"'
                    else:
                        value_display = str(member_value)
                    lines.extend(
                        [
                            '                <div class="enum-member">',
                            f'                  <span class="enum-member-name"><code>{html_lib.escape(str(member_name))}</code></span>',
                            '                  <span class="enum-member-separator">=</span>',
                            f'                  <span class="enum-member-value"><code>{html_lib.escape(value_display)}</code></span>',
                            "                </div>",
                        ]
                    )
                lines.append("              </div>")
                lines.append("            </div>")

            lines.append("          </div>")
        lines.append("        </div>")
        return lines

    def _build_importing_section(self) -> str:
        """Render library Importing docs from Libdoc init metadata when present."""
        if (self.library_info.source_type or "LIBRARY").upper() != "LIBRARY":
            return ""

        inits: List[InitInfo] = list(getattr(self.library_info, "inits", None) or [])
        if not inits:
            return ""

        # Libdoc exposes one primary init for typical class libraries.
        init = inits[0]
        has_args = bool(init.parameters)
        has_docs = bool(init.description)
        # Omit an empty Importing section instead of a placeholder message.
        if not has_args and not has_docs:
            return ""

        # Importing covers constructor args/docs only. The Library import line
        # already appears in Sample Usage / intro examples.
        lines = [
            '<section id="importing" class="keyword-container importing-section">',
            '  <div class="keyword-name">',
            "    <h2>Importing</h2>",
            "  </div>",
            '  <div class="keyword-content">',
        ]

        if has_args:
            lines.append('    <div class="kw-overview">')
            lines.append('      <div class="args">')
            lines.append("        <h3>Arguments</h3>")
            lines.extend(
                self._render_argument_items(
                    init.parameters,
                    init.parameter_defaults,
                    init.parameter_docs,
                    getattr(init, "parameter_enums", None),
                )
            )
            lines.append("      </div>")
            lines.append("    </div>")
        if has_docs:
            linked = self._link_keyword_references(init.description)
            lines.append('    <div class="kw-docs">')
            lines.append("      <h3>Documentation</h3>")
            lines.append(f'      <div class="kwdoc doc">{linked}</div>')
            lines.append("    </div>")

        lines.extend(["  </div>", "</section>"])
        return "\n".join(lines)

    def _import_line_for_sample(self) -> str:
        """Return the Library/Resource import line for synthetic samples."""
        if self._is_resource():
            source = (
                self.config.get("source")
                or getattr(self.library_info, "source", "")
                or f"{self.library_name}.resource"
            )
            source_path = Path(str(source))
            # Keep sample readable when config stores an absolute path.
            if source_path.is_absolute():
                source = source_path.name
            return f"Resource    {source}"
        return f"Library    {self.library_name}"

    def _extract_robot_snippet_from_html(self, html: str) -> Optional[str]:
        """Recover plain Robot source from the first highlighted robot <pre> block."""
        if not html:
            return None
        match = re.search(
            r'<pre[^>]*class="[^"]*language-robot[^"]*"[^>]*>(.*?)</pre>',
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return None
        plain = self._strip_html_tags(match.group(1)).strip()
        return plain or None

    def _build_sample_usage(self) -> str:
        """Build the Sample Usage hero snippet.

        Preference order:
        1. First fenced Robot example from the library Introduction
        2. First harvested keyword ``example``
        3. Synthetic Settings/Test Cases stub from the first keyword
        """
        intro_snippet = self._extract_robot_snippet_from_html(
            self.library_info.description or ""
        )
        if intro_snippet:
            return intro_snippet

        for keyword in self.library_info.keywords:
            harvested = (keyword.example or "").strip()
            if harvested:
                return harvested

        import_line = self._import_line_for_sample()
        call_line = "    # add your keyword calls here"
        if self.library_info.keywords:
            keyword = self.library_info.keywords[0]
            if keyword.parameters:
                arg_bits = []
                for param_name, _param_type in keyword.parameters[:3]:
                    clean = param_name.lstrip("*")
                    arg_bits.append(f"${{{clean}}}")
                args = "    ".join(arg_bits)
                call_line = (
                    f"    {keyword.name}    {args}" if args else f"    {keyword.name}"
                )
            else:
                call_line = f"    {keyword.name}"

        return f"""*** Settings ***
{import_line}

*** Test Cases ***
Example
    [Documentation]    Demonstrates using {self.library_name}
{call_line}"""

    @staticmethod
    def _find_git_root(path: Path) -> Optional[Path]:
        """Walk parents of ``path`` until a ``.git`` directory/file is found."""
        current = path if path.is_dir() else path.parent
        for candidate in (current, *current.parents):
            if (candidate / ".git").exists():
                return candidate
        return None

    @staticmethod
    def _github_repo_name(github_url: str) -> str:
        """Last path segment of a GitHub repo URL (``owner/repo`` → ``repo``)."""
        cleaned = (github_url or "").rstrip("/")
        if not cleaned:
            return ""
        return cleaned.rsplit("/", 1)[-1]

    def _normalize_repo_relative_path(self, rel: str, github_url: str = "") -> str:
        """Normalize separators and drop a mistaken leading repo-name segment."""
        rel = (rel or "").replace("\\", "/").lstrip("./")
        if not rel:
            return ""
        repo = self._github_repo_name(github_url or self.config.get("github_url", ""))
        if repo and (rel == repo or rel.startswith(repo + "/")):
            rel = rel[len(repo) :].lstrip("/")
        return rel

    def _resolve_github_source_path(self, source_path: str = "") -> str:
        """Repo-relative path for GitHub blob URLs (empty when unavailable).

        Prefer the per-keyword Libdoc source when provided, then ``github_file``,
        then the library/config source path.
        """
        github_url = self.config.get("github_url") or ""
        candidates: List[str] = []
        if source_path and str(source_path).strip():
            candidates.append(str(source_path).strip())
        else:
            explicit = (self.config.get("github_file") or "").strip()
            if explicit:
                return self._normalize_repo_relative_path(explicit, github_url)
            for raw in (
                self.config.get("source"),
                getattr(self.library_info, "source", ""),
            ):
                if raw:
                    candidates.append(str(raw))

        for raw in candidates:
            if not raw:
                continue
            path = Path(str(raw))
            abs_path: Optional[Path] = None
            if path.is_absolute():
                abs_path = path
            elif path.exists():
                abs_path = path.resolve()

            if abs_path is not None:
                try:
                    resolved = abs_path.resolve()
                except OSError:
                    resolved = abs_path
                git_root = self._find_git_root(resolved)
                if git_root is not None:
                    try:
                        return self._normalize_repo_relative_path(
                            str(resolved.relative_to(git_root.resolve())),
                            github_url,
                        )
                    except ValueError:
                        pass
                # Last resort: cwd-relative, then strip a duplicated repo prefix.
                try:
                    return self._normalize_repo_relative_path(
                        str(resolved.relative_to(Path.cwd().resolve())),
                        github_url,
                    )
                except ValueError:
                    continue

            # Already a relative path from config — treat as repo-relative.
            return self._normalize_repo_relative_path(str(path), github_url)
        return ""

    def _source_links_enabled(self) -> bool:
        """Whether per-keyword GitHub Source links should be rendered.

        Defaults to on when ``github_url`` is set. Set ``source_links: false``
        to keep repo/issue buttons while hiding keyword Source links.
        """
        if "source_links" not in self.config:
            return True
        return bool(self.config.get("source_links"))

    def _source_url(self, line_number: int = 0, source_path: str = "") -> str:
        """Optional GitHub blob URL for a keyword/library source (+ optional #L)."""
        if not self._source_links_enabled():
            return ""
        github = (self.config.get("github_url") or "").rstrip("/")
        if not github:
            return ""
        rel = self._resolve_github_source_path(source_path)
        if not rel:
            return ""
        branch = (self.config.get("github_branch") or "main").strip() or "main"
        url = f"{github}/blob/{branch}/{rel}"
        if line_number and int(line_number) > 0:
            url += f"#L{int(line_number)}"
        return url

    def _render_source_link(self, line_number: int = 0, source_path: str = "") -> str:
        url = self._source_url(line_number, source_path=source_path)
        if not url:
            return ""
        label = f"Source:L{line_number}" if line_number and int(line_number) > 0 else "Source"
        return (
            f'<a class="kw-source" href="{html_lib.escape(url)}" '
            f'target="_blank" rel="noopener noreferrer" title="View source on GitHub">'
            f"{html_lib.escape(label)}</a>"
        )

    def _render_keyword_tags(self, tags: List[str]) -> str:
        if not tags:
            return ""
        chips = [
            f'<span class="badge badge-tag">{html_lib.escape(tag)}</span>'
            for tag in tags
        ]
        return f'<div class="kw-tags">{"".join(chips)}</div>'

    def _render_return_item(
        self, return_type: str = "", return_doc: str = ""
    ) -> List[str]:
        """Render Returns in the same compact list style as Arguments."""
        type_html = ""
        if return_type:
            type_html = (
                f'<span class="arg-type">{html_lib.escape(return_type)}</span>'
            )
        else:
            type_html = '<span class="arg-type arg-type-muted">Any</span>'

        lines = [
            '        <div class="returns-list-container">',
            '          <div class="return-item">',
            '            <div class="argument-header">',
            '              <span class="argument-signature">',
            '                <span class="arg-name">return</span>',
            '                <span class="arg-separator">:</span>',
            f"                {type_html}",
            "              </span>",
            "            </div>",
        ]
        if return_doc:
            linked = self._link_keyword_references(return_doc)
            lines.append(f'            <div class="return-doc">{linked}</div>')
        lines.extend(["          </div>", "        </div>"])
        return lines

    def _build_need_help_section(self, kind_label: str) -> str:
        """Compact footer help strip; omitted when no contact actions exist."""
        actions: List[str] = []
        github_url = (self.config.get("github_url") or "").rstrip("/")
        if github_url:
            issues_url = f"{github_url}/issues/new"
            actions.append(
                f'<a class="btn btn-primary" href="{html_lib.escape(issues_url)}" '
                'target="_blank" rel="noopener noreferrer">Open an Issue</a>'
            )

        support_email = (self.config.get("support_email") or "").strip()
        if support_email:
            actions.append(
                f'<a class="btn btn-ghost" href="mailto:{html_lib.escape(support_email)}">'
                "Contact Support</a>"
            )

        if not actions:
            return ""

        if github_url and support_email:
            copy = (
                f"Questions or bugs in this {html_lib.escape(kind_label)}? "
                "Open an issue or email support — include environment details when you can."
            )
        elif github_url:
            copy = (
                f"Found a bug or want a feature in this {html_lib.escape(kind_label)}? "
                "Open a GitHub issue with enough detail to reproduce it."
            )
        else:
            copy = (
                f"Need help with this {html_lib.escape(kind_label)}? "
                "Reach out to support with your environment details."
            )

        return (
            '<section class="help-strip" id="need-help" aria-label="Need help">'
            '<div class="help-strip-body">'
            '<div class="help-strip-copy">'
            "<h2>Need help?</h2>"
            f"<p>{copy}</p>"
            "</div>"
            f'<div class="help-strip-actions">{"".join(actions)}</div>'
            "</div>"
            "</section>"
        )

    def _keyword_search_blob(self, keyword) -> str:
        """Plain-text blob used by sidebar content search (name + docs + tags)."""
        parts = [keyword.name or ""]
        parts.extend(getattr(keyword, "tags", None) or [])
        description = keyword.description or ""
        if description:
            parts.append(self._strip_html_tags(description))
        if getattr(keyword, "return_doc", ""):
            parts.append(self._strip_html_tags(keyword.return_doc))
        for doc in (getattr(keyword, "parameter_docs", None) or {}).values():
            if doc:
                parts.append(self._strip_html_tags(doc))
        blob = " ".join(parts)
        blob = re.sub(r"\s+", " ", blob).strip().lower()
        return blob

    def generate_markdown(self) -> str:
        """Generate markdown documentation."""
        md_content = []

        md_content.append(f"# {self.library_name}")
        md_content.append("")
        version = self._normalize_version(self.library_info.version)
        if version:
            md_content.append(f"**Version:** {version}")
        md_content.append(f"**Scope:** {self.library_info.scope}")
        md_content.append("")

        if self.library_info.description:
            md_content.append("## Description")
            md_content.append("")
            md_content.append(self._html_to_markdown(self.library_info.description))
            md_content.append("")

        if (self.library_info.source_type or "LIBRARY").upper() == "LIBRARY":
            md_content.append("## Importing")
            md_content.append("")
            md_content.append(f"`Library    {self.library_name}`")
            md_content.append("")
            inits = getattr(self.library_info, "inits", None) or []
            if inits and inits[0].parameters:
                init = inits[0]
                md_content.append("**Arguments:**")
                md_content.append("")
                for param_name, param_type in init.parameters:
                    default = init.parameter_defaults.get(param_name)
                    default_str = f" = `{default}`" if default is not None else ""
                    type_str = f" : `{param_type}`" if param_type else ""
                    md_content.append(f"- `{param_name}`{type_str}{default_str}")
                    arg_doc = init.parameter_docs.get(param_name)
                    if arg_doc:
                        md_content.append(f"  - {self._html_to_markdown(arg_doc)}")
                md_content.append("")
            elif inits and inits[0].description:
                md_content.append(self._html_to_markdown(inits[0].description))
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
                    # Check if this parameter has Enum information
                    enum_info = keyword.parameter_enums.get(param_name) if hasattr(keyword, 'parameter_enums') and keyword.parameter_enums else None
                    
                    # Get default value (from Enum info or parameter_defaults)
                    default_str = ""
                    if enum_info and 'default' in enum_info and enum_info['default']:
                        default_str = f" = `{enum_info['default']}`"
                    elif hasattr(keyword, 'parameter_defaults') and keyword.parameter_defaults and param_name in keyword.parameter_defaults:
                        default_value = keyword.parameter_defaults[param_name]
                        default_str = f" = `{default_value}`"
                    
                    if enum_info:
                        # Render Enum parameter with allowed values
                        md_content.append(f"- `{param_name}` : `{param_type}`{default_str}")
                        md_content.append("")
                        md_content.append("  Allowed values:")
                        for member in enum_info.get('members', []):
                            member_name = member.get('name', '')
                            member_value = member.get('value', '')
                            md_content.append(f"  - `{member_name}` = `{repr(member_value)}`")
                    else:
                        # Regular parameter
                        md_content.append(f"- `{param_name}` : `{param_type}`{default_str}")
                    arg_doc = getattr(keyword, "parameter_docs", {}).get(param_name)
                    if arg_doc:
                        md_content.append(f"  - {self._html_to_markdown(arg_doc)}")
                md_content.append("")

            if keyword.return_type and keyword.return_type != "None":
                md_content.append(f"**Returns:** `{keyword.return_type}`")
                md_content.append("")
            return_doc = getattr(keyword, "return_doc", "") or ""
            if return_doc:
                md_content.append(self._html_to_markdown(return_doc))
                md_content.append("")

            if keyword.example:
                md_content.append("**Example:**")
                md_content.append("")
                md_content.append("```robot")
                md_content.append(keyword.example)
                md_content.append("```")
                md_content.append("")

        return "\n".join(md_content)

    @staticmethod
    def keyword_anchor_id(name: str) -> str:
        """Build a stable HTML id/hash for a keyword name.

        Embedded-argument names like ``Fill ${e_type} email`` must not keep
        ``$`` / ``{}`` in the id — browsers handle those hashes poorly.
        """
        slug = (name or "").strip().lower().replace(" ", "-")
        slug = re.sub(r"[^a-z0-9\-_]+", "-", slug)
        slug = re.sub(r"-{2,}", "-", slug).strip("-_")
        return slug or "keyword"

    def generate_html(self) -> str:
        """Generate HTML documentation following Robot Framework libdoc format."""
        template = self._load_html_template()

        keyword_list_items = []
        keyword_sections = []

        for keyword in self.library_info.keywords:
            keyword_id = self.keyword_anchor_id(keyword.name)
            search_blob = html_lib.escape(
                self._keyword_search_blob(keyword), quote=True
            )
            keyword_list_items.append(
                f'<li data-search="{search_blob}">'
                f'<a href="#{keyword_id}">{html_lib.escape(keyword.name)}</a></li>'
            )

            source_link = self._render_source_link(
                getattr(keyword, "line_number", 0) or 0,
                source_path=getattr(keyword, "source", "") or "",
            )
            tags_html = self._render_keyword_tags(
                list(getattr(keyword, "tags", None) or [])
            )
            name_extras = ""
            if source_link or tags_html:
                name_extras = (
                    f'<div class="kw-meta">{tags_html}{source_link}</div>'
                )

            section_lines = [
                f'<div class="keyword-container" id="{keyword_id}">',
                '  <div class="keyword-name">',
                f'    <h2><a class="kw-name" href="#{keyword_id}">{html_lib.escape(keyword.name)}</a></h2>',
                f"    {name_extras}" if name_extras else "",
                "  </div>",
                '  <div class="keyword-content">',
            ]
            section_lines = [line for line in section_lines if line != ""]

            has_return = bool(
                (keyword.return_type and keyword.return_type != "None")
                or getattr(keyword, "return_doc", "")
            )
            has_overview = bool(keyword.parameters or has_return)

            if has_overview:
                section_lines.append('    <div class="kw-overview">')

            if keyword.parameters:
                section_lines.extend(
                    [
                        '      <div class="args">',
                        "        <h3>Arguments</h3>",
                    ]
                )
                section_lines.extend(
                    self._render_argument_items(
                        keyword.parameters,
                        getattr(keyword, "parameter_defaults", None),
                        getattr(keyword, "parameter_docs", None),
                        getattr(keyword, "parameter_enums", None),
                    )
                )
                section_lines.append("      </div>")

            if has_return:
                section_lines.append('      <div class="return-type">')
                section_lines.append("        <h3>Returns</h3>")
                section_lines.extend(
                    self._render_return_item(
                        keyword.return_type if keyword.return_type != "None" else "",
                        getattr(keyword, "return_doc", "") or "",
                    )
                )
                section_lines.append("      </div>")

            if has_overview:
                section_lines.append("    </div>")
            else:
                section_lines.append('    <div style="margin-bottom: 1rem;"></div>')

            # Harvested suite examples win; otherwise promote docstring Examples
            # into the same Example section so keywords look consistent.
            example_source = (keyword.example or "").strip()
            if not example_source:
                example_source = (
                    self._extract_examples_section_robot(keyword.description or "")
                    or ""
                )

            if keyword.description:
                description = keyword.description
                broken_image_pattern = r'!<a href="([^"]+)">([^<]+)</a>'

                def fix_broken_image(match):
                    url = match.group(1)
                    alt_text = match.group(2)
                    alt_text = html_lib.escape(alt_text)
                    return f'<img alt="{alt_text}" src="{url}" />'

                description = re.sub(
                    broken_image_pattern, fix_broken_image, description
                )
                if keyword.parameters:
                    description = self._strip_arguments_doc_section(description)
                if example_source:
                    description = self._strip_examples_doc_section(description)
                description = self._link_keyword_references(description)

                if description.strip():
                    section_lines.extend(
                        [
                            '    <div class="kw-docs">',
                            "      <h3>Documentation</h3>",
                            '      <div class="kwdoc doc">',
                            f"        {description}",
                            "      </div>",
                            "    </div>",
                        ]
                    )
                else:
                    section_lines.extend(
                        [
                            '    <div class="kw-docs">',
                            "      <h3>Documentation</h3>",
                            '      <div class="kwdoc doc"><p class="no-docs">No documentation.</p></div>',
                            "    </div>",
                        ]
                    )
            else:
                section_lines.extend(
                    [
                        '    <div class="kw-docs">',
                        "      <h3>Documentation</h3>",
                        '      <div class="kwdoc doc"><p class="no-docs">No documentation.</p></div>',
                        "    </div>",
                    ]
                )

            if example_source:
                if self.parser:
                    example_html = self.parser._highlight_robot_framework(
                        example_source, self.config
                    )
                else:
                    example_html = html_lib.escape(example_source)
                # Keep example HTML flush inside <pre> — joining on separate
                # lines would insert blank lines (white-space: pre).
                section_lines.extend(
                    [
                        '    <div class="kw-example">',
                        "      <h3>Example</h3>",
                        f'      <div class="code-block"><pre class="language-robot">{example_html.rstrip()}</pre></div>',
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
            # Description is already HTML from the parser (_parse_docstring).
            # Do not run _parse_custom_syntax again or tags get double-escaped.
            processed_description = self._link_keyword_references(
                self.library_info.description
            )
            intro_section = (
                '<section class="keyword-container intro-section">'
                '<div class="keyword-name"><h2>Introduction</h2></div>'
                f'<div class="kw-overview"><div class="kw-docs"><div class="intro-content">{processed_description}</div></div></div>'
                "</section>"
            )

        importing_section = self._build_importing_section()
        getting_started_extra = ""
        importing_nav = ""
        if importing_section:
            getting_started_extra = (
                '<li><a href="#importing">Importing</a></li>'
            )
            importing_nav = '<a href="#importing">Importing</a>'

        metadata_pairs = []
        metadata_fields = [
            ("author", "Author"),
            ("maintainer", "Maintainer"),
            ("license", "License"),
            ("robot_framework", "Robot Framework"),
        ]
        # Python version is library-oriented; skip for pure Robot resources.
        if not self._is_resource():
            metadata_fields.append(("python", "Python"))
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
            website_label = f"{self._entry_kind_label()} Website"
            hero_buttons.append(
                f'<a class="btn btn-primary" href="{library_url}" target="_blank" rel="noopener noreferrer">'
                '<svg height="18" aria-hidden="true" viewBox="0 0 24 24" width="18" fill="currentColor">'
                '<path d="M12 2a10 10 0 1 0 10 10A10.011 10.011 0 0 0 12 2Zm6.93 9H16.2a17.459 17.459 0 0 0-1.18-4.495A7.953 7.953 0 0 1 18.93 11Zm-7.93 8a15.417 15.417 0 0 1-1.458-4h2.916A15.417 15.417 0 0 1 11 19Zm-1.458-6a13.7 13.7 0 0 1 0-2h2.916a13.7 13.7 0 0 1 0 2Zm-3.25-2a13.116 13.116 0 0 1 .4-2h2.365a13.472 13.472 0 0 0 0 4H6.692a13.116 13.116 0 0 1-.4-2Zm4.708-6a15.417 15.417 0 0 1 1.458 4h-2.916A15.417 15.417 0 0 1 11 5Zm-2.02.505A17.459 17.459 0 0 0 7.8 11H5.07A7.953 7.953 0 0 1 8.98 5.505ZM5.07 13H7.8a17.459 17.459 0 0 0 1.18 4.495A7.953 7.953 0 0 1 5.07 13Zm9.95 4.495c.42-1.282.728-2.64.892-3.995h2.188a7.953 7.953 0 0 1-3.08 3.995Z"></path>'
                "</svg>"
                f"<span>{website_label}</span>"
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

        sample_usage_code = self._build_sample_usage()

        if self.parser:
            sample_usage_highlighted = self.parser._highlight_robot_framework(
                sample_usage_code, self.config
            )
        else:
            sample_usage_highlighted = sample_usage_code

        kind_label = self._entry_kind_label().lower()
        need_help_section = self._build_need_help_section(kind_label)
        tagline = f"Robot Framework {kind_label} documentation"

        version_badge = self._format_version_badge()
        kind_badge = self._format_kind_badge()
        scope_badge = self._format_scope_badge()
        theme_tokens = resolve_theme_tokens(self.config)
        theme_css = render_theme_override_css(theme_tokens)
        logo_url = logo_url_for_theme(theme_tokens)

        replacements = {
            "{{LIBRARY_NAME}}": self.library_name,
            "{{TAGLINE}}": tagline,
            "{{KIND_BADGE}}": kind_badge,
            "{{VERSION_BADGE}}": version_badge,
            "{{SCOPE_BADGE}}": scope_badge,
            "{{KEYWORD_COUNT}}": str(len(self.library_info.keywords)),
            "{{KEYWORD_LIST}}": "\n        ".join(keyword_list_items),
            "{{GETTING_STARTED_EXTRA}}": getting_started_extra,
            "{{IMPORTING_NAV}}": importing_nav,
            "{{INTRO_SECTION}}": intro_section,
            "{{IMPORTING_SECTION}}": importing_section,
            "{{KEYWORDS_SECTION}}": "\n        ".join(keyword_sections),
            "{{LAST_UPDATE}}": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "{{LIBRARY_META}}": library_meta,
            "{{HERO_ACTIONS}}": hero_actions,
            "{{SAMPLE_USAGE}}": sample_usage_highlighted,
            "{{NEED_HELP_SECTION}}": need_help_section,
            "{{ENTRY_KIND}}": self._entry_kind_label(),
            "{{THEME_OVERRIDE}}": theme_css,
            "{{LOGO_URL}}": logo_url,
        }

        html_output = template
        for placeholder, value in replacements.items():
            html_output = html_output.replace(placeholder, value or "")

        return html_output


