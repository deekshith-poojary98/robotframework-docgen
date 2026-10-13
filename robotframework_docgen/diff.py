"""
Keyword changelog / diff between two library catalog snapshots.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from robotframework_docgen.catalog import (
    CatalogBundle,
    KeywordMetadata,
    LibraryCatalog,
    load_catalog_bundle,
)


@dataclass
class KeywordChange:
    """A single keyword-level change inside one library."""

    name: str
    change_type: str  # added | removed | changed
    old_signature: Optional[str] = None
    new_signature: Optional[str] = None
    field_changes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LibraryDiff:
    """Diff for one library present in old and/or new catalogs."""

    name: str
    change_type: str  # added | removed | changed | unchanged
    keyword_changes: List[KeywordChange] = field(default_factory=list)

    @property
    def added(self) -> List[KeywordChange]:
        return [c for c in self.keyword_changes if c.change_type == "added"]

    @property
    def removed(self) -> List[KeywordChange]:
        return [c for c in self.keyword_changes if c.change_type == "removed"]

    @property
    def changed(self) -> List[KeywordChange]:
        return [c for c in self.keyword_changes if c.change_type == "changed"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "change_type": self.change_type,
            "keyword_changes": [change.to_dict() for change in self.keyword_changes],
        }


@dataclass
class DiffReport:
    """Full changelog between two catalog bundles."""

    old_label: str
    new_label: str
    libraries: List[LibraryDiff] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return any(lib.change_type != "unchanged" for lib in self.libraries)

    def summary_counts(self) -> Dict[str, int]:
        added = removed = changed = 0
        libraries_added = libraries_removed = 0
        for lib in self.libraries:
            if lib.change_type == "added":
                libraries_added += 1
            elif lib.change_type == "removed":
                libraries_removed += 1
            added += len(lib.added)
            removed += len(lib.removed)
            changed += len(lib.changed)
        return {
            "libraries_added": libraries_added,
            "libraries_removed": libraries_removed,
            "keywords_added": added,
            "keywords_removed": removed,
            "keywords_changed": changed,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "old_label": self.old_label,
            "new_label": self.new_label,
            "summary": self.summary_counts(),
            "libraries": [lib.to_dict() for lib in self.libraries],
        }

    def to_text(self) -> str:
        lines = [
            f"Keyword changelog: {self.old_label} → {self.new_label}",
            "",
        ]
        counts = self.summary_counts()
        lines.append(
            "Summary: "
            f"+{counts['keywords_added']} / -{counts['keywords_removed']} / "
            f"~{counts['keywords_changed']} keywords "
            f"({counts['libraries_added']} libraries added, "
            f"{counts['libraries_removed']} removed)"
        )
        lines.append("")

        if not self.has_changes:
            lines.append("No keyword signature changes detected.")
            return "\n".join(lines)

        for lib in self.libraries:
            if lib.change_type == "unchanged":
                continue
            lines.append(f"## {lib.name} ({lib.change_type})")
            for change in lib.keyword_changes:
                if change.change_type == "added":
                    lines.append(f"  + {change.new_signature}")
                elif change.change_type == "removed":
                    lines.append(f"  - {change.old_signature}")
                else:
                    detail = ", ".join(change.field_changes) or "signature"
                    lines.append(f"  ~ {change.name}: {detail}")
                    if change.old_signature and change.new_signature:
                        lines.append(f"      old: {change.old_signature}")
                        lines.append(f"      new: {change.new_signature}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def to_markdown(self) -> str:
        lines = [
            f"# Keyword changelog: `{self.old_label}` → `{self.new_label}`",
            "",
        ]
        counts = self.summary_counts()
        lines.extend(
            [
                "## Summary",
                "",
                f"- Keywords added: **{counts['keywords_added']}**",
                f"- Keywords removed: **{counts['keywords_removed']}**",
                f"- Keywords changed: **{counts['keywords_changed']}**",
                f"- Libraries added: **{counts['libraries_added']}**",
                f"- Libraries removed: **{counts['libraries_removed']}**",
                "",
            ]
        )
        if not self.has_changes:
            lines.append("No keyword signature changes detected.")
            return "\n".join(lines) + "\n"

        for lib in self.libraries:
            if lib.change_type == "unchanged":
                continue
            lines.append(f"## {lib.name}")
            lines.append("")
            lines.append(f"_Library {lib.change_type}_")
            lines.append("")
            if lib.added:
                lines.append("### Added")
                for change in lib.added:
                    lines.append(f"- `{change.new_signature}`")
                lines.append("")
            if lib.removed:
                lines.append("### Removed")
                for change in lib.removed:
                    lines.append(f"- `{change.old_signature}`")
                lines.append("")
            if lib.changed:
                lines.append("### Changed")
                for change in lib.changed:
                    detail = ", ".join(change.field_changes) or "signature"
                    lines.append(f"- **{change.name}** ({detail})")
                    lines.append(f"  - old: `{change.old_signature}`")
                    lines.append(f"  - new: `{change.new_signature}`")
                lines.append("")
        return "\n".join(lines).rstrip() + "\n"


def _param_map(keyword: KeywordMetadata) -> Dict[str, Any]:
    return {
        param.name: {
            "type": param.type or "Any",
            "default": param.default,
        }
        for param in keyword.parameters
    }


def compare_keywords(
    old: KeywordMetadata, new: KeywordMetadata
) -> Optional[KeywordChange]:
    """Return a KeywordChange when signatures differ; otherwise None."""
    field_changes: List[str] = []

    old_params = _param_map(old)
    new_params = _param_map(new)
    if list(old_params) != list(new_params):
        field_changes.append("parameters")
    else:
        for name in old_params:
            if old_params[name]["type"] != new_params[name]["type"]:
                field_changes.append(f"type:{name}")
            if old_params[name]["default"] != new_params[name]["default"]:
                field_changes.append(f"default:{name}")

    if (old.return_type or "None") != (new.return_type or "None"):
        field_changes.append("return_type")

    # Documentation-only edits are tracked separately from signature breaks.
    if (old.description or "").strip() != (new.description or "").strip():
        field_changes.append("documentation")

    if not field_changes:
        return None

    return KeywordChange(
        name=new.name,
        change_type="changed",
        old_signature=old.full_signature(),
        new_signature=new.full_signature(),
        field_changes=field_changes,
    )


def compare_libraries(
    old: Optional[LibraryCatalog], new: Optional[LibraryCatalog]
) -> LibraryDiff:
    """Diff keywords for a single library."""
    if old is None and new is not None:
        return LibraryDiff(
            name=new.name,
            change_type="added",
            keyword_changes=[
                KeywordChange(
                    name=kw.name,
                    change_type="added",
                    new_signature=kw.full_signature(),
                )
                for kw in new.keywords
            ],
        )

    if new is None and old is not None:
        return LibraryDiff(
            name=old.name,
            change_type="removed",
            keyword_changes=[
                KeywordChange(
                    name=kw.name,
                    change_type="removed",
                    old_signature=kw.full_signature(),
                )
                for kw in old.keywords
            ],
        )

    assert old is not None and new is not None
    old_map = old.keyword_map()
    new_map = new.keyword_map()
    changes: List[KeywordChange] = []

    for name in sorted(set(old_map) | set(new_map), key=str.lower):
        if name not in old_map:
            changes.append(
                KeywordChange(
                    name=name,
                    change_type="added",
                    new_signature=new_map[name].full_signature(),
                )
            )
        elif name not in new_map:
            changes.append(
                KeywordChange(
                    name=name,
                    change_type="removed",
                    old_signature=old_map[name].full_signature(),
                )
            )
        else:
            changed = compare_keywords(old_map[name], new_map[name])
            if changed:
                changes.append(changed)

    change_type = "changed" if changes else "unchanged"
    return LibraryDiff(name=new.name, change_type=change_type, keyword_changes=changes)


def diff_catalogs(old: CatalogBundle, new: CatalogBundle) -> DiffReport:
    """Compare two catalog bundles and return a DiffReport."""
    old_map = old.library_map()
    new_map = new.library_map()
    names = sorted(set(old_map) | set(new_map), key=str.lower)
    libraries = [
        compare_libraries(old_map.get(name), new_map.get(name)) for name in names
    ]
    return DiffReport(
        old_label=old.label or "old",
        new_label=new.label or "new",
        libraries=libraries,
    )


def diff_paths(
    old_path: str,
    new_path: str,
    old_label: str = "",
    new_label: str = "",
) -> DiffReport:
    """Load catalogs from filesystem paths and diff them."""
    old_bundle = load_catalog_bundle(old_path, label=old_label or old_path)
    new_bundle = load_catalog_bundle(new_path, label=new_label or new_path)
    return diff_catalogs(old_bundle, new_bundle)
