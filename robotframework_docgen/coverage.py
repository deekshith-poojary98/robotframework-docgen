"""
Documentation coverage report for Robot Framework libraries and resources.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from robotframework_docgen.catalog import (
    CatalogBundle,
    KeywordMetadata,
    LibraryCatalog,
    load_catalog_bundle,
)


@dataclass
class CoverageIssue:
    """A single coverage finding."""

    library: str
    keyword: str
    issue_type: str
    message: str
    parameter: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LibraryCoverage:
    """Coverage stats for one library."""

    name: str
    keyword_count: int = 0
    documented_keywords: int = 0
    undocumented_keywords: int = 0
    untyped_parameters: int = 0
    total_parameters: int = 0
    issues: List[CoverageIssue] = field(default_factory=list)

    @property
    def documentation_coverage(self) -> float:
        if self.keyword_count == 0:
            return 100.0
        return round(100.0 * self.documented_keywords / self.keyword_count, 2)

    @property
    def type_coverage(self) -> float:
        if self.total_parameters == 0:
            return 100.0
        typed = self.total_parameters - self.untyped_parameters
        return round(100.0 * typed / self.total_parameters, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "keyword_count": self.keyword_count,
            "documented_keywords": self.documented_keywords,
            "undocumented_keywords": self.undocumented_keywords,
            "untyped_parameters": self.untyped_parameters,
            "total_parameters": self.total_parameters,
            "documentation_coverage": self.documentation_coverage,
            "type_coverage": self.type_coverage,
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass
class CoverageReport:
    """Aggregate coverage report across libraries."""

    label: str
    libraries: List[LibraryCoverage] = field(default_factory=list)

    @property
    def keyword_count(self) -> int:
        return sum(lib.keyword_count for lib in self.libraries)

    @property
    def documented_keywords(self) -> int:
        return sum(lib.documented_keywords for lib in self.libraries)

    @property
    def undocumented_keywords(self) -> int:
        return sum(lib.undocumented_keywords for lib in self.libraries)

    @property
    def untyped_parameters(self) -> int:
        return sum(lib.untyped_parameters for lib in self.libraries)

    @property
    def total_parameters(self) -> int:
        return sum(lib.total_parameters for lib in self.libraries)

    @property
    def documentation_coverage(self) -> float:
        if self.keyword_count == 0:
            return 100.0
        return round(100.0 * self.documented_keywords / self.keyword_count, 2)

    @property
    def type_coverage(self) -> float:
        if self.total_parameters == 0:
            return 100.0
        typed = self.total_parameters - self.untyped_parameters
        return round(100.0 * typed / self.total_parameters, 2)

    @property
    def issues(self) -> List[CoverageIssue]:
        return [issue for lib in self.libraries for issue in lib.issues]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "summary": {
                "keyword_count": self.keyword_count,
                "documented_keywords": self.documented_keywords,
                "undocumented_keywords": self.undocumented_keywords,
                "documentation_coverage": self.documentation_coverage,
                "total_parameters": self.total_parameters,
                "untyped_parameters": self.untyped_parameters,
                "type_coverage": self.type_coverage,
                "issue_count": len(self.issues),
            },
            "libraries": [lib.to_dict() for lib in self.libraries],
        }

    def to_text(self) -> str:
        lines = [
            f"Documentation coverage: {self.label}",
            "",
            f"Keywords: {self.documented_keywords}/{self.keyword_count} "
            f"documented ({self.documentation_coverage}%)",
            f"Parameters: {self.total_parameters - self.untyped_parameters}/"
            f"{self.total_parameters} typed ({self.type_coverage}%)",
            f"Issues: {len(self.issues)}",
            "",
        ]
        if not self.issues:
            lines.append("No coverage issues found.")
            return "\n".join(lines) + "\n"

        for issue in self.issues:
            target = issue.keyword
            if issue.parameter:
                target = f"{issue.keyword}.{issue.parameter}"
            lines.append(f"- [{issue.issue_type}] {issue.library}::{target}: {issue.message}")
        return "\n".join(lines) + "\n"

    def to_markdown(self) -> str:
        lines = [
            f"# Documentation coverage: `{self.label}`",
            "",
            "## Summary",
            "",
            f"- Documented keywords: **{self.documented_keywords}/{self.keyword_count}** "
            f"({self.documentation_coverage}%)",
            f"- Typed parameters: **{self.total_parameters - self.untyped_parameters}/"
            f"{self.total_parameters}** ({self.type_coverage}%)",
            f"- Issues: **{len(self.issues)}**",
            "",
        ]
        for lib in self.libraries:
            lines.append(f"## {lib.name}")
            lines.append("")
            lines.append(
                f"- Keyword docs: {lib.documented_keywords}/{lib.keyword_count} "
                f"({lib.documentation_coverage}%)"
            )
            lines.append(
                f"- Typed args: {lib.total_parameters - lib.untyped_parameters}/"
                f"{lib.total_parameters} ({lib.type_coverage}%)"
            )
            lines.append("")
            if lib.issues:
                lines.append("| Issue | Keyword | Detail |")
                lines.append("| --- | --- | --- |")
                for issue in lib.issues:
                    target = issue.keyword
                    if issue.parameter:
                        target = f"{issue.keyword}.{issue.parameter}"
                    lines.append(
                        f"| `{issue.issue_type}` | `{target}` | {issue.message} |"
                    )
                lines.append("")
        return "\n".join(lines).rstrip() + "\n"


def _is_untyped(type_name: str) -> bool:
    normalized = (type_name or "").strip()
    return normalized in {"", "Any", "any", "object", "Object"}


def _description_mentions_parameter(description: str, param_name: str) -> bool:
    if not description or not param_name:
        return False
    # Strip leading * / ** used for varargs in catalog names.
    bare = param_name.lstrip("*")
    tokens = {
        bare.lower(),
        f"`{bare}`".lower(),
        f"${{{bare}}}".lower(),
        f"@{bare}".lower(),
        f"&{{{bare}}}".lower(),
    }
    haystack = description.lower()
    return any(token in haystack for token in tokens if token)


def analyze_keyword(
    library_name: str,
    keyword: KeywordMetadata,
    source_type: str = "LIBRARY",
) -> LibraryCoverage:
    """Analyze one keyword and return a temporary LibraryCoverage fragment."""
    coverage = LibraryCoverage(name=library_name, keyword_count=1)
    if keyword.has_documentation or (keyword.description or "").strip():
        coverage.documented_keywords = 1
    else:
        coverage.undocumented_keywords = 1
        coverage.issues.append(
            CoverageIssue(
                library=library_name,
                keyword=keyword.name,
                issue_type="missing_doc",
                message="Keyword has no documentation",
            )
        )

    check_arg_docs = source_type.upper() == "LIBRARY"
    check_types = source_type.upper() == "LIBRARY"

    for param in keyword.parameters:
        coverage.total_parameters += 1
        if check_types and _is_untyped(param.type):
            coverage.untyped_parameters += 1
            coverage.issues.append(
                CoverageIssue(
                    library=library_name,
                    keyword=keyword.name,
                    issue_type="undeclared_type",
                    parameter=param.name,
                    message=f"Parameter '{param.name}' has no declared type",
                )
            )

        # Argument documentation check for Python libraries with a docstring.
        if (
            check_arg_docs
            and (keyword.description or "").strip()
            and not _description_mentions_parameter(keyword.description, param.name)
        ):
            coverage.issues.append(
                CoverageIssue(
                    library=library_name,
                    keyword=keyword.name,
                    issue_type="missing_arg_doc",
                    parameter=param.name,
                    message=f"Parameter '{param.name}' is not mentioned in the keyword docs",
                )
            )
    return coverage


def analyze_library(library: LibraryCatalog) -> LibraryCoverage:
    """Build coverage stats for one library catalog."""
    result = LibraryCoverage(name=library.name)
    source_type = library.source_type or "LIBRARY"
    for keyword in library.keywords:
        fragment = analyze_keyword(library.name, keyword, source_type=source_type)
        result.keyword_count += fragment.keyword_count
        result.documented_keywords += fragment.documented_keywords
        result.undocumented_keywords += fragment.undocumented_keywords
        result.untyped_parameters += fragment.untyped_parameters
        result.total_parameters += fragment.total_parameters
        result.issues.extend(fragment.issues)
    return result


def analyze_catalog(bundle: CatalogBundle) -> CoverageReport:
    """Analyze an entire catalog bundle."""
    return CoverageReport(
        label=bundle.label or "catalog",
        libraries=[analyze_library(library) for library in bundle.libraries],
    )


def coverage_for_path(path: str, label: str = "") -> CoverageReport:
    """Load sources/catalog from path and return a coverage report."""
    bundle = load_catalog_bundle(path, label=label or path)
    return analyze_catalog(bundle)
