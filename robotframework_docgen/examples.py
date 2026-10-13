"""
Extract keyword usage examples from Robot Framework test suites.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set

from robotframework_docgen.parser import KeywordInfo, LibraryInfo


SUITE_SUFFIXES = {".robot", ".resource", ".txt", ".tsv"}


@dataclass
class KeywordExample:
    """A usage example harvested from a test case."""

    keyword: str
    test_name: str
    documentation: str
    snippet: str
    source: str

    def as_robot_block(self) -> str:
        return self.snippet.strip()


def normalize_keyword_name(name: str) -> str:
    """Normalize keyword names for matching (case/space insensitive)."""
    return " ".join((name or "").split()).lower()


def _iter_suite_files(paths: Sequence[str | Path]) -> Iterable[Path]:
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            continue
        if path.is_file() and path.suffix.lower() in SUITE_SUFFIXES:
            yield path
            continue
        if path.is_dir():
            for candidate in sorted(path.rglob("*")):
                if not candidate.is_file():
                    continue
                if candidate.suffix.lower() not in SUITE_SUFFIXES:
                    continue
                if any(
                    part in {".git", ".venv", "venv", "__pycache__", "node_modules"}
                    for part in candidate.parts
                ):
                    continue
                yield candidate


def _extract_test_documentation(test_case) -> str:
    from robot.parsing.model.statements import Documentation

    for stmt in test_case.body:
        if isinstance(stmt, Documentation):
            value = getattr(stmt, "value", None)
            if isinstance(value, (list, tuple)):
                return " ".join(str(part) for part in value).strip()
            return str(value or "").strip()
    return ""


def _snippet_for_test(source_lines: List[str], test_case) -> str:
    start = max((getattr(test_case, "lineno", 1) or 1) - 1, 0)
    end = getattr(test_case, "end_lineno", None) or (start + 1)
    end = min(end, len(source_lines))
    body = source_lines[start:end]
    # Drop trailing blank lines for cleaner examples.
    while body and not body[-1].strip():
        body.pop()
    snippet_lines = ["*** Test Cases ***", *body]
    return "\n".join(snippet_lines).rstrip() + "\n"


def _keyword_calls_in_test(test_case) -> List[str]:
    from robot.parsing.model.statements import KeywordCall

    names = []
    for stmt in test_case.body:
        if isinstance(stmt, KeywordCall):
            keyword = getattr(stmt, "keyword", "") or ""
            # Assignment form: `${x}=    Keyword` — KeywordCall.keyword is the keyword.
            if keyword:
                names.append(keyword)
    return names


def collect_examples_from_tests(
    suite_paths: Sequence[str | Path],
    keyword_names: Optional[Sequence[str]] = None,
    max_examples_per_keyword: int = 3,
) -> Dict[str, List[KeywordExample]]:
    """
    Scan suite files and collect usage examples for the given keyword names.

    Returns a mapping of original keyword name -> examples.
    """
    from robot.api import get_model
    from robot.parsing.model.blocks import TestCase

    wanted: Dict[str, str] = {}
    if keyword_names:
        for name in keyword_names:
            wanted[normalize_keyword_name(name)] = name
    else:
        wanted = {}

    collected: Dict[str, List[KeywordExample]] = {}

    for suite_path in _iter_suite_files(suite_paths):
        try:
            model = get_model(str(suite_path))
            source_lines = suite_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue

        for section in model.sections:
            for item in getattr(section, "body", []):
                if not isinstance(item, TestCase):
                    continue
                called = _keyword_calls_in_test(item)
                if not called:
                    continue

                matched_originals: Set[str] = set()
                for called_name in called:
                    key = normalize_keyword_name(called_name)
                    if wanted:
                        if key not in wanted:
                            continue
                        matched_originals.add(wanted[key])
                    else:
                        matched_originals.add(called_name)

                if not matched_originals:
                    continue

                documentation = _extract_test_documentation(item)
                snippet = _snippet_for_test(source_lines, item)
                for original in sorted(matched_originals):
                    examples = collected.setdefault(original, [])
                    if len(examples) >= max_examples_per_keyword:
                        continue
                    # Avoid duplicate snippets for the same keyword.
                    if any(existing.snippet == snippet for existing in examples):
                        continue
                    examples.append(
                        KeywordExample(
                            keyword=original,
                            test_name=item.name,
                            documentation=documentation,
                            snippet=snippet,
                            source=str(suite_path),
                        )
                    )
    return collected


def attach_examples_to_library(
    library_info: LibraryInfo,
    suite_paths: Sequence[str | Path],
    max_examples_per_keyword: int = 3,
    overwrite_existing: bool = False,
) -> int:
    """
    Attach harvested test examples onto LibraryInfo keywords.

    Populates ``keyword.example`` when empty (or when overwrite_existing=True).
    Returns the number of keywords that received an example.
    """
    if not suite_paths:
        return 0

    keyword_names = [kw.name for kw in library_info.keywords]
    found = collect_examples_from_tests(
        suite_paths,
        keyword_names=keyword_names,
        max_examples_per_keyword=max_examples_per_keyword,
    )
    updated = 0
    for keyword in library_info.keywords:
        examples = found.get(keyword.name) or []
        if not examples:
            # Also try normalized lookup in case of minor naming differences.
            examples = found.get(normalize_keyword_name(keyword.name)) or []
        if not examples:
            continue
        if keyword.example and not overwrite_existing:
            continue
        primary = examples[0]
        header = ""
        if primary.documentation:
            header = f"# From test '{primary.test_name}': {primary.documentation}\n"
        keyword.example = header + primary.as_robot_block()
        updated += 1
    return updated
