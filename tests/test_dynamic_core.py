"""Regression tests for DynamicCore / dynamic library Libdoc resolution (issue #7)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from robotframework_docgen.parser import RobotFrameworkDocParser

SAMPLE_LIBS = Path(__file__).resolve().parents[1] / "sample_libs"


@pytest.fixture
def parser() -> RobotFrameworkDocParser:
    return RobotFrameworkDocParser({})


def _kw_names(info) -> list[str]:
    return sorted(kw.name for kw in info.keywords)


class TestDynamicCoreSamples:
    def test_single_file_aggregator(self, parser):
        info = parser.parse_file(str(SAMPLE_LIBS / "MainLibrary.py"))
        assert info.name == "MainLibrary"
        assert _kw_names(info) == ["Compute From B", "Greet From A"]
        greet = next(kw for kw in info.keywords if kw.name == "Greet From A")
        assert any(name == "name" for name, _ in greet.parameters)

    def test_package_module_file_path_resolves_class(self, parser):
        """File-path Libdoc returns 0 keywords; class-qualified target must win."""
        info = parser.parse_file(str(SAMPLE_LIBS / "dyn_pkg" / "main.py"))
        assert info.name == "MainLibrary"
        assert _kw_names(info) == ["Compute From B", "Greet From A"]

    def test_issue_style_absolute_imports(self, parser):
        info = parser.parse_file(str(SAMPLE_LIBS / "IssueStyleMain.py"))
        assert info.name == "IssueStyleMain"
        assert _kw_names(info) == ["Compute From B", "Greet From A"]

    def test_required_init_args_use_placeholders(self, parser):
        """Libraries that require import args must not fall back to inner helpers."""
        info = parser.parse_file(str(SAMPLE_LIBS / "ArgsDynamic.py"))
        assert info.name == "ArgsDynamic"
        assert _kw_names(info) == ["Ping"]
        assert info.inits, "expected Libdoc init metadata for required base_url"

    def test_pure_get_keyword_names_library(self, parser):
        info = parser.parse_file(str(SAMPLE_LIBS / "PureDynamic.py"))
        assert info.name == "PureDynamic"
        assert _kw_names(info) == ["Do Thing", "Say Hello"]
        do_thing = next(kw for kw in info.keywords if kw.name == "Do Thing")
        assert "dynamic" in do_thing.tags
        assert do_thing.description

    def test_hybrid_dynamic_with_optional_init(self, parser):
        info = parser.parse_file(str(SAMPLE_LIBS / "HybridDynamic.py"))
        assert info.name == "HybridDynamic"
        assert _kw_names(info) == ["Helper Only"]

    def test_packaged_dynamic_core_relative_imports(self, parser):
        info = parser.parse_file(
            str(SAMPLE_LIBS / "dynamic_core" / "main_library.py")
        )
        assert info.name == "MainLibrary"
        assert _kw_names(info) == [
            "Compute From B",
            "Echo From B",
            "Greet From A",
            "Ping A",
        ]
        echo = next(kw for kw in info.keywords if kw.name == "Echo From B")
        assert echo.description

    def test_packaged_args_library(self, parser):
        info = parser.parse_file(
            str(SAMPLE_LIBS / "dynamic_core" / "args_library.py")
        )
        assert info.name == "ArgsLibrary"
        assert _kw_names(info) == ["Ping"]

    def test_broken_dynamic_does_not_pick_component_class(self, parser):
        """Init passes classes instead of instances — must not document LibraryA."""
        info = parser.parse_file(str(SAMPLE_LIBS / "BrokenDynamic.py"))
        assert info.name == "BrokenDynamic"
        assert info.keywords == []
        assert parser._last_libdoc_error


class TestDynamicCoreTmpFixtures:
    def test_tmp_dynamic_core_package(self, parser, tmp_path, monkeypatch):
        root = tmp_path / "proj"
        pkg = root / "dynlib"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "helpers.py").write_text(
            textwrap.dedent(
                """
                from robot.api.deco import keyword

                class Helpers:
                    @keyword
                    def hello_dynamic(self, whom: str = "world") -> str:
                        \"\"\"Greet via DynamicCore helper.\"\"\"
                        return f"hi {whom}"
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        (pkg / "library.py").write_text(
            textwrap.dedent(
                """
                from robotlibcore import DynamicCore
                from .helpers import Helpers

                class DemoLibrary(DynamicCore):
                    \"\"\"Demo DynamicCore library.\"\"\"
                    ROBOT_LIBRARY_SCOPE = "GLOBAL"
                    ROBOT_LIBRARY_VERSION = "9.9.9"

                    def __init__(self):
                        super().__init__([Helpers()])
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(root)
        info = parser.parse_file(str(pkg / "library.py"))
        assert info.name == "DemoLibrary"
        assert info.version == "9.9.9"
        assert _kw_names(info) == ["Hello Dynamic"]
        hello = info.keywords[0]
        assert any(name == "whom" for name, _ in hello.parameters)
        assert hello.parameter_defaults.get("whom") in {"world", "'world'", '"world"'}

    def test_tmp_required_init_avoids_inner_class(self, parser, tmp_path, monkeypatch):
        lib = tmp_path / "NeedUrl.py"
        lib.write_text(
            textwrap.dedent(
                """
                from robot.api.deco import keyword
                from robotlibcore import DynamicCore

                class _OnlyHelper:
                    @keyword
                    def only_helper(self):
                        \"\"\"Should belong to NeedUrl, not _OnlyHelper.\"\"\"
                        return True

                class NeedUrl(DynamicCore):
                    \"\"\"Needs a URL at import time.\"\"\"
                    def __init__(self, base_url: str):
                        self.base_url = base_url
                        super().__init__([_OnlyHelper()])
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        info = parser.parse_file(str(lib))
        assert info.name == "NeedUrl"
        assert _kw_names(info) == ["Only Helper"]

    def test_ast_fallback_prefers_dynamic_core_name(self, parser, tmp_path):
        """When Libdoc cannot initialize, AST should still name the aggregator."""
        lib = tmp_path / "BrokenAgg.py"
        lib.write_text(
            textwrap.dedent(
                """
                from robot.api.deco import keyword
                from robotlibcore import DynamicCore

                class Leaf:
                    @keyword
                    def leaf_kw(self):
                        \"\"\"Leaf keyword.\"\"\"
                        pass

                class BrokenAgg(DynamicCore):
                    ROBOT_LIBRARY_VERSION = "1.2.3"
                    def __init__(self):
                        super().__init__([Leaf])  # class, not instance
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        info = parser.parse_file(str(lib))
        assert info.name == "BrokenAgg"
        assert info.version == "1.2.3"
        assert info.keywords == []


class TestDynamicCoreEndToEnd:
    def test_generator_html_contains_dynamic_keywords(self, parser):
        from robotframework_docgen.generator import DocumentationGenerator

        cases = [
            (
                SAMPLE_LIBS / "dynamic_core" / "main_library.py",
                ["Greet From A", "Echo From B", "Ping A", "Compute From B"],
                ["_ArgsHelpers", "ComponentA"],
            ),
            (
                SAMPLE_LIBS / "dynamic_core" / "args_library.py",
                ["Ping"],
                ["_ArgsHelpers"],
            ),
            (
                SAMPLE_LIBS / "PureDynamic.py",
                ["Do Thing", "Say Hello"],
                [],
            ),
            (
                SAMPLE_LIBS / "dyn_pkg" / "main.py",
                ["Greet From A", "Compute From B"],
                [],
            ),
        ]
        for path, expected, forbidden in cases:
            info = parser.parse_file(str(path))
            html = DocumentationGenerator(info, parser=parser).generate_html()
            for name in expected:
                assert name in html, f"{path}: missing {name}"
            for name in forbidden:
                assert name not in html, f"{path}: unexpected {name}"
            assert "<html" in html.lower()
